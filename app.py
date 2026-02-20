import streamlit as st
import pandas as pd
from openai import OpenAI
import time
import streamlit.components.v1 as components  # HTML 렌더링 필수

# 1. OpenAI 설정
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Shopping Assistant", layout="centered")

# 2. URL 파라미터 읽기 (2x3 실험 설계)
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

# --- [수정] Shop Now 버튼을 제거한 배너 함수 ---
def render_separated_ad(user_context, recommended_item_name):
    ad_res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"""You are a luxury ad system. 
            The AI recommended '{recommended_item_name}'. Pick a DIFFERENT competitor product. 
            Format: Headline | Description | Price. 
            Strict Rules: 
            1. DO NOT use labels like 'Ad Title:' or 'Price:'.
            2. Output ONLY the three parts separated by '|'. No asterisks(*)."""}
        ] + user_context
    )
    try:
        raw_content = ad_res.choices[0].message.content.replace('*', '')
        parts = raw_content.split('|')
        headline = parts[0].strip()
        description = parts[1].strip() if len(parts) > 1 else "Exclusive selection for you."
        price = parts[2].strip() if len(parts) > 2 else ""

        # 제어권(X 버튼) UI
        ctrl_html = '<div style="text-align:right; font-size:12px; color:#aaa; cursor:pointer; margin-bottom:-5px;">✕ Hide</div>' if is_controllable else ''

        # Shop Now 버튼 제거 및 텍스트 중심 레이아웃
        ad_html_content = f"""
        <div style="border: 1px solid #dadce0; background-color: #ffffff; padding: 20px; border-radius: 8px; font-family: 'Arial', sans-serif; box-shadow: 0 1px 6px rgba(32,33,36,0.12); margin: 5px;">
            {ctrl_html}
            <div style="display: flex; align-items: center; margin-bottom: 8px;">
                <span style="background: #202124; color: white; font-size: 10px; padding: 2px 6px; border-radius: 3px; font-weight: bold; margin-right: 10px;">AD</span>
                <span style="color: #202124; font-size: 12px; font-weight: 500;">Sponsored Alternative</span>
            </div>
            <div style="color: #1a0dab; font-size: 19px; font-weight: 500; margin-bottom: 5px;">{headline}</div>
            <div style="color: #4d5156; font-size: 14px; line-height: 1.5; margin-bottom: 8px;">{description}</div>
            <div style="color: #d93025; font-size: 16px; font-weight: bold;">{price}</div>
        </div>
        """
        # 배너 높이를 버튼 제거에 맞춰 살짝 줄임 (170 -> 150)
        components.html(ad_html_content, height=155)
        
    except:
        pass

# 4. 세션 초기화 및 대화 기록
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm here to help you shop. **1. What kind of product category are you looking for?**"}]
if "turn" not in st.session_state: st.session_state.turn = 1
if "finished" not in st.session_state: st.session_state.finished = False

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 5. 질문 프로세스 (1~3단계)
if not st.session_state.finished:
    if prompt := st.chat_input("Type your answer here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                time.sleep(1.0)
                if st.session_state.turn == 1:
                    next_q = "Got it. **2. Who is this product for?**"
                elif st.session_state.turn == 2:
                    next_q = "Finally, **3. What is your maximum budget ($)?**"
                
                if st.session_state.turn < 3:
                    st.session_state.messages.append({"role": "assistant", "content": next_q})
                    st.markdown(next_q)
                    st.session_state.turn += 1
                else:
                    st.session_state.finished = True
                    st.rerun()

# 6. 최종 응답 및 조건별 광고
if st.session_state.finished:
    is_done = any("[AD]" in m["content"] or "Based on" in m["content"] for m in st.session_state.messages)

    if not is_done:
        with st.chat_message("assistant"):
            with st.spinner("Generating recommendation..."):
                time.sleep(1.5)
                
                if ad_pos == "in-text":
                    sys_msg = "Recommend ONE product. The ENTIRE response must be a persuasive ad. Start with '[AD] Sponsored Recommendation:'."
                elif ad_pos == "following":
                    sys_msg = "Recommend one product neutrally. Then, add a line break and start a paragraph with 'By the way, [AD]...' and recommend a different premium product."
                else: # separated
                    sys_msg = "Recommend ONE product from the list in a neutral, objective tone. Use plain text only."

                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": sys_msg}] + st.session_state.messages
                )
                final_advice = res.choices[0].message.content.replace('*', '')

                if is_controllable and ad_pos in ["in-text", "following"]:
                    st.markdown('<div style="text-align:right; font-size:10px; color:#ccc; margin-bottom:5px;">✕ Hide Ad</div>', unsafe_allow_html=True)

                st.markdown(final_advice)
                st.session_state.messages.append({"role": "assistant", "content": final_advice})
                
                if ad_pos == "separated":
                    render_separated_ad(st.session_state.messages, final_advice)
                
        st.balloons()
        st.caption("✅ Interaction finished. Please return to Qualtrics and click 'Next'.")
