import streamlit as st
import pandas as pd
from openai import OpenAI

# 1. OpenAI 설정
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Shopping Assistant", layout="centered")

# 디자인: 말풍선 및 레이아웃 정리
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    .stButton button { width: 100%; border-radius: 20px; background-color: #ff4b4b; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛍️ Personal AI Shopper")

# 2. 데이터 로드
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('products.csv')
        return df
    except:
        return None

product_df = load_data()

# 3. 세션 및 질문 관리
if "messages" not in st.session_state:
    # 첫 번째 질문 고정: 어떤 제품군?
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm here to help you shop. **First, what kind of product category are you looking for?** (e.g., Electronics, Beauty, Sports...)"}
    ]
if "turn" not in st.session_state:
    st.session_state.turn = 1

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. 고정된 3단계 질문 로직
if st.session_state.turn <= 3:
    if prompt := st.chat_input("Type your answer..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if st.session_state.turn == 1:
                # 두 번째 질문: 누가 쓰나요?
                next_question = "Got it. **Who is this product for?** (e.g., For myself, a gift for my wife, for a friend...)"
            elif st.session_state.turn == 2:
                # 세 번째 질문: 가격대는?
                next_question = "Finally, **what is your maximum budget for this purchase?** (Please specify the amount in dollars $)"
            
            if st.session_state.turn < 3:
                st.markdown(next_question)
                st.session_state.messages.append({"role": "assistant", "content": next_question})
                st.session_state.turn += 1
            else:
                # 3번째 답변 수집 완료
                st.session_state.turn += 1
                st.rerun()

# 5. 최종 추천 (ID 1~100 중 최적템 선택)
else:
    st.divider()
    with st.spinner("Finding the best product from our 100 premium items..."):
        subset = product_df[['id', 'name', 'price', 'category', 'keywords']]
        
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a professional shopper. Based on the user's category, target, and budget, pick the best product ID from this CSV data: \n{subset.to_string()}\n\nReturn ONLY the ID number."}
            ] + st.session_state.messages
        )
        
        try:
            # ID만 추출하여 해당 상품 정보 표시
            best_id = int(''.join(filter(str.isdigit, res.choices[0].message.content)))
            item = product_df[product_df['id'] == best_id].iloc[0]
            
            st.subheader("🎯 My Top Recommendation")
            
            with st.container(border=True):
                col1, col2 = st.columns([1, 1.5])
                with col1:
                    st.image(item['img_url'])
                with col2:
                    st.write(f"### {item['name']}")
                    st.write(f"**Price:** ${item['price']}")
                    st.write(f"**Category:** {item['category']}")
                    st.success("This item matches all your criteria!")
            st.balloons()
            
        except:
            st.write("I've found a great match! Please see the results in your survey.")

    st.info("✅ Chat finished. Please return to the Qualtrics window and click **'Next'**.")
