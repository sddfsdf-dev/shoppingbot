import streamlit as st
import pandas as pd
from openai import OpenAI

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

# --- [수정] 구글 배너 스타일 광고 출력 함수 ---
def render_ad_banner():
    user_query = ""
    if "messages" in st.session_state:
        user_msgs = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
        if user_msgs:
            user_query = " ".join(user_msgs).lower()

    # 광고 데이터 세트
    ads = [
        {"keyword": "perfume", "text": "Luxury Fragrance Sale: Up to 30% Off!", "link": "https://google.com"},
        {"keyword": "tennis", "text": "Pro Racket Collection - New Arrivals", "link": "https://google.com"},
        {"keyword": "electronic", "text": "Tech Week: Best Deals on Gadgets", "link": "https://google.com"},
        {"keyword": "gift", "text": "Perfect Gifts for Your Loved Ones", "link": "https://google.com"}
    ]

    selected_ad = {"text": "Free Shipping on all orders over $50!", "link": "https://google.com"}
    for ad in ads:
        if ad["keyword"] in user_query:
            selected_ad = ad
            break

    # 구글 배너 애드 스타일 CSS (답변 바로 밑에 위치)
    st.markdown(f"""
        <div style="
            border: 1px solid #e0e0e0;
            background-color: #fafafa;
            padding: 10px 15px;
            margin-top: -10px;
            margin-bottom: 20px;
            border-radius: 5px;
            font-family: 'Arial', sans-serif;
        ">
            <div style="color: #5f6368; font-size: 10px; margin-bottom: 5px; font-weight: bold;">[AD]</div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #1a0dab; font-size: 14px; font-weight: 500;">{selected_ad['text']}</span>
                <a href="{selected_ad['link']}" target="_blank" style="
                    background-color: #1a73e8;
                    color: white;
                    padding: 5px 12px;
                    text-decoration: none;
                    font-size: 12px;
                    border-radius: 4px;
                ">Visit</a>
            </div>
        </div>
    """, unsafe_allow_html=True)

# 3. 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm here to help you shop. **1. What kind of product category are you looking for?**"}]
if "turn" not in st.session_state: st.session_state.turn = 1
if "finished" not in st.session_state: st.session_state.finished = False

# 4. 대화 기록 및 광고 출력
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
    
    # AI의 답변(assistant) 바로 다음에 광고 배너 삽입
    if msg["role"] == "assistant":
        # 첫 번째 인사는 광고 제외하고 싶다면 i > 0 조건을 추가하세요
        render_ad_banner()

# 5. 입력 로직
if not st.session_state.finished:
    if prompt := st.chat_input("Type your answer..."):
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

# 6. 최종 추천 결과
if st.session_state.finished and len(st.session_state.messages) < 7: # 추천 메시지가 중복 생성되지 않게 제어
    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            subset = product_df[['id', 'name', 'price', 'category']]
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "You are a professional shopper. Recommend one clear product. No messy formatting."}] + st.session_state.messages
            )
            final_advice = res.choices[0].message.content
            st.markdown(final_advice)
            st.session_state.messages.append({"role": "assistant", "content": final_advice})
            st.rerun()
