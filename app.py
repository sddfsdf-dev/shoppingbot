import streamlit as st
import pandas as pd
from openai import OpenAI
import re

# 1. OpenAI 설정
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Shopping Assistant", layout="centered")

# --- [추가] 실시간 배너 광고 로직 ---
def display_ad_banner():
    # 유저의 최신 입력값(쿼리) 확인
    user_query = ""
    if "messages" in st.session_state:
        # 유저가 보낸 메시지들만 수집
        user_msgs = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
        if user_msgs:
            user_query = " ".join(user_msgs).lower()

    # 광고 데이터베이스 (키워드 매칭)
    ads = [
        {"keyword": "perfume", "text": "✨ Luxury Fragrance Sale: Up to 30% Off!", "color": "#f8ecec"},
        {"keyword": "tennis", "text": "🎾 Pro Racket Collection - New Arrivals", "color": "#eef8ec"},
        {"keyword": "electronic", "text": "💻 Tech Week: Best Deals on Gadgets", "color": "#ececf8"},
        {"keyword": "gift", "text": "🎁 Perfect Gifts for Your Loved Ones", "color": "#fff4e6"},
        {"keyword": "beauty", "text": "💄 K-Beauty Essentials: Get Glowing Skin", "color": "#fdf2f8"}
    ]

    # 기본 광고 (매칭되는 게 없을 때)
    selected_ad = {"text": "🚚 Free Shipping on all orders over $50!", "color": "#f0f2f6"}

    # 유저 쿼리에 맞는 광고 검색
    for ad in ads:
        if ad["keyword"] in user_query:
            selected_ad = ad
            break

    # 배너 HTML 출력 (상단 고정 스타일)
    st.markdown(f"""
        <div style="
            background-color: {selected_ad['color']};
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #ddd;
            text-align: center;
            margin-bottom: 25px;
            font-weight: bold;
            color: #333;
            animation: fadeIn 0.5s;
        ">
            {selected_ad['text']}
        </div>
        <style>
            @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
        </style>
    """, unsafe_allow_html=True)

# 2. 데이터 로드
@st.cache_data
def load_data():
    for f in ['products.csv', 'product.csv']:
        try: return pd.read_csv(f)
        except: continue
    return None

product_df = load_data()

# --- 화면 최상단에 배너 표시 ---
display_ad_banner()

st.title("🛍️ Personal AI Shopper")

# 3. 세션 상태 및 4. 대화 로직 (이하 기존 코드와 동일)
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm here to help you shop. **1. What kind of product category are you looking for?**"}]
if "turn" not in st.session_state: st.session_state.turn = 1
if "finished" not in st.session_state: st.session_state.finished = False

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if not st.session_state.finished:
    if prompt := st.chat_input("Type your answer here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        # 배너를 즉시 갱신하기 위해 새로고침 효과
        
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

# 5. 추천 결과
if st.session_state.finished:
    with st.chat_message("assistant"):
        with st.spinner("Writing my recommendation..."):
            subset = product_df[['id', 'name', 'price', 'category']]
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "You are a professional shopper. Recommend one clear product. Avoid messy formatting. Use plain English."}] + st.session_state.messages
            )
            final_advice = res.choices[0].message.content
            st.markdown(final_advice)
            st.session_state.messages.append({"role": "assistant", "content": final_advice})
    st.balloons()
    st.caption("✅ Interaction finished. Please return to Qualtrics and click 'Next'.")
