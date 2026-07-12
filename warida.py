import streamlit as st
import gspread
import json
import re
import pandas as pd
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="💰 WariDA Pro", page_icon="💸", layout="wide")

@st.cache_data(ttl=5)
def load_data():
    # SecretsからJSONを安全にパース
    secret_data = st.secrets["gcp"]["data"]
    # もしsecret_dataがJSON文字列なら辞書に変換
    creds_dict = json.loads(secret_data) if isinstance(secret_data, str) else secret_data
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
    
    rows = sheet.get_all_values()
    if len(rows) > 1:
        df = pd.DataFrame(rows[1:], columns=['会', '支払者', '金額'])
        df['金額'] = pd.to_numeric(df['金額'], errors='coerce').fillna(0)
    else:
        df = pd.DataFrame(columns=['会', '支払者', '金額'])
    return df

# アプリ本体
if 'my_name' not in st.session_state: st.session_state.my_name = None

st.markdown("<h1 style='text-align: center; color: #ff6b6b;'>💸 WariDA Pro 💸</h1>", unsafe_allow_html=True)

try:
    df = load_data()
except Exception as e:
    st.error(f"読み込みエラーが発生しました。設定を確認してください: {e}")
    st.stop()

# --- 入力エリア ---
if not st.session_state.my_name:
    name_input = st.text_input("あなたの名前", max_chars=4)
    if st.button("名前を確定"):
        if re.match(r'^[a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+$', name_input):
            st.session_state.my_name = name_input
            st.rerun()
else:
    st.write(f"ログイン中: **{st.session_state.my_name}** さん")
    session = st.selectbox("会を選択", ["1次会", "2次会", "3次会", "4次会", "5次会"])
    amount = st.number_input("金額", min_value=0, step=100)
    if st.button("送信"):
        creds_dict = json.loads(st.secrets["gcp"]["data"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        client = gspread.authorize(creds)
        client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").append_row([session, st.session_state.my_name, amount])
        st.cache_data.clear()
        st.rerun()

st.divider()

# --- 表示エリア ---
if st.button("🔄 最新情報を更新"):
    st.cache_data.clear()
    st.rerun()

st.subheader("📋 支払い履歴")
if not df.empty:
    st.dataframe(df, use_container_width=True)
    
    # 自分の履歴だけ削除ボタンを表示
    for i, row in df.iterrows():
        if row['支払者'] == st.session_state.my_name:
            if st.button(f"❌ 削除 ({row['会']} | {row['金額']}円)", key=f"del_{i}"):
                creds_dict = json.loads(st.secrets["gcp"]["data"])
                creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
                client = gspread.authorize(creds)
                client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").delete_rows(i + 2)
                st.cache_data.clear()
                st.rerun()
else:
    st.info("データがありません。")

# --- 精算ロジック ---
st.subheader("⚖️ 精算結果（誰が誰に渡す？）")
if not df.empty:
    for session in df['会'].unique():
        s_df = df[df['会'] == session]
        total = s_df['金額'].sum()
        avg = total / len(s_df['支払者'].unique())
        
        balance = {m: s_df[s_df['支払者'] == m]['金額'].sum() - avg for m in s_df['支払者'].unique()}
        debtors = sorted({k: v for k, v in balance.items() if v < 0}.items(), key=lambda x: x[1])
        creditors = sorted({k: v for k, v in balance.items() if v > 0}.items(), key=lambda x: x[1], reverse=True)
        
        st.write(f"**[{session}]**")
        for d_name, d_val in debtors:
            rem = abs(d_val)
            for c_name, c_val in creditors:
                if rem <= 1: break
                transfer = min(rem, c_val)
                if transfer > 0:
                    st.write(f"💸 **{d_name}** → **{c_name}** に **{transfer:.0f}円**")
                    rem -= transfer
