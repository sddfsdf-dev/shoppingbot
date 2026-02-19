import streamlit as st
from openai import OpenAI

# 1. 초기 설정
client = OpenAI(api_key=st.secrets["sk-proj-534UQJ3xc38Co-zevRHlhJDc1WuzuGESkQiSfiyPw4nbRQ5Xq2AOcDBdwdZHUncwr-284v928ZT3BlbkFJuK4O_vQbZJ5PAeQrQPuZ1sNlIhSi9iYLBQIH5hx8DwUEMvFsa6TDIFoYNnIBX4tF7wdbQrY"])

st.set_page_config(page_title="Shopping AI", layout="centered")
st.title("🎁 AI 쇼핑 어시스턴트")

# 제품 데이터 (나중에 100개로 늘리면 됩니다)
products = [
    {"name": "Dior Perfume", "price": "$150", "desc": "럭셔리한 향기"},
    {"name": "ZARA Shirt", "price": "$40", "desc": "트렌디한 셔츠"}
]

if "messages" not in st.session_state:
    st.session_state.messages = []
if "turn" not in st.session_state:
    st.session_state.turn = 0

# 대화 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 3번의 대화 제한
if st.session_state.turn < 3:
    if prompt := st.chat_input("무엇을 찾으시나요?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": f"추천 대상 제품: {products}"}] + st.session_state.messages
            )
            ans = response.choices[0].message.content
            st.markdown(ans)
            st.session_state.messages.append({"role": "assistant", "content": ans})
            st.session_state.turn += 1
            if st.session_state.turn == 3: st.rerun()
else:
    st.success("대화가 완료되었습니다! 아래 추천 제품을 확인하세요.")
    st.info(f"추천 제품: {products[0]['name']} ({products[0]['price']})")
    # 여기에 나중에 데이터 저장(구글 시트) 코드가 들어갑니다.
