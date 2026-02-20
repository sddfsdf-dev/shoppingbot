import streamlit as st
import pandas as pd
from openai import OpenAI

# 1. OpenAI 설정 (Secrets 확인 필수)
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception as e:
    st.error("OpenAI API Key가 설정되지 않았습니다. Secrets를 확인해주세요.")
    st.stop()

st.set_page_config(page_title="AI Shopping Assistant", layout="centered")

# CSS 수정 (unsafe_allow_html=True 가 올바른 문법입니다)
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stChatMessage { border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛍️ Personal AI Shopper")

# 2. 데이터 로드
@st.cache_data
def load_data():
    try:
        # 이미 products.csv로 만드셨으니 그대로 읽어옵니다.
        df = pd.read_csv('products.csv')
        return df
    except Exception as e:
        return None

product_df = load_data()

# 파일 로드 실패 시 에러 메시지
if product_df is None:
    st.error("⚠️ 'products.csv' 파일을 읽을 수 없습니다. 파일 내용이 비어있거나 형식이 잘못되었는지 확인해주세요.")
    st.stop()

# 3. 채팅 세션 관리
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm your personal shopping assistant. How can I help you today?"}
    ]
if "turn" not in st.session_state:
    st.session_state.turn = 0

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. 대화 로직 (3턴 제한)
if st.session_state.turn < 3:
    if prompt := st.chat_input("Type your message here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "You are a helpful shopping assistant. Ask a short follow-up question."}] + st.session_state.messages
                )
                ai_msg = response.choices[0].message.content
                st.markdown(ai_msg)
                st.session_state.messages.append({"role": "assistant", "content": ai_msg})
                st.session_state.turn += 1
                if st.session_state.turn == 3:
                    st.rerun()
            except Exception as e:
                st.error(f"AI 응답 생성 중 오류 발생: {e}")

else:
    # 5. 최종 추천 화면
    st.divider()
    with st.spinner("Finding the best match for you..."):
        # GPT에게 CSV 데이터를 요약해서 전달
        subset = product_df[['id', 'name', 'price', 'keywords']]
        try:
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"Based on the dialogue, pick the best product ID from this list: \n{subset.to_string()}\n\nReturn ONLY the ID number (e.g., 5)."}
                ] + st.session_state.messages
            )
            
            best_id_str = res.choices[0].message.content.strip()
            # 숫자가 아닌 문자열이 섞여 있을 경우를 대비해 숫자만 추출
            best_id = int(''.join(filter(str.isdigit, best_id_str)))
            item = product_df[product_df['id'] == best_id].iloc[0]
            
            st.subheader("🎯 AI Expert's Choice")
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(item['img_url'])
            with col2:
                st.write(f"### {item['name']}")
                st.write(f"**Price:** ${item['price']}")
                st.success("This is the perfect match for your needs!")
        except Exception as e:
            st.info("Great! We've found a perfect item for you. Please proceed to the next page.")

    st.warning("Please click the 'Next' button in your Qualtrics survey.")
