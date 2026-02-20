import streamlit as st
import pandas as pd
from openai import OpenAI
import time
import streamlit.components.v1 as components

# 1. OpenAI 설정
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Shopping Assistant", layout="centered")

# 2. URL 파라미터 읽기
query_params = st.query_params
group_id = query_params.get("group", "1")

is_controllable = group_id in ["4", "5", "6"]
ad_pos = "separated" if group_id in ["1", "4"] else \
         "in-text" if group_id in ["2", "5"] else "following"

# 3. 세션 초기화 (상태 관리를 더 엄격하게 변경)
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm here to help you shop. **1. What kind of product category are you looking for?**"}]
if "turn" not in st.session_state: st.session_state.turn = 1
if "finished" not in st.session_state: st.session_state.finished = False
if "recommendation_generated" not in st.session_state: st.session_state.recommendation_generated = False # 중복 방지 핵심 플래그
if "ad_pref_asked" not in st.session_state: st.session_state.ad_pref_asked = False 
if "show_ad" not in st.session_state: st.session_state.show_ad = True 
if "flow_complete" not in st.session_state: st.session_state.flow_complete = False
if "ad_html_cache" not in st.session_state: st.session_state.ad_html_cache = None 

# 대화 기록 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=True)

# 광고 태그 디자인
ad_tag = '<span style="color: #006621; border: 1px solid #006621; padding: 0px 3px; border-radius: 3px; font-size: 11px; font-weight: bold; margin-right: 5px; vertical-align: middle;">AD</span>'

# 4. 질문 프로세스 (1~3단계)
if not st.session_state.finished:
    if prompt := st.chat_input("Type your answer here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if st.session_state.turn < 3:
                time.sleep(0.5)
                next_q = "Got it. **2. Who is this product for?**" if st.session_state.turn == 1 else "Finally, **3. What is your maximum budget ($)?**"
                st.session_state.messages.append({"role": "assistant", "content": next_q})
                st.markdown(next_q)
                st.session_state.turn += 1
            else:
                st.session_state.finished = True
                st.rerun()

# 5. 최종 응답 및 광고 로직
if st.session_state.finished:
    # 플래그가 False일 때만 단 한 번 API 호출
    if not st.session_state.recommendation_generated:
        with st.chat_message("assistant"):
            with st.spinner("Generating recommendation..."):
                # 추천 답변 생성 프롬프트
                if ad_pos == "in-text":
                    sys_msg = f"Recommend ONE product. Start with a brief intro, then put {ad_tag} right before the product name. 1 short paragraph."
                elif ad_pos == "following":
                    sys_msg = f"Recommend one product neutrally. Then, new paragraph, introduce premium alternative with {ad_tag} before its name."
                else: # separated
                    sys_msg = "Recommend ONE product neutrally. No ads in text. Under 2 sentences."

                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": sys_msg}] + st.session_state.messages[:-1] # 마지막 입력 포함
                )
                final_advice = res.choices[0].message.content.replace('*', '')
                st.session_state.messages.append({"role": "assistant", "content": final_advice})
                
                # Separated 광고 생성 및 캐싱
                if ad_pos == "separated" and st.session_state.show_ad:
                    ad_res = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "system", "content": "Headline | Description | Price. 2 sentences max. No labels."}] + st.session_state.messages
                    )
                    try:
                        parts = ad_res.choices[0].message.content.replace('*', '').split('|')
                        h, d, p = parts[0].strip(), parts[1].strip(), (parts[2].strip() if len(parts)>2 else "")
                        st.session_state.ad_html_cache = f"""
                        <div style="border: 1px solid #dadce0; padding: 18px; border-radius: 8px; font-family: sans-serif; box-shadow: 0 1px 6px rgba(0,0,0,0.1); margin-top: 10px;">
                            <div style="display: flex; align-items: center; margin-bottom: 8px;">
                                <span style="background: #006621; color: white; font-size: 10px; padding: 2px 6px; border-radius: 3px; font-weight: bold; margin-right: 10px;">AD</span>
                                <span style="color: #202124; font-size: 12px; font-weight: 500;">Sponsored Alternative</span>
                            </div>
                            <div style="color: #1a0dab; font-size: 17px; font-weight: bold; margin-bottom: 4px;">{h}</div>
                            <div style="color: #4d5156; font-size: 13px; line-height: 1.4; margin-bottom: 8px;">{d}</div>
                            <div style="color: #d93025; font-size: 15px; font-weight: bold;">{p}</div>
                        </div>
                        """
                    except: pass
                
                # 생성이 완료되었음을 기록
                st.session_state.recommendation_generated = True
                st.rerun()

    # Separated 광고 출력 (추천 답변 바로 아래)
    if ad_pos == "separated" and st.session_state.ad_html_cache and st.session_state.show_ad:
        components.html(st.session_state.ad_html_cache, height=170)

    # 제어권 인터랙션 (추천 완료 후 별도로 진행)
    if is_controllable and not st.session_state.ad_pref_asked:
        with st.chat_message("assistant"):
            ctrl_q = "You might have noticed an advertisement based on your shopping intent. **Would you like to keep seeing these tailored ads, or would you prefer to turn them off?**"
            st.markdown("---")
            st.markdown(ctrl_q)
            st.session_state.messages.append({"role": "assistant", "content": ctrl_q})
            st.session_state.ad_pref_asked = True
            # 주의: 여기서 st.rerun()을 하지 않고 chat_input을 기다립니다.

    # 제어권 답변 처리
    if is_controllable and st.session_state.ad_pref_asked and not st.session_state.flow_complete:
        if ad_resp := st.chat_input("Type 'Keep ads' or 'Turn off ads'..."):
            st.session_state.messages.append({"role": "user", "content": ad_resp})
            if any(x in ad_resp.lower() for x in ["off", "no", "끄", "안", "turn off"]):
                st.session_state.show_ad = False
                confirm_msg = "Understood. I have **turned off** the ads for you."
            else:
                confirm_msg = "Great! I will continue to provide tailored recommendations."
            st.session_state.messages.append({"role": "assistant", "content": confirm_msg})
            st.session_state.flow_complete = True
            st.rerun()
    elif not is_controllable:
        st.session_state.flow_complete = True

    # 최종 안내
    if st.session_state.flow_complete:
        st.balloons()
        st.success("✅ Interaction finished. Please return to Qualtrics and click 'Next'.")
