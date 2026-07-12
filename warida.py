import streamlit as st
import gspread
import json
import re
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="💰 WariDA Pro", page_icon="💸", layout="wide")

@st.cache_data(ttl=5)
def load_data():
    creds_dict = json.loads(st.secrets["gcp"]["data"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
    return pd.DataFrame(sheet.get_all_records())

if 'my_name' not in st.session_state: st.session_state.my_name = None

st.markdown("<h1 style='text-align: center; color: #ff6b6b;'>💸 WariDA Pro 💸</h1>", unsafe_allow_html=True)

try:
    df = load_data()
except:
    st.error("読み込みエラー。更新ボタンを押してください。")
    st.stop()

# --- 入力 ---
if not st.session_state.my_name:
    name_input = st.text_input("あなたの名前（4文字以内、記号不可）", max_chars=4)
    if st.button("名前を確定"):
        if re.match(r'^[a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+$', name_input):
            st.session_state.my_name = name_input
            st.rerun()
else:
    st.write(f"ログイン中: **{st.session_state.my_name}** さん")
    session = st.selectbox("会を選択", ["1次会", "2次会", "3次会", "4次会", "5次会"])
    amount = st.number_input("金額", min_value=0, step=100)
    if st.button("送信"):
        client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp"]["data"]), ["https://www.googleapis.com/auth/spreadsheets"]))
        client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").append_row([session, st.session_state.my_name, amount])
        st.cache_data.clear()
        st.rerun()

st.divider()

if st.button("🔄 最新情報を更新"):
    st.cache_data.clear()
    st.rerun()

# --- 1. 履歴一覧と削除 ---
st.subheader("📋 支払い履歴")
if not df.empty:
    for i, row in df.iterrows():
        cols = st.columns([3, 1])
        cols[0].write(f"**{row['会']}** | {row['支払者']}さん：{row['金額']}円")
        if row['支払者'] == st.session_state.my_name:
            if cols[1].button("❌ 削除", key=f"del_{i}"):
                client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp"]["data"]), ["https://www.googleapis.com/auth/spreadsheets"]))
                client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").delete_rows(i + 2)
                st.cache_data.clear()
                st.rerun()
else:
    st.info("データがありません。")

# --- 2. 精算結果計算 ---
st.subheader("⚖️ 精算結果（誰が誰に払う？）")
if not df.empty:
    for session in df['会'].unique():
        st.write(f"### 📍 {session}")
        s_df = df[df['会'] == session]
        total = s_df['金額'].sum()
        all_members = df['支払者'].unique()
        avg = total / len(all_members)
        
        balance = {m: s_df[s_df['支払者'] == m]['金額'].sum() - avg for m in all_members}
        debtors = sorted({k: v for k, v in balance.items() if v < 0}.items(), key=lambda x: x[1])
        creditors = sorted({k: v for k, v in balance.items() if v > 0}.items(), key=lambda x: x[1], reverse=True)
        
        for d_name, d_val in debtors:
            rem = abs(d_val)
            for c_name, c_val in creditors:
                if rem <= 0: break
                transfer = min(rem, c_val)
                if transfer > 0:
                    st.write(f"💸 **{d_name}** さん → **{c_name}** さん に **{transfer:.0f}円**")
                    rem -= transfer
                    # 結果を一時保存して表示を更新するロジック
else:
    st.info("データがありません。")
