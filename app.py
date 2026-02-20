import streamlit as st
import pandas as pd
from openai import OpenAI

# 1. API 키 설정 (Streamlit Secrets에서 가져옴)
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Shopping Assistant", layout="centered")

# CSS로 디자인 살짝 다듬기
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stChatMessage { border-radius: 15px; }
    </style>
    """, unsafe_allow_value=True)

st.title("🛍️ Personal AI Shopper")
st.write("I will find the best product for you from our 100+ premium collection.")

# 2. CSV 데이터 로드 함수
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('products.csv')
        return df
    except Exception as e:
        st.error(f"Error loading products.csv: {e}")
        return None

product_df = load_data()

# 3. 세션 상태(대화 기록) 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm your personal shopping assistant. What are you looking for today? (e.g., a gift for my boyfriend, a luxury perfume, etc.)"}
    ]
if "turn" not in st.session_state:
    st.session_state.turn = 0

# 대화 기록 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. 채팅 로직 (최대 3번의 질문 주고받기)
if st.session_state.turn < 3:
    if prompt := st.chat_input("Enter your request here..."):
        # 유저 메시지 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI 응답 생성
        with st.chat_message("assistant"):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a friendly shopping assistant. Ask brief follow-up questions to understand user's preference and budget. Keep it short."}
                ] + st.session_state.messages
            )
            ai_msg = response.choices[0].message.content
            st.markdown(ai_msg)
            st.session_state.messages.append({"role": "assistant", "content": ai_msg})
            st.session_state.turn += 1
            
            # 3턴이 끝나면 바로 결과 화면으로 넘어가기 위해 리런
            if st.session_state.turn == 3:
                st.rerun()

# 5. 최종 추천 결과 화면 (3턴 종료 후)
else:
    st.divider()
    st.subheader("🎯 My Best Recommendation for You")
    
    with st.spinner("Analyzing our 100 products to find the perfect match..."):
        # GPT가 CSV 데이터를 보고 가장 적합한 ID를 고르게 함
        products_info = product_df[['id', 'name', 'price', 'keywords', 'price_limit']].to_string()
        
        recommend_res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Based on the conversation, pick the best product ID from this list: \n{products_info}\n\n Return ONLY the ID number."},
            ] + st.session_state.messages
        )
        
        try:
            best_id = int(recommend_res.choices[0].message.content.strip())
            item = product_df[product_df['id'] == best_id].iloc[0]
            
            # 결과 카드 표시
            col1, col2 = st.columns([1, 1.5])
            with col1:
                st.image(item['img_url'], use_container_width=True)
            with col2:
                st.write(f"### {item['name']}")
                st.write(f"**Price:** ${item['price']}")
                st.write(f"**Category:** {item['category']}")
                st.info("This product perfectly matches your preferences and budget.")
                
        except:
            st.write("I found a great match for you, but I had trouble displaying the image. Please check our catalog!")

    st.success("Thank you for chatting! Please click the 'Next' button in the Qualtrics survey to continue.")
