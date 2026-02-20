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

# 3. 데이터 로드 (캐싱)
@st.cache_data
def load_data():
    for f in ['products.csv', 'product.csv']:
        try: return pd.read_csv(f)
        except: continue
    return None
product_df = load_data()

# 4. 세션 상태 초기화 (리다이렉션 방지 및 데이터 보존)
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm here to help you shop. **1. What kind of product category are you looking for?**"}]
if "turn" not in st.session_state: st.session_state.turn = 1
if "finished" not in st.session_state: st.session_state.finished = False
if "ad_content" not in st.session_state: st.session_state.ad_content = None

# 기존 대화 로그 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 5. 대화 진행 로직
if not st.session_state.finished:
    if prompt := st.chat_input("Type your answer here..."):
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 시스템 답변 생성
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                time.sleep(1.0)
                if st.session_state.turn == 1:
                    next_q = "Got it. **2. Who is this product for?**"
                    st.session_state.turn += 1
                elif st.session_state.turn == 2:
                    next_q = "Finally, **3. What is your maximum budget ($)?**"
                    st.session_state.turn += 1
                else:
                    st.session_state.finished = True
                    st.rerun() # 마지막 질문 후 결과 생성을 위해 리런
                
                st.session_state.messages.append({"role": "assistant", "content": next_q})
                st.markdown(next_q)

# 6. 최종 결과 및 광고 출력 (실험 조건별 분기)
if st.session_state.finished:
    # 이미 최종 답변이 있는지 확인
    is_done = any("[AD]" in m["content"] or "Based on our" in m["content"] for m in st.session_state.messages)

    if not is_done:
        with st.chat_message("assistant"):
            with st.spinner("Finding your perfect match..."):
                time.sleep(1.5)
                
                # 그룹별 프롬프트 설정
                if ad_pos == "in-text":
                    sys_msg = "Recommend ONE product. The ENTIRE response must be a persuasive ad. Start with '[AD] Sponsored Recommendation:'."
                elif ad_pos == "following":
                    sys_msg = "Recommend one product neutrally. Then, add a line break and start a paragraph with 'By the way, [AD]...' and recommend a different product."
                else: # separated (Group 1, 4)
                    sys_msg = "Recommend ONE product from the list in a neutral, objective tone. USE PLAIN TEXT ONLY. NO asterisks."

                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": sys_msg}] + st.session_state.messages
                )
                final_advice = res.choices[0].message.content.replace('*', '')

                # [Control] 제어권 UI 표시 (In-text, Following)
                if is_controllable and ad_pos in ["in-text", "following"]:
                    st.markdown('<div style="text-align:right; font-size:10px; color:#ccc; margin-bottom:5px;">✕ Hide Ad</div>', unsafe_allow_html=True)

                st.markdown(final_advice)
                st.session_state.messages.append({"role": "assistant", "content": final_advice})

                # [Separated] 배너 광고용 데이터 미리 생성
                if ad_pos == "separated":
                    ad_res = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "system", "content": "Pick a DIFFERENT product. Format: Headline | Description | Price. Output only parts separated by '|'. No labels."}] + st.session_state.messages
                    )
                    st.session_state.ad_content = ad_res.choices[0].message.content.replace('*', '')
        
        st.balloons()
        st.caption("✅ Interaction finished. Please return to Qualtrics and click 'Next'.")

    # --- [해결] Separated 배너 렌더링 (채팅 말풍선 외부 독립 영역) ---
    if ad_pos == "separated" and st.session_state.ad_content:
        try:
            parts = st.session_state.ad_content.split('|')
            h = parts[0].strip()
            d = parts[1].strip() if len(parts) > 1 else "Exclusive selection."
            p = parts[2].strip() if len(parts) > 2 else ""

            # 제어권(X) 버튼
            ctrl_btn = '<div style="text-align:right; font-size:12px; color:#aaa; cursor:pointer; margin-bottom:-5px;">✕ Hide</div>' if is_controllable else ''
            
            ad_html = f"""
            <div style="border: 1px solid #dadce0; background-color: #ffffff; padding: 20px; border-radius: 8px; font-family: 'Arial', sans-serif; box-shadow: 0 1px 6px rgba(32,33,36,0.12); margin-top: 20px;">
                {ctrl_btn}
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <span style="background: #202124; color: white; font-size: 10px; padding: 2px 6px; border-radius: 3px; font-weight: bold; margin-right: 10px;">AD</span>
                    <span style="color: #202124; font-size: 12px; font-weight: 500;">Sponsored Alternative</span>
                </div>
                <div style="color: #1a0dab; font-size: 19px; font-weight: 500; margin-bottom: 5px;">{h}</div>
                <div style="color: #4d5156; font-size: 14px; line-height: 1.5; margin-bottom: 8px;">{d}</div>
                <div style="color: #d93025; font-size: 16px; font-weight: bold;">{p}</div>
            </div>
            """
            components.html(ad_html, height=170)
        except:
            pass
