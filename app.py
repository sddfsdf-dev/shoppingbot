import streamlit as st
import pandas as pd
from openai import OpenAI
import time

# 1. OpenAI 설정
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Shopping Assistant", layout="centered")

# 2. URL 파라미터 읽기 (2x3 디자인 분기)
query_params = st.query_params
group_id = query_params.get("group", "1")

# 실험 조건 매핑
# 1,2,3: No Control (Absence) / 4,5,6: Control (Presence)
# 1,4: Separated / 2,5: In-text / 3,6: Following
is_controllable = group_id in ["4", "5", "6"]
ad_pos = "separated" if group_id in ["1", "4"] else \
         "in-text" if group_id in ["2", "5"] else "following"

# 3. 데이터 로드
@st.cache_data
def load_data():
    for f in ['products.csv', 'product.csv']:
        try: return pd.read_csv(f)
        except: continue
    return None
product_df = load_data()

# 4. 세션 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm your AI shopping assistant. What product category are you looking for today?"}]
if "turn" not in st.session_state: st.session_state.turn = 1
if "finished" not in st.session_state: st.session_state.finished = False

# 대화 기록 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 5. 대화 로직
if not st.session_state.finished:
    if prompt := st.chat_input("Type your answer here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                time.sleep(1.2)
                if st.session_state.turn == 1:
                    next_q = "Got it. **Who is this product for?**"
                elif st.session_state.turn == 2:
                    next_q = "Finally, **What is your maximum budget in dollars ($)?**"
                
                if st.session_state.turn < 3:
                    st.session_state.messages.append({"role": "assistant", "content": next_q})
                    st.markdown(next_q)
                    st.session_state.turn += 1
                else:
                    st.session_state.finished = True
                    st.rerun()

# 6. 최종 추천 및 2x3 광고 노출
if st.session_state.finished:
    is_done = any("[AD]" in m["content"] or "Based on" in m["content"] for m in st.session_state.messages)
    
    if not is_done:
        with st.chat_message("assistant"):
            with st.spinner("Generating best recommendation..."):
                time.sleep(2)
                subset = product_df[['name', 'price', 'category']] if product_df is not None else "No data"
                
                # 조건별 프롬프트 구성
                if ad_pos == "in-text":
                    sys_msg = "Recommend ONE product. The ENTIRE response must be a persuasive advertisement. Start with '[AD] Sponsored Recommendation:'."
                elif ad_pos == "following":
                    sys_msg = "Provide a neutral recommendation first. Then, add a line break and start a new paragraph with 'By the way, [AD]...' recommending a different premium product."
                else: # separated
                    sys_msg = "Provide a neutral, objective product recommendation only."

                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": sys_msg}] + st.session_state.messages
                )
                final_text = res.choices[0].message.content.replace('*', '')

                # [Control 조건] 닫기 버튼 UI (말풍선 내부 상단)
                if is_controllable and ad_pos in ["in-text", "following"]:
                    st.markdown('<div style="text-align:right; font-size:10px; color:#ccc; border-bottom:1px solid #eee; margin-bottom:5px; cursor:pointer;">✕ Hide Ad Content</div>', unsafe_allow_html=True)
                
                st.markdown(final_text)
                st.session_state.messages.append({"role": "assistant", "content": final_text})

                # [Separated 조건] 사이드바 광고
                if ad_pos == "separated":
                    with st.sidebar:
                        st.markdown("### Sponsored")
                        if is_controllable:
                            st.markdown('<div style="text-align:right; font-size:10px; color:gray; cursor:pointer;">✕ Close</div>', unsafe_allow_html=True)
                        st.info("✨ [AD] We found a premium alternative you might like. Check out our partner's top-rated product!")

        st.balloons()
        st.caption("✅ Interaction finished. Please return to Qualtrics and click 'Next'.")
