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

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. 대화 로직
if not st.session_state.finished:
    if prompt := st.chat_input("Type your answer..."):
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

# 5. 하이브리드 추천 로직 (CSV 우선 -> 없으면 GPT 자체 추천)
if st.session_state.finished:
    st.divider()
    with st.spinner("Finding the best match..."):
        subset = product_df[['id', 'name', 'price', 'category', 'keywords']]
        
        # GPT에게 판단 요청 (ID를 주거나, 없으면 'NONE'이라고 답하게 함)
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a professional shopper. Look at this list:\n{subset.to_string()}\n\n1. If a product matches the user's need, return ONLY the ID number.\n2. If NO product matches, return 'NONE' and provide a brief recommendation from your own knowledge."}
            ] + st.session_state.messages
        )
        
        ans = res.choices[0].message.content
        best_id_match = re.search(r'\d+', ans)

        # 케이스 A: CSV에서 찾은 경우
        if best_id_match and "NONE" not in ans.upper():
            try:
                best_id = int(best_id_match.group())
                item = product_df[product_df['id'] == best_id].iloc[0]
                
                st.subheader("🎯 Found a perfect match in our store!")
                with st.container(border=True):
                    c1, c2 = st.columns([1, 1.5])
                    with c1: st.image(item['img_url'], use_container_width=True)
                    with c2:
                        st.write(f"### {item['name']}")
                        st.write(f"**Price:** ${item['price']}")
                        st.info("This is the best choice from our premium collection.")
                st.balloons()
            except:
                st.error("Matching error. But I have an idea!")

        # 케이스 B: CSV에 없어서 GPT가 직접 추천하는 경우
        else:
            st.subheader("🌟 Special Recommendation for You")
            st.info("We don't have this exact item in our current CSV catalog, but based on my expert knowledge, here is what you should look for:")
            st.markdown(ans.replace("NONE", "").strip())
            st.caption("Tip: You can find similar items at major retailers within your budget.")

    st.success("✅ Interaction finished. Please click 'Next' in Qualtrics.")
