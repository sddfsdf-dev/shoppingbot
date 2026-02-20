import streamlit as st
import pandas as pd
from openai import OpenAI
import time
import re

# 1. OpenAI 설정
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Shopping Assistant", layout="centered")

# 2. 데이터 로드
@st.cache_data
def load_data():
    for f in ['products.csv', 'product.csv']:
        try: return pd.read_csv(f)
        except: continue
    return None

product_df = load_data()

# --- 광고 생성 함수: 특수기호 제거 로직 포함 ---
def render_final_ad(user_context, recommended_item_name):
    ad_res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"""You are a luxury ad system. 
            The AI recommended '{recommended_item_name}'. Pick a DIFFERENT competitor product.
            Rules: No asterisks(*), no hashtags(#). Use plain text.
            Format: Headline | Description | Price"""}
        ] + user_context
    )
    
    try:
        # 별표(*)를 모두 공백으로 치환하여 깨짐 방지
        raw_content = ad_res.choices[0].message.content.replace('*', '')
        parts = raw_content.split('|')
        headline = parts[0].strip()
        description = parts[1].strip() if len(parts) > 1 else "Premium selection for you."
        price = parts[2].strip() if len(parts) > 2 else ""

        st.markdown(f"""
            <div style="border: 1px solid #dadce0; background-color: #ffffff; padding: 20px; margin-top: 25px; border-radius: 8px; font-family: 'Arial', sans-serif; box-shadow: 0 1px 6px rgba(32,33,36,0.28);">
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <span style="background: #202124; color: white; font-size: 11px; padding: 2px 6px; border-radius: 3px; font-weight: bold; margin-right: 10px;">AD</span>
                    <span style="color: #202124; font-size: 12px; font-weight: 500;">Sponsored Alternative</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div style="flex: 1; padding-right: 20px;">
                        <div style="color: #1a0dab; font-size: 18px; font-weight: 500; margin-bottom: 4px;">{headline}</div>
                        <div style="color: #4d5156; font-size: 14px; line-height: 1.5; margin-bottom: 8px;">{description}</div>
                        <div style="color: #d93025; font-size: 16px; font-weight: bold;">{price}</div>
                    </div>
                    <a href="https://google.com" target="_blank" style="background-color: #1a73e8; color: white; padding: 10px 24px; text-decoration: none; font-size: 14px; border-radius: 4px; font-weight: 500;">Shop Now</a>
                </div>
            </div>
        """, unsafe_allow_html=True)
    except:
        pass

# 3. 세션 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm here to help you shop. **1. What kind of product category are you looking for?**"}]
if "turn" not in st.session_state: st.session_state.turn = 1
if "finished" not in st.session_state: st.session_state.finished = False

# 대화 기록 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. 대화 로직: 자연스러운 딜레이(Spinner) 추가
if not st.session_state.finished:
    if prompt := st.chat_input("Type your answer here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                time.sleep(1.5) # 자연스러운 대기 시간 추가
                
                if st.session_state.turn == 1:
                    next_q = "Got it. **2. Who is this product for?**"
                    st.session_state.messages.append({"role": "assistant", "content": next_q})
                    st.markdown(next_q)
                    st.session_state.turn += 1
                elif st.session_state.turn == 2:
                    next_q = "Finally, **3. What is your maximum budget in dollars ($)?**"
                    st.session_state.messages.append({"role": "assistant", "content": next_q})
                    st.markdown(next_q)
                    st.session_state.turn += 1
                elif st.session_state.turn == 3:
                    st.session_state.finished = True
                    st.rerun()

# 5. 최종 추천 및 광고 (깨짐 방지 처리)
if st.session_state.finished:
    is_done = any("Based on our conversation" in m["content"] for m in st.session_state.messages)
    
    if not is_done:
        with st.chat_message("assistant"):
            with st.spinner("Finding your perfect match..."):
                time.sleep(2) # 추천 전에는 조금 더 긴 생각 시간
                subset = product_df[['id', 'name', 'price', 'category']]
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "Recommend ONE product from the list. USE PLAIN TEXT ONLY. NO asterisks(*). Keep it clean."}] + st.session_state.messages
                )
                # 최종 답변에서도 모든 별표(*) 제거
                final_advice = res.choices[0].message.content.replace('*', '')
                st.markdown(final_advice)
                st.session_state.messages.append({"role": "assistant", "content": final_advice})
                
                # 광고 렌더링
                render_final_ad(st.session_state.messages, final_advice)
                
        st.balloons()
        st.caption("✅ Interaction finished. Please return to Qualtrics and click 'Next'.")
