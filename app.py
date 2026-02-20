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
    try:
        return pd.read_csv('products.csv')
    except:
        return None

product_df = load_data()

# 3. 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm here to help you shop. **1. What kind of product category are you looking for?** (e.g., Electronics, Beauty, Sports...)"}
    ]
if "turn" not in st.session_state:
    st.session_state.turn = 1
if "finished" not in st.session_state:
    st.session_state.finished = False

# 대화 기록 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. 대화 및 추천 로직
if not st.session_state.finished:
    if prompt := st.chat_input("Type your answer here..."):
        # 유저 메시지 기록
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 질문 단계별 처리
        if st.session_state.turn == 1:
            next_msg = "Got it. **2. Who is this product for?** (e.g., For myself, a gift for my wife, for a friend...)"
            st.session_state.messages.append({"role": "assistant", "content": next_msg})
            with st.chat_message("assistant"):
                st.markdown(next_msg)
            st.session_state.turn += 1
        
        elif st.session_state.turn == 2:
            next_msg = "Finally, **3. What is your maximum budget in dollars ($)?**"
            st.session_state.messages.append({"role": "assistant", "content": next_msg})
            with st.chat_message("assistant"):
                st.markdown(next_msg)
            st.session_state.turn += 1
            
        elif st.session_state.turn == 3:
            # 3번째 답을 받으면 바로 종료 상태로 변경하고 새로고침
            st.session_state.finished = True
            st.rerun()

# 5. 추천 결과 출력 (finished가 True일 때만 실행)
if st.session_state.finished:
    st.divider()
    with st.spinner("Analyzing our 100 products to find the perfect match..."):
        # GPT에게 보낼 데이터 요약
        subset = product_df[['id', 'name', 'price', 'category', 'keywords']]
        
        try:
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"You are a professional shopper. Based on the dialogue, pick the best product ID from this list: \n{subset.to_string()}\n\nReturn ONLY the ID number (e.g., 7)."}
                ] + st.session_state.messages
            )
            
            # 숫자만 추출하는 더 강력한 방법
            ans = res.choices[0].message.content
            best_id = int(re.search(r'\d+', ans).group())
            item = product_df[product_df['id'] == best_id].iloc[0]
            
            # 추천 카드 출력
            st.subheader("🎯 My Top Recommendation for You")
            with st.container(border=True):
                col1, col2 = st.columns([1, 1.5])
                with col1:
                    st.image(item['img_url'])
                with col2:
                    st.write(f"### {item['name']}")
                    st.write(f"**Price:** ${item['price']}")
                    st.write(f"**Category:** {item['category']}")
                    st.info(f"This {item['name']} is the best fit for your request and budget.")
            st.balloons()
            
        except Exception as e:
            st.error("I found a great match, but had a slight issue displaying it. Please refer to the survey!")

    st.warning("✅ Interaction finished. Please return to Qualtrics and click **'Next'**.")
