import streamlit as st
import pandas as pd
from openai import OpenAI
import re

# 1. OpenAI 설정
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Shopping Assistant", layout="centered")

# 2. 데이터 로드
@st.cache_data
def load_data():
    for f in ['products.csv', 'product.csv']:
        try: return pd.read_csv(f)
        except: continue
    return None

product_df = load_data()

# --- [수정] 마지막 답변과 함께 뜰 구글 스타일 광고 배너 ---
def render_final_ad(user_context):
    # GPT에게 광고로 제안할 '다른' 제품을 하나 고르게 함
    ad_res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an advertising system. Based on the user's interest, pick ONE alternative product that is different from their main preference but related. Provide a short catchy ad title and a price."}
        ] + user_context
    )
    ad_content = ad_res.choices[0].message.content

    st.markdown(f"""
        <div style="
            border: 1px solid #e0e0e0;
            background-color: #f9f9f9;
            padding: 15px;
            margin-top: 20px;
            border-radius: 8px;
            font-family: 'Roboto', sans-serif;
        ">
            <div style="color: #70757a; font-size: 11px; margin-bottom: 8px; font-weight: bold; letter-spacing: 0.5px;">[AD] Sponsored Content</div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="color: #1a0dab; font-size: 16px; font-weight: 500; margin-bottom: 4px;">{ad_content[:50]}...</div>
                    <div style="color: #006621; font-size: 13px;">Special Offer Available Now</div>
                </div>
                <a href="https://google.com" target="_blank" style="
                    background-color: #1a73e8;
                    color: white;
                    padding: 8px 20px;
                    text-decoration: none;
                    font-size: 13px;
                    border-radius: 4px;
                    font-weight: bold;
                ">Shop Now</a>
            </div>
        </div>
    """, unsafe_allow_html=True)

# 3. 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm here to help you shop. **1. What kind of product category are you looking for?**"}]
if "turn" not in st.session_state: st.session_state.turn = 1
if "finished" not in st.session_state: st.session_state.finished = False

# 4. 대화 기록 표시 (일반 대화 중에는 광고 없음)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 5. 대화 진행 로직
if not st.session_state.finished:
    if prompt := st.chat_input("Type your answer here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        if st.session_state.turn == 1:
            next_q = "Got it. **2. Who is this product for?**"
            st.session_state.messages.append({"role": "assistant", "content": next_q})
            st.session_state.turn += 1
        elif st.session_state.turn == 2:
            next_q = "Finally, **3. What is your maximum budget in dollars ($)?**"
            st.session_state.messages.append({"role": "assistant", "content": next_q})
            st.session_state.turn += 1
        elif st.session_state.turn == 3:
            st.session_state.finished = True
        
        st.rerun()

# 6. 마지막 추천 및 광고 동시 출력
if st.session_state.finished:
    # 추천 메시지가 이미 생성되었는지 확인 (중복 생성 방지)
    is_already_recommended = any("Based on our conversation" in m["content"] for m in st.session_state.messages)
    
    if not is_already_recommended:
        with st.chat_message("assistant"):
            with st.spinner("Finding your perfect match..."):
                subset = product_df[['id', 'name', 'price', 'category']]
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": f"Our products: {subset.to_string()}\n\nTask: Recommend ONE product from the list. Start with 'Based on our conversation...'. Keep it natural and simple."}] + st.session_state.messages
                )
                final_advice = res.choices[0].message.content
                st.markdown(final_advice)
                st.session_state.messages.append({"role": "assistant", "content": final_advice})
                
                # --- 광고 배너: 추천 답변 바로 아래에만 딱 한 번 등장 ---
                render_final_ad(st.session_state.messages)
                
        st.balloons()
        st.success("✅ Interaction finished. Please return to Qualtrics and click 'Next'.")
