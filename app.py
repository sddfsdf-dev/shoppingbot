import streamlit as st
import pandas as pd
from openai import OpenAI
import time

# 1. OpenAI 설정
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Shopping Assistant", layout="centered")

# 2. URL 파라미터 읽기
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

# --- [수정] Separated 배너 전용 함수 (HTML 렌더링 최적화) ---
def render_separated_ad(user_context, recommended_item_name):
    ad_res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"""You are a luxury ad system. 
            The AI recommended '{recommended_item_name}'. Pick a DIFFERENT competitor product. 
            Format: Headline | Description | Price. 
            Strict Rules: 
            1. DO NOT use labels like 'Ad Title:' or 'Description:'.
            2. DO NOT use any asterisks (*) or bold marks.
            3. Output ONLY the three parts separated by '|'."""}
        ] + user_context
    )
    try:
        raw_content = ad_res.choices[0].message.content.replace('*', '')
        parts = raw_content.split('|')
        headline = parts[0].strip()
        description = parts[1].strip() if len(parts) > 1 else "Exclusive premium selection."
        price = parts[2].strip() if len(parts) > 2 else ""

        # 제어권(X 버튼)
        ctrl_html = f'<div style="text-align:right; font-size:12px; color:#aaa; cursor:pointer; margin-bottom:-5px;">✕ Hide</div>' if is_controllable else ''

        # HTML 문자열을 변수에 담아 한 번에 렌더링 (들여쓰기 주의)
        ad_html = f"""
<div style="border: 1px solid #dadce0; background-color: #ffffff; padding: 20px; border-radius: 8px; font-family: 'Arial', sans-serif; box-shadow: 0 1px 6px rgba(32,33,36,0.28); margin-top: 20px; margin-bottom: 20px;">
    {ctrl_html}
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <span style="background: #202124; color: white; font-size: 10px; padding: 2px 6px; border-radius: 3px; font-weight: bold; margin-right: 10px;">AD</span>
        <span style="color: #202124; font-size: 12px; font-weight: 500;">Sponsored Alternative</span>
    </div>
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="flex: 1; padding-right: 20px;">
            <div style="color: #1a0dab; font-size: 18px; font-weight: 500; margin-bottom: 5px;">{headline}</div>
            <div style="color: #4d5156; font-size: 14px; line-height: 1.5;">{description}</div>
            <div style="color: #d93025; font-size: 16px; font-weight: bold; margin-top: 5px;">{price}</div>
        </div>
        <div style="background-color: #1a73e8; color: white; padding: 10px 20px; border-radius: 4px; font-weight: 500; font-size: 14px; cursor: pointer;">Shop Now</div>
    </div>
</div>
"""
        # unsafe_allow_html=True 옵션이 반드시 들어가야 함
        st.markdown(ad_html, unsafe_allow_html=True)
    except:
        st.error("Ad generation error.")

# 4. 세션 초기화 및 대화 로그
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm here to help you shop. **What product category are you looking for?**"}]
if "turn" not in st.session_state: st.session_state.turn = 1
if "finished" not in st.session_state: st.session_state.finished = False

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 5. 대화 진행 로직
if not st.session_state.finished:
    if prompt := st.chat_input("Type your answer here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                time.sleep(1.2)
                if st.session_state.turn == 1:
                    next_q = "Got it. **Who is this product for?**"
                elif st.session_state.turn == 2:
                    next_q = "Finally, **What is your maximum budget ($)?**"
                
                if st.session_state.turn < 3:
                    st.session_state.messages.append({"role": "assistant", "content": next_q})
                    st.markdown(next_q)
                    st.session_state.turn += 1
                else:
                    st.session_state.finished = True
                    st.rerun()

# 6. 최종 답변 및 실험 조건별 광고 출력
if st.session_state.finished:
    # 이미 응답했는지 확인
    is_already_responded = any("[AD]" in m["content"] or "Based on" in m["content"] for m in st.session_state.messages)
    
    if not is_already_responded:
        with st.chat_message("assistant"):
            with st.spinner("Finding your perfect match..."):
                time.sleep(1.5)
                
                # 프롬프트 분기
                if ad_pos == "in-text":
                    sys_instr = "Recommend ONE product. The ENTIRE response must be a persuasive ad. Start with '[AD] Sponsored Recommendation:'."
                elif ad_pos == "following":
                    sys_instr = "Recommend one product neutrally. Then, start a new paragraph with 'By the way, [AD]...' and recommend a different premium product."
                else: # separated
                    sys_instr = "Recommend ONE product from the list in a neutral, objective tone. Use PLAIN TEXT ONLY."

                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages
                )
                final_advice = res.choices[0].message.content.replace('*', '')

                # 인텍스트/팔로잉 제어권 표시
                if is_controllable and ad_pos in ["in-text", "following"]:
                    st.markdown('<div style="text-align:right; font-size:10px; color:#ccc; margin-bottom: 5px;">✕ Hide Ad</div>', unsafe_allow_html=True)

                st.markdown(final_advice)
                st.session_state.messages.append({"role": "assistant", "content": final_advice})
                
                # [Separated 조건] 답변 아래에 HTML 배너 생성
                if ad_pos == "separated":
                    render_separated_ad(st.session_state.messages, final_advice)
                
        st.balloons()
