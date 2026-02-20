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
            with st.chat_message("assistant"):
                with st.spinner("Writing my recommendation..."):
                    subset = product_df[['id', 'name', 'price', 'category']]
                    res = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": f"""You are a professional shopper. 
                            Product list: {subset.to_string()}
                            
                            Instructions for clear text:
                            1. Recommend one clear product.
                            2. Do NOT use excessive asterisks like *** or multiple stars. Use simple bolding like **Product Name** only if necessary.
                            3. Add a blank line between sentences for readability.
                            4. If the product is not in the list, recommend the best one from your knowledge clearly.
                            5. Use plain, clean English. Avoid any messy formatting."""}
                        ] + st.session_state.messages
                    )
                    final_advice = res.choices[0].message.content
                    st.markdown(final_advice)
                    st.session_state.messages.append({"role": "assistant", "content": final_advice})
            
            st.session_state.finished = True
            st.balloons()

# 5. 종료 안내
if st.session_state.finished:
    st.caption("✅ Interaction finished. Please return to Qualtrics and click 'Next'.")
