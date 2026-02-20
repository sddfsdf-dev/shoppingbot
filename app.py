import streamlit as st
import pandas as pd
from openai import OpenAI

# 1. Setup
# Secrets에 저장한 OPENAI_API_KEY를 불러옵니다.
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Shopping Assistant", layout="centered")

# CSS 오타 수정: unsafe_allow_html=True
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stChatMessage { border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛍️ Personal AI Shopper")

# 2. Load Data
@st.cache_data
def load_data():
    try:
        # GitHub에 올린 products.csv를 읽어옵니다.
        df = pd.read_csv('products.csv')
        return df
    except:
        return None

product_df = load_data()

if product_df is None:
    st.error("⚠️ 'products.csv' 파일을 찾을 수 없습니다. GitHub에 업로드했는지 확인해주세요!")
    st.stop()

# 3. Chat Session
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm your personal shopping assistant. What are you looking for today?"}
    ]
if "turn" not in st.session_state:
    st.session_state.turn = 0

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. Logic
if st.session_state.turn < 3:
    if prompt := st.chat_input("Type here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "You are a shopping assistant. Ask a short follow-up question."}] + st.session_state.messages
            )
            ai_msg = response.choices[0].message.content
            st.markdown(ai_msg)
            st.session_state.messages.append({"role": "assistant", "content": ai_msg})
            st.session_state.turn += 1
            if st.session_state.turn == 3:
                st.rerun()
else:
    st.divider()
    with st.spinner("Finding the best match..."):
        # GPT에게 추천 받기
        subset = product_df[['id', 'name', 'price', 'keywords']]
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Pick the best product ID from this list: \n{subset.to_string()}\n\nReturn ONLY the ID number."}
            ] + st.session_state.messages
        )
        try:
            best_id = int(res.choices[0].message.content.strip())
            item = product_df[product_df['id'] == best_id].iloc[0]
            
            st.subheader("🎯 Recommendation")
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(item['img_url'])
            with col2:
                st.write(f"### {item['name']}")
                st.write(f"**Price:** ${item['price']}")
                st.success("This is the perfect match for you!")
        except:
            st.write("Done! Check the survey for results.")
    
    st.warning("Please click the 'Next' button in Qualtrics.")
