import streamlit as st
import gspread
import json
import re
import pandas as pd
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="💰 WariDA Pro", page_icon="💸", layout="wide")

# --- 共通の認証関数 ---
def get_authorized_client():
    # SecretsからJSONを読み込む
    secret_data = st.secrets["gcp"]["data"]
    creds_dict = json.loads(secret_data) if isinstance(secret_data, str) else secret_data
    
    # 認証情報を生成
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=5)
def load_data():
    client = get_authorized_client()
    sheet = client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
    rows = sheet.get_all_values()
    if len(rows) > 1:
        df = pd.DataFrame(rows[1:], columns=['会', '支払者', '金額'])
        df['金額'] = pd.to_numeric(df['金額'], errors='coerce').fillna(0)
    else:
        df = pd.DataFrame(columns=['会', '支払者', '金額'])
    return df

# --- アプリ本体 ---
if 'my_name' not in st.session_state: st.session_state.my_name = None

st.markdown("<h1 style='text-align: center; color: #ff6b6b;'>💸 WariDA Pro 💸</h1>", unsafe_allow_html=True)

try:
    df = load_data()
except Exception as e:
    st.error(f"読み込みエラー: {e}")
    st.stop()

# --- 入力 ---
if not st.session_state.my_name:
    name_input = st.text_input("あなたの名前", max_chars=4)
    if st.button("名前を確定"):
        st.session_state.my_name = name_input
        st.rerun()
else:
    st.write(f"ログイン中: **{st.session_state.my_name}** さん")
    session = st.selectbox("会を選択", ["1次会", "2次会", "3次会", "4次会", "5次会"])
    amount = st.number_input("金額", min_value=0, step=100)
    
    if st.button("送信"):
        client = get_authorized_client()
        client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").append_row([session, st.session_state.my_name, amount])
        st.cache_data.clear()
        st.rerun()

st.divider()

# --- 履歴と削除 ---
if st.button("🔄 最新情報を更新"):
    st.cache_data.clear()
    st.rerun()

st.subheader("📋 支払い履歴")
if not df.empty:
    st.dataframe(df, use_container_width=True)
    for i, row in df.iterrows():
        if row['支払者'] == st.session_state.my_name:
            if st.button(f"❌ 削除 ({row['会']} | {row['金額']}円)", key=f"del_{i}"):
                client = get_authorized_client()
                client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").delete_rows(i + 2)
                st.cache_data.clear()
                st.rerun()
