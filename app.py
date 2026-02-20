import streamlit as st
import pandas as pd
from openai import OpenAI
import time
import streamlit.components.v1 as components

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

# 4. 세션 상태 관리 (에러 방지의 핵심)
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm here to help you shop. **1. What kind of product category are you looking for?**"}]
if "turn" not in st.session_state: st.session_state.turn = 1
if "finished" not in st.session_state: st.session_state.finished = False
if "ad_data" not in st.session_state: st.session_state.ad_data = None

# 대화 로그 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 5. 질문 및 답변 로직
if not st.session_state.finished:
    if prompt := st.chat_input("Type your answer here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # 즉각적인 답변 생성 (rerun 최소화로 리다이렉션 방지)
        with st.chat_message("assistant"):
            if st.session_state.turn < 3:
                time.sleep(0.5)
                next_q = "Got it. **2. Who is this product for?**" if st.session_state.turn == 1 else "Finally, **3. What is your maximum budget ($)?**"
                st.session_state.messages.append({"role": "assistant", "content": next_q})
                st.markdown(next_q)
                st.session_state.turn += 1
            else:
                st.session_state.finished = True
                st.rerun()

# 6. 최종 결과 생성 (여기서 광고 데이터만 추출)
if st.session_state.finished:
    # 중복 답변 방지용 체크
    has_final_res = any("Based on" in m["content"] or "[AD]" in m["content"] for m in st.session_state.messages)

    if not has_final_res:
        with st.chat_message("assistant"):
            with st.spinner("Finding your perfect match..."):
                # 그룹별 프롬프트 분기
                if ad_pos == "in-text":
                    sys_msg = "Recommend ONE product. Response must be a persuasive ad. Start with '[AD] Sponsored Recommendation:'."
                elif ad_pos == "following":
                    sys_msg = "Recommend one product neutrally. Then, start a new paragraph with 'By the way, [AD]...' and recommend a different product."
                else: # separated
                    sys_msg = "Recommend ONE product from the list in a neutral tone. Plain text only. No asterisks."

                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": sys_msg}] + st.session_state.messages
                )
                final_advice = res.choices[0].message.content.replace('*', '')

                # 인텍스트/팔로잉 조건 제어권 표시
                if is_controllable and ad_pos in ["in-text", "following"]:
                    st.markdown('<div style="text-align:right; font-size:10px; color:#ccc;">✕ Hide Ad</div>', unsafe_allow_html=True)

                st.markdown(final_advice)
                st.session_state.messages.append({"role": "assistant", "content": final_advice})

                # Separated 배너용 데이터 생성
                if ad_pos == "separated":
                    ad_res = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "system", "content": "Pick a DIFFERENT product. Format: Headline | Description | Price. No labels, no asterisks."}] + st.session_state.messages
                    )
                    st.session_state.ad_data = ad_res.choices[0].message.content.replace('*', '')
                    st.rerun()

    st.balloons()
    st.caption("✅ Interaction finished. Please return to Qualtrics and click 'Next'.")

# 7. [해결사] 광고 배너 전용 독립 렌더링 영역
# 이 코드는 'with chat_message' 밖에 위치하여 절대 코드 박스에 갇히지 않습니다.
if ad_pos == "separated" and st.session_state.ad_data:
    try:
        parts = st.session_state.ad_data.split('|')
        h = parts[0].strip()
        d = parts[1].strip() if len(parts) > 1 else "Premium quality choice."
        p = parts[2].strip() if len(parts) > 2 else ""

        ctrl_ui = '<div style="text-align:right; font-size:12px; color:#aaa; cursor:pointer;">✕ Hide</div>' if is_controllable else ''
        
        banner_html = f"""
        <div style="border: 1px solid #dadce0; background-color: #ffffff; padding: 18px; border-radius: 8px; font-family: sans-serif; box-shadow: 0 1px 6px rgba(32,33,36,0.15); margin-top: 10px;">
            {ctrl_ui}
            <div style="display: flex; align-items: center; margin-bottom: 8px;">
                <span style="background: #202124; color: white; font-size: 10px; padding: 2px 5px; border-radius: 3px; font-weight: bold; margin-right: 8px;">AD</span>
                <span style="color: #202124; font-size: 12px; font-weight: 500;">Sponsored Alternative</span>
            </div>
            <div style="color: #1a0dab; font-size: 18px; font-weight: 500; margin-bottom: 4px;">{h}</div>
            <div style="color: #4d5156; font-size: 14px; line-height: 1.4; margin-bottom: 8px;">{d}</div>
            <div style="color: #d93025; font-size: 16px; font-weight: bold;">{p}</div>
        </div>
        """
        components.html(banner_html, height=170)
    except:
        pass
