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

# --- [수정] 광고 내용을 더 구체적이고 풍성하게 생성하는 함수 ---
def render_final_ad(user_context):
    with st.spinner("Generating sponsored offer..."):
        ad_res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """You are a high-end advertising system. 
                Based on the user's interest, create a compelling Google-style search ad.
                
                Rules:
                1. Create a catchy Headline (Product Name + Short Benefit).
                2. Write a one-line Description that creates urgency or desire.
                3. Include a realistic Price.
                4. Output format (STRICT): Headline | Description | Price
                5. Do NOT use labels like 'Ad Title:' or 'Price:'. Just the content separated by '|'."""}
            ] + user_context
        )
        
        try:
            # 콘텐츠 파싱
            parts = ad_res.choices[0].message.content.split('|')
            headline = parts[0].strip()
            description = parts[1].strip() if len(parts) > 1 else "Limited time offer for you."
            price = parts[2].strip() if len(parts) > 2 else ""

            st.markdown(f"""
                <div style="
                    border: 1px solid #dadce0;
                    background-color: #ffffff;
                    padding: 20px;
                    margin-top: 25px;
                    border-radius: 8px;
                    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    box-shadow: 0 1px 6px rgba(32,33,36,0.28);
                ">
                    <div style="display: flex; align-items: center; margin-bottom: 8px;">
                        <span style="background: #202124; color: white; font-size: 11px; padding: 2px 6px; border-radius: 3px; font-weight: bold; margin-right: 10px;">AD</span>
                        <span style="color: #202124; font-size: 12px; font-weight: 500;">Sponsored by Premium Partners</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="flex: 1; padding-right: 20px;">
                            <div style="color: #1a0dab; font-size: 18px; font-weight: 500; text-decoration: none; margin-bottom: 4px; cursor: pointer;">
                                {headline}
                            </div>
                            <div style="color: #4d5156; font-size: 14px; line-height: 1.5; margin-bottom: 8px;">
                                {description}
                            </div>
                            <div style="color: #d93025; font-size: 16px; font-weight: bold;">
                                {price}
                            </div>
                        </div>
                        <a href="https://google.com" target="_blank" style="
                            background-color: #1a73e8;
                            color: white;
                            padding: 10px 24px;
                            text-decoration: none;
                            font-size: 14px;
                            border-radius: 4px;
                            font-weight: 500;
                            white-space: nowrap;
                        ">Shop Now</a>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        except:
            st.write("Special offer available for your selected item.")

# 3. 세션 및 4. 대화 로직 (기존과 동일)
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
            next_q = "Got it. **2. Who is this product for?**"
            st.session_state.messages.append({"role": "assistant", "content": next_q})
            st.session_state.turn += 1
        elif st.session_state.turn == 2:
            next_q = "Finally, **3. What is your maximum budget in dollars ($)?**"
            st.session_state.messages.append({"role": "assistant", "content": next_q})
            st.session_state.turn += 1
        elif st.session_state.turn == 3:
            st.session_state.finished = True
        st.rerun()

# 5. 마지막 추천 및 풍성한 광고 출력
if st.session_state.finished:
    is_already_recommended = any("Based on our conversation" in m["content"] for m in st.session_state.messages)
    
    if not is_already_recommended:
        with st.chat_message("assistant"):
            subset = product_df[['id', 'name', 'price', 'category']]
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": f"Our products: {subset.to_string()}\n\nRecommend ONE from the list. Start with 'Based on our conversation...'."}] + st.session_state.messages
            )
            final_advice = res.choices[0].message.content
            st.markdown(final_advice)
            st.session_state.messages.append({"role": "assistant", "content": final_advice})
            
            # 여기서 광고 호출
            render_final_ad(st.session_state.messages)
            
        st.balloons()
