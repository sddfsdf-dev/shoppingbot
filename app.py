import streamlit as st
import pandas as pd
from openai import OpenAI
import time
import streamlit.components.v1 as components

# 1. OpenAI 설정
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Shopping Assistant", layout="centered")

# 2. URL 파라미터 읽기 (2x3 실험 설계)
query_params = st.query_params
group_id = query_params.get("group", "1")

is_controllable = group_id in ["4", "5", "6"]
ad_pos = "separated" if group_id in ["1", "4"] else \
         "in-text" if group_id in ["2", "5"] else "following"

# 3. 세션 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm here to help you shop. **1. What kind of product category are you looking for?**"}]
if "turn" not in st.session_state: st.session_state.turn = 1
if "finished" not in st.session_state: st.session_state.finished = False
if "ad_pref_asked" not in st.session_state: st.session_state.ad_pref_asked = False # 제어권 질문 여부
if "show_ad" not in st.session_state: st.session_state.show_ad = True # 광고 노출 여부

# 대화 기록 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- [함수] Separated 광고 렌더링 ---
def render_separated_ad(user_context, recommended_item_name):
    if not st.session_state.show_ad: return
    ad_res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"""You are a luxury ad system. 
            Recommend a DIFFERENT competitor to '{recommended_item_name}'. 
            Format: Headline | Brief Description | Price. 
            Strict Rules: Keep it very short (max 2 sentences). Output ONLY 3 parts separated by '|'. No labels."""}
        ] + user_context
    )
    try:
        parts = ad_res.choices[0].message.content.replace('*', '').split('|')
        h, d, p = parts[0].strip(), parts[1].strip(), parts[2].strip()
        
        ad_html = f"""
        <div style="border: 1px solid #dadce0; background-color: #ffffff; padding: 18px; border-radius: 8px; font-family: sans-serif; box-shadow: 0 1px 6px rgba(32,33,36,0.12); margin-top: 10px;">
            <div style="display: flex; align-items: center; margin-bottom: 8px;">
                <span style="background: #202124; color: white; font-size: 10px; padding: 2px 6px; border-radius: 3px; font-weight: bold; margin-right: 10px;">AD</span>
                <span style="color: #202124; font-size: 12px; font-weight: 500;">Sponsored Alternative</span>
            </div>
            <div style="color: #1a0dab; font-size: 18px; font-weight: bold; margin-bottom: 4px;">{h}</div>
            <div style="color: #4d5156; font-size: 13px; line-height: 1.4; margin-bottom: 8px;">{d}</div>
            <div style="color: #d93025; font-size: 15px; font-weight: bold;">{p}</div>
        </div>
        """
        components.html(ad_html, height=160)
    except: pass

# 4. 질문 프로세스 (1~3단계)
if not st.session_state.finished:
    if prompt := st.chat_input("Type your answer here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                time.sleep(0.8)
                if st.session_state.turn == 1:
                    next_q = "Got it. **2. Who is this product for?**"
                elif st.session_state.turn == 2:
                    next_q = "Finally, **3. What is your maximum budget ($)?**"
                
                if st.session_state.turn < 3:
                    st.session_state.messages.append({"role": "assistant", "content": next_q})
                    st.markdown(next_q)
                    st.session_state.turn += 1
                else:
                    st.session_state.finished = True
                    st.rerun()

# 5. 최종 응답 및 제어권 인터랙션
if st.session_state.finished:
    # 최종 추천 생성
    is_done = any("Based on" in m["content"] or "**[AD]**" in m["content"] for m in st.session_state.messages)

    if not is_done:
        with st.chat_message("assistant"):
            with st.spinner("Generating recommendation..."):
                # 광고 스타일 및 분량 제한 프롬프트
                if ad_pos == "in-text":
                    sys_msg = "Recommend ONE product. Entire response must be a VERY SHORT (1 paragraph) persuasive ad. Start with '**[AD]** Sponsored Recommendation:'."
                elif ad_pos == "following":
                    sys_msg = "Recommend one product neutrally (1-2 sentences). Then, add a line break and start with '**[AD]** By the way...' followed by a VERY BRIEF premium alternative."
                else: # separated
                    sys_msg = "Recommend ONE product neutrally and objectively. Keep it under 2 sentences. Use plain text only."

                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": sys_msg}] + st.session_state.messages
                )
                final_advice = res.choices[0].message.content.replace('*', '').replace('[AD]', '**[AD]**')

                st.markdown(final_advice)
                st.session_state.messages.append({"role": "assistant", "content": final_advice})
                
                if ad_pos == "separated":
                    render_separated_ad(st.session_state.messages, final_advice)
                
                # [Controllability 단계 추가] 광고 후 질문
                if is_controllable and not st.session_state.ad_pref_asked:
                    time.sleep(1.0)
                    ctrl_q = "You might have noticed an advertisement based on your shopping intent. **Would you like to keep seeing these tailored ads, or would you prefer to turn them off for the rest of this session?**"
                    st.session_state.messages.append({"role": "assistant", "content": ctrl_q})
                    st.markdown("---")
                    st.markdown(ctrl_q)
                    st.session_state.ad_pref_asked = True
                    st.rerun()

    # 제어권 응답 처리
    if is_controllable and st.session_state.ad_pref_asked and st.session_state.show_ad:
        if ad_resp := st.chat_input("Keep ads / Turn off ads"):
            st.session_state.messages.append({"role": "user", "content": ad_resp})
            if "off" in ad_resp.lower() or "no" in ad_resp.lower() or "끄" in ad_resp:
                st.session_state.show_ad = False
                confirm_msg = "Understood. I have **turned off** the ads for you. You can continue with your shopping."
            else:
                confirm_msg = "Great! I will continue to provide tailored recommendations including sponsored items."
            
            st.session_state.messages.append({"role": "assistant", "content": confirm_msg})
            st.rerun()

    st.balloons()
    st.caption("✅ Interaction finished. Please return to Qualtrics and click 'Next'.")
