import streamlit as st
import gspread
import json
import re
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="💰 WariDA Pro", page_icon="💸", layout="wide")

# 1. キャッシュ機能で通信を最小限に
@st.cache_data(ttl=60) # 60秒間はキャッシュを使用
def load_data():
    creds_dict = json.loads(st.secrets["gcp"]["data"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
    return pd.DataFrame(sheet.get_all_records())

if 'my_name' not in st.session_state: st.session_state.my_name = None

st.markdown("<h1 style='text-align: center; color: #ff6b6b;'>💸 WariDA Pro 💸</h1>", unsafe_allow_html=True)

# データの読み込み
try:
    df = load_data()
except Exception as e:
    st.error("データ読み込み失敗。更新ボタンを押してください。")
    st.stop()

# --- 入力エリア ---
if not st.session_state.my_name:
    name_input = st.text_input("あなたの名前（4文字以内、記号不可）", max_chars=4)
    if st.button("名前を確定"):
        if re.match(r'^[a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+$', name_input):
            st.session_state.my_name = name_input
            st.rerun()
else:
    st.write(f"ログイン中: **{st.session_state.my_name}**")
    session = st.selectbox("会を選択", ["1次会", "2次会", "3次会", "4次会", "5次会"])
    amount = st.number_input("金額", min_value=0, step=100)
    if st.button("送信"):
        # 書き込み時はキャッシュをクリアするために明示的に再読み込みを促す
        st.cache_data.clear()
        # ここでスプレッドシートへ書き込み
        client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp"]["data"]), ["https://www.googleapis.com/auth/spreadsheets"]))
        client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").append_row([session, st.session_state.my_name, amount])
        st.rerun()

# --- 表示・計算エリア ---
if st.button("🔄 最新情報を更新"):
    st.cache_data.clear()
    st.rerun()

if not df.empty:
    st.subheader("📋 支払い履歴")
    st.dataframe(df, use_container_width=True)
    
    st.subheader("⚖️ 会ごとの精算まとめ")
    # pandasで高速集計
    summary = df.groupby(['会', '支払者'])['金額'].sum().unstack(fill_value=0)
    st.dataframe(summary, use_container_width=True)
else:
    st.info("データがありません。")
