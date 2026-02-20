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

# 3. 세션 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm here to help you shop. **1. What kind of product category are you looking for?**"}]
if "turn" not in st.session_state: st.session_state.turn = 1
if "finished" not in st.session_state: st.session_state.finished = False
if "recommendation_generated" not in st.session_state: st.session_state.recommendation_generated = False 
if "ad_pref_asked" not in st.session_state: st.session_state.ad_pref_asked = False 
if "show_ad" not in st.session_state: st.session_state.show_ad = True # 광고 노출 여부 변수
if "flow_complete" not in st.session_state: st.session_state.flow_complete = False
if "ad_control_choice" not in st.session_state:
    st.session_state.ad_control_choice = "fixed"

# 4. 대화 기록 표시 함수
def display_chat():
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)
            # 중요: 사용자가 OFF를 했더라도 이번 세션에서는 광고 데이터를 유지하여 보여줍니다.
            if "ad_html" in msg:
                components.html(msg["ad_html"], height=175)

display_chat()

# 5. 질문 프로세스
if not st.session_state.finished:
    if prompt := st.chat_input("Type your answer here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
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

# 6. 최종 응답 및 광고 로직
if st.session_state.finished:
    if not st.session_state.recommendation_generated:
        with st.chat_message("assistant"):
            with st.spinner("Generating recommendation..."):
                ad_tag = '<span style="color: white; background-color: #006621; padding: 2px 5px; border-radius: 3px; font-size: 11px; font-weight: bold; margin-right: 5px; vertical-align: middle;">AD</span>'
                ad_style = 'style="text-decoration: underline; font-weight: bold; color: #1a0dab;"'
                
                if ad_pos == "in-text":
                    sys_msg = f"""Recommend ONE product. You MUST insert the sponsored alternative WITHIN the paragraph.
                    Format: "I recommend [Neutral Product]. However, you might also like {ad_tag} <span {ad_style}>[Sponsored Product]</span> which is..." """
                elif ad_pos == "following":
                    sys_msg = f"""Recommend one product neutrally. Then, start a NEW paragraph starting with {ad_tag}.
                    In that paragraph, introduce a premium alternative wrapping its name in: <span {ad_style}>[Product Name]</span>"""
                else: 
                    sys_msg = "Recommend ONE product neutrally. No ads in text. Under 2 sentences."

                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": sys_msg}] + st.session_state.messages
                )
                final_advice = res.choices[0].message.content.replace('*', '')
                new_msg = {"role": "assistant", "content": final_advice}

                if ad_pos == "separated":
                    ad_res = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "system", "content": f"Analyze: {final_advice}. Pick ONE competitor. Output: Brand & Model | One-sentence feature | Price."}]
                    )
                    try:
                        parts = ad_res.choices[0].message.content.replace('*', '').split('|')
                        h, d, p = parts[0].strip(), parts[1].strip(), (parts[2].strip() if len(parts) > 2 else "")
                        new_msg["ad_html"] = f"""
                        <div style="border: 1px solid #dadce0; padding: 18px; border-radius: 8px; font-family: sans-serif; box-shadow: 0 1px 6px rgba(0,0,0,0.1); margin-top: 10px; background-color: white;">
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
                
                st.session_state.messages.append(new_msg)
                st.session_state.recommendation_generated = True
                st.rerun()

    # 6-2. 제어권 및 종료 로직
    if is_controllable and not st.session_state.ad_pref_asked:
        time.sleep(0.8)
        ctrl_q = "You might have noticed an advertisement based on your shopping intent. **Would you like to keep seeing these tailored ads, or would you prefer to turn them off?**"
        st.session_state.messages.append({"role": "assistant", "content": ctrl_q})
        st.session_state.ad_pref_asked = True
        st.rerun()

    if is_controllable and st.session_state.ad_pref_asked and not st.session_state.flow_complete:
        if ad_resp := st.chat_input("Type your answer here..."):
            st.session_state.messages.append({"role": "user", "content": ad_resp})
            
            if any(x in ad_resp.lower() for x in ["off", "no", "끄", "안", "turn off"]):
                st.session_state.ad_control_choice = "OFF"
                # 핵심: 지우지 않고 안내만 제공
                confirm_msg = "Understood. I will **not show you any more ads** from our next interaction. You can always turn them back on in your settings if you change your mind."
            else:
                st.session_state.ad_control_choice = "KEEP"
                confirm_msg = "Great! I will continue to provide tailored recommendations."
            
            st.session_state.messages.append({"role": "assistant", "content": confirm_msg})
            st.session_state.flow_complete = True
            st.rerun()
    elif not is_controllable and st.session_state.recommendation_generated:
        st.session_state.flow_complete = True

    # 7. 최종 종료 및 코드 생성
    if st.session_state.flow_complete:
        st.balloons()
        completion_code = f"SURVEY-{group_id}-{st.session_state.ad_control_choice}-{str(int(time.time()))[-5:]}"
        st.success("✅ Interaction finished.")
        st.markdown("---")
        st.subheader("Final Step: Copy your Completion Code")
        st.info("Please copy the code below and paste it back into the Qualtrics survey to receive your credit.")
        st.code(completion_code, language="text")
        st.write("After copying the code, you can close this window and return to the survey.")
