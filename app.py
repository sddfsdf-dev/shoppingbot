import streamlit as st
import pandas as pd
from openai import OpenAI
import time

# 1. OpenAI 설정
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Shopping Assistant", layout="centered")

# 2. URL 파라미터 읽기 (2x3 디자인)
query_params = st.query_params
group_id = query_params.get("group", "1")

# 실험 조건 설정
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

# --- [핵심] 구글 배너 스타일 광고 렌더링 함수 ---
def render_separated_ad(user_context, recommended_item_name):
    # GPT를 사용해 광고용 데이터 생성
    ad_res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"The AI recommended '{recommended_item_name}'. Pick a DIFFERENT competitor product. Format: Headline | Description | Price. Plain text only."}
        ] + user_context
    )
    try:
        raw_content = ad_res.choices[0].message.content.replace('*', '')
        parts = raw_content.split('|')
        headline = parts[0].strip()
        description = parts[1].strip() if len(parts) > 1 else "Premium selection for you."
        price = parts[2].strip() if len(parts) > 2 else ""

        # 제어권(X 버튼) UI
        ctrl_html = '<div style="text-align:right; font-size:12px; color:#aaa; cursor:pointer; margin-bottom:-10px;">✕ Hide</div>' if is_controllable else ''

        st.markdown(f"""
            <div style="border: 1px solid #dadce0; background-color: #ffffff; padding: 18px; margin: 20px 0; border-radius: 8px; font-family: 'Arial', sans-serif; box-shadow: 0 1px 6px rgba(32,33,36,0.15);">
                {ctrl_html}
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <span style="background: #202124; color: white; font-size: 10px; padding: 1px 5px; border-radius: 3px; font-weight: bold; margin-right: 8px;">AD</span>
                    <span style="color: #202124; font-size: 12px; font-weight: 500;">Sponsored Alternative</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="flex: 1; padding-right: 15px;">
                        <div style="color: #1a0dab; font-size: 17px; font-weight: 500; margin-bottom: 3px;">{headline}</div>
                        <div style="color: #4d5156; font-size: 13px; line-height: 1.4;">{description}</div>
                        <div style="color: #d93025; font-size: 15px; font-weight: bold; margin-top: 5px;">{price}</div>
                    </div>
                    <div style="background-color: #1a73e8; color: white; padding: 8px 16px; font-size: 13px; border-radius: 4px; font-weight: 500;">Shop Now</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    except:
        pass

# 4. 세션 초기화 및 대화 기록 표시
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm here to help you shop. **1. What product category are you looking for?**"}]
if "turn" not in st.session_state: st.session_state.turn = 1
if "finished" not in st.session_state: st.session_state.finished = False

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

# 5. 대화 로직 (turn 1~3)
if not st.session_state.finished:
    if prompt := st.chat_input("Type your answer here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                time.sleep(1.2)
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

# 6. 최종 답변 및 광고 (2x3 분기)
if st.session_state.finished:
    is_already_responded = any("Based on" in m["content"] or "[AD]" in m["content"] for m in st.session_state.messages)
    
    if not is_already_responded:
        with st.chat_message("assistant"):
            with st.spinner("Finding your perfect match..."):
                time.sleep(2.0)
                
                # 프롬프트 설정
                if ad_pos == "in-text":
                    sys_instr = "Recommend ONE product. The ENTIRE response must be a persuasive ad. Start with '[AD] Sponsored Recommendation:'."
                elif ad_pos == "following":
                    sys_instr = "Recommend one product neutrally. Then, start a new paragraph with 'By the way, [AD]...' and recommend a different premium product."
                else: # separated
                    sys_instr = "Recommend ONE product from the list in a neutral, objective plain text."

                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages
                )
                final_advice = res.choices[0].message.content.replace('*', '')
                
                # 제어권(Control) UI - 텍스트 상단에 표시
                if is_controllable and ad_pos in ["in-text", "following"]:
                    st.markdown('<div style="text-align:right; font-size:10px; color:#ccc;">✕ Hide Ad</div>', unsafe_allow_html=True)
                
                st.markdown(final_advice)
                st.session_state.messages.append({"role": "assistant", "content": final_advice})
                
                # [Separated 조건] 답변이 나온 후, 그 바로 아래 배너 생성
                if ad_pos == "separated":
                    render_separated_ad(st.session_state.messages, final_advice)
                
        st.balloons()
        st.caption("✅ Please return to Qualtrics and click 'Next'.")
