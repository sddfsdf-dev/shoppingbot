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
        try: return pd.read_csv(f)
        except: continue
    return None

product_df = load_data()

# --- [수정] 공식 추천과 겹치지 않게 광고를 생성하는 함수 ---
def render_final_ad(user_context, recommended_item_name):
    with st.spinner("Generating sponsored offer..."):
        ad_res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"""You are a high-end advertising system. 
                The AI already recommended '{recommended_item_name}' to the user.
                
                Your Task:
                1. Pick a DIFFERENT product (a competitor or a higher-end alternative).
                2. Do NOT recommend the same product as the official recommendation.
                3. Create a Google-style search ad.
                4. Format (STRICT): Headline | Description | Price
                5. Output only the content separated by '|'."""}
            ] + user_context
        )
        
        try:
            parts = ad_res.choices[0].message.content.split('|')
            headline = parts[0].strip()
            description = parts[1].strip() if len(parts) > 1 else "Check out this alternative."
            price = parts[2].strip() if len(parts) > 2 else ""

            st.markdown(f"""
                <div style="border: 1px solid #dadce0; background-color: #ffffff; padding: 20px; margin-top: 25px; border-radius: 8px; font-family: sans-serif; box-shadow: 0 1px 6px rgba(32,33,36,0.28);">
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

# 3. 세션 및 4. 대화 로직 (동일)
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm here to help you shop. **1. What kind of product category are you looking for?**"}]
if "turn" not in st.session_state: st.session_state.turn = 1
if "finished" not in st.session_state: st.session_state.finished = False

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if not st.session_state.finished:
    if prompt := st.chat_input("Type your answer here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        if st.session_state.turn == 1:
            st.session_state.messages.append({"role": "assistant", "content": "Got it. **2. Who is this product for?**"})
            st.session_state.turn += 1
        elif st.session_state.turn == 2:
            st.session_state.messages.append({"role": "assistant", "content": "Finally, **3. What is your maximum budget in dollars ($)?**"})
            st.session_state.turn += 1
        elif st.session_state.turn == 3:
            st.session_state.finished = True
        st.rerun()

# 5. 최종 추천 및 광고 (서로 다른 제품)
if st.session_state.finished:
    is_done = any("Based on our conversation" in m["content"] for m in st.session_state.messages)
    
    if not is_done:
        with st.chat_message("assistant"):
            subset = product_df[['id', 'name', 'price', 'category']]
            # 1. 공식 추천 생성
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": f"Products: {subset.to_string()}\n\nRecommend ONLY ONE best product from the list."}] + st.session_state.messages
            )
            final_advice = res.choices[0].message.content
            st.markdown(final_advice)
            st.session_state.messages.append({"role": "assistant", "content": final_advice})
            
            # 2. 광고 생성 (추천된 제품 이름을 피해서 생성하도록 전달)
            render_final_ad(st.session_state.messages, final_advice)
            
        st.balloons()
