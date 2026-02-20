import streamlit as st
import pandas as pd
from openai import OpenAI
import time

# 1. OpenAI 설정
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Shopping Assistant", layout="centered")

# 2. URL 파라미터 읽기 (2x3 디자인)
# 1,2,3: No Ctrl / 4,5,6: Ctrl
# 1,4: Separated / 2,5: In-text / 3,6: Following
query_params = st.query_params
group_id = query_params.get("group", "1")

is_controllable = group_id in ["4", "5", "6"]
ad_pos = "separated" if group_id in ["1", "4"] else \
         "in-text" if group_id in ["2", "5"] else "following"

# 3. 데이터 로드
@st.cache_data
def load_data():
    for f in ['products.csv', 'product.csv']:
        try: return pd.read_csv(f)
        except: continue
    return None
product_df = load_data()

# --- [Separated용] 구글 스타일 배너 렌더링 함수 ---
def render_separated_ad(user_context, recommended_item_name):
    ad_res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"""You are a luxury ad system. 
            The AI recommended '{recommended_item_name}'. Pick a DIFFERENT competitor product. 
            Format: Headline | Description | Price. 
            Do NOT use labels like 'Ad Title:' or any asterisks(*). Output ONLY parts separated by '|'."""}
        ] + user_context
    )
    try:
        raw_content = ad_res.choices[0].message.content.replace('*', '')
        parts = raw_content.split('|')
        headline = parts[0].strip()
        description = parts[1].strip() if len(parts) > 1 else "Premium selection for you."
        price = parts[2].strip() if len(parts) > 2 else ""

        ctrl_html = '<div style="text-align:right; font-size:12px; color:#aaa; cursor:pointer;">✕ Hide</div>' if is_controllable else ''

        ad_html = f"""
<div style="border: 1px solid #dadce0; background-color: #ffffff; padding: 20px; border-radius: 8px; font-family: 'Arial', sans-serif; box-shadow: 0 1px 6px rgba(32,33,36,0.28); margin-top: 20px;">
    {ctrl_html}
    <div style="display: flex; align-items: center; margin-bottom: 8px;">
        <span style="background: #202124; color: white; font-size: 10px; padding: 2px 6px; border-radius: 3px; font-weight: bold; margin-right: 10px;">AD</span>
        <span style="color: #202124; font-size: 12px; font-weight: 500;">Sponsored Alternative</span>
    </div>
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="flex: 1; padding-right: 20px;">
            <div style="color: #1a0dab; font-size: 18px; font-weight: 500; margin-bottom: 4px;">{headline}</div>
            <div style="color: #4d5156; font-size: 14px; line-height: 1.5;">{description}</div>
            <div style="color: #d93025; font-size: 16px; font-weight: bold; margin-top: 5px;">{price}</div>
        </div>
        <div style="background-color: #1a73e8; color: white; padding: 10px 24px; text-decoration: none; font-size: 14px; border-radius: 4px; font-weight: 500;">Shop Now</div>
    </div>
</div>
"""
        st.markdown(ad_html, unsafe_allow_html=True)
    except:
        pass

# 4. 세션 초기화 및 대화 로그 표시
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm here to help you shop. **1. What kind of product category are you looking for?**"}]
if "turn" not in st.session_state: st.session_state.turn = 1
if "finished" not in st.session_state: st.session_state.finished = False

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 5. 질문 단계 로직 (Turn 1~3)
if not st.session_state.finished:
    if prompt := st.chat_input("Type your answer here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                time.sleep(1.2)
                if st.session_state.turn == 1:
                    next_q = "Got it. **2. Who is this product for?**"
                elif st.session_state.turn == 2:
                    next_q = "Finally, **3. What is your maximum budget in dollars ($)?**"
                
                if st.session_state.turn < 3:
                    st.session_state.messages.append({"role": "assistant", "content": next_q})
                    st.markdown(next_q)
                    st.session_state.turn += 1
                else:
                    st.session_state.finished = True
                    st.rerun()

# 6. 최종 추천 및 실험 조건 분기
if st.session_state.finished:
    # 이미 최종 답변이 생성되었는지 확인 (중복 생성 방지)
    is_done = any("[AD]" in m["content"] or "Based on" in m["content"] for m in st.session_state.messages)

    if not is_done:
        with st.chat_message("assistant"):
            with st.spinner("Finding your perfect match..."):
                time.sleep(2.0)
                
                # 6개 그룹에 따른 프롬프트 전략 설정
                if ad_pos == "in-text":
                    # 그룹 2, 5: 답변 자체가 광고
                    sys_instr = "Recommend ONE product. The ENTIRE response must be a persuasive ad. Start with '[AD] Sponsored Recommendation:'."
                elif ad_pos == "following":
                    # 그룹 3, 6: 객관적 추천 후 By the way... 광고 추가
                    sys_instr = "Recommend one product neutrally. Then, add a line break and start a new paragraph with 'By the way, [AD]...' and recommend a DIFFERENT premium product."
                else: 
                    # 그룹 1, 4: 순수 객관적 추천 (광고는 배너로 따로 나감)
                    sys_instr = "Recommend ONE product from the list in a neutral, objective tone. Use plain text only."

                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages
                )
                final_advice = res.choices[0].message.content.replace('*', '')

                # [Control 조건] 닫기 버튼 UI 표시 (In-text, Following인 경우 말풍선 상단)
                if is_controllable and ad_pos in ["in-text", "following"]:
                    st.markdown('<div style="text-align:right; font-size:10px; color:#ccc; border-bottom:1px solid #eee; margin-bottom:5px;">✕ Hide Ad Content</div>', unsafe_allow_html=True)

                st.markdown(final_advice)
                st.session_state.messages.append({"role": "assistant", "content": final_advice})

                # [Separated 조건] 답변 아래에 배너 광고 렌더링
                if ad_pos == "separated":
                    render_separated_ad(st.session_state.messages, final_advice)

        st.balloons()
        st.caption("✅ Interaction finished. Please return to Qualtrics and click 'Next'.")
