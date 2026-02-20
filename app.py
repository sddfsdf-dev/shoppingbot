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
        try:
            return pd.read_csv(f)
        except:
            continue
    return None

product_df = load_data()

# 3. 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm here to help you shop. **1. What kind of product category are you looking for?**"}
    ]
if "turn" not in st.session_state:
    st.session_state.turn = 1
if "finished" not in st.session_state:
    st.session_state.finished = False

# 대화 기록 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. 대화 로직
if not st.session_state.finished:
    if prompt := st.chat_input("Type your answer here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if st.session_state.turn == 1:
            next_q = "Got it. **2. Who is this product for?**"
            st.session_state.messages.append({"role": "assistant", "content": next_q})
            with st.chat_message("assistant"):
                st.markdown(next_q)
            st.session_state.turn += 1
        elif st.session_state.turn == 2:
            next_q = "Finally, **3. What is your maximum budget in dollars ($)?**"
            st.session_state.messages.append({"role": "assistant", "content": next_q})
            with st.chat_message("assistant"):
                st.markdown(next_q)
            st.session_state.turn += 1
        elif st.session_state.turn == 3:
            st.session_state.finished = True
            st.rerun()

# 5. 텍스트 기반 추천 로직 (이미지 제거)
if st.session_state.finished:
    st.divider()
    with st.spinner("Finding the best recommendation..."):
        subset = product_df[['id', 'name', 'price', 'category', 'keywords']]
        
        # GPT가 CSV 데이터를 참고하여 텍스트로만 추천 대답을 생성
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"""You are a professional shopper. 
                Below is our product list:
                {subset.to_string()}
                
                Task:
                1. If a matching product exists in the list, recommend it by name and price.
                2. If no exact match exists, use your own knowledge to recommend a suitable product.
                3. Provide the recommendation in a friendly, conversational text format. 
                4. DO NOT use image tags or markdown for images. Just text."""}
            ] + st.session_state.messages
        )
        
        recommendation_text = res.choices[0].message.content
        
        # 추천 결과 표시
        st.subheader("🎯 My Recommendation")
        with st.chat_message("assistant"):
            st.markdown(recommendation_text)
        
        st.balloons()

    st.success("✅ Interaction finished. Please return to Qualtrics and click 'Next'.")
