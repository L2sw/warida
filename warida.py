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
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/sheets"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
    
    # データを取得し、列名を強制的に固定する（KeyError対策）
    rows = sheet.get_all_values()
    if len(rows) > 1:
        df = pd.DataFrame(rows[1:], columns=['会', '支払者', '金額'])
        df['金額'] = pd.to_numeric(df['金額'])
    else:
        df = pd.DataFrame(columns=['会', '支払者', '金額'])
    return df

# アプリ起動
if 'my_name' not in st.session_state: st.session_state.my_name = None

st.markdown("<h1 style='text-align: center; color: #ff6b6b;'>💸 WariDA Pro 💸</h1>", unsafe_allow_html=True)

try:
    df = load_data()
except Exception as e:
    st.error(f"読み込みエラー: {e}")
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

# --- 表示・削除 ---
if st.button("🔄 最新情報を更新"):
    st.cache_data.clear()
    st.rerun()

st.subheader("📋 支払い履歴")
if not df.empty:
    st.dataframe(df, width=None) # ストリーミングエラーを防ぐため調整
    
    for i, row in df.iterrows():
        if row['支払者'] == st.session_state.my_name:
            if st.button(f"❌ {row['会']}の記録を削除", key=f"del_{i}"):
                client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp"]["data"]), ["https://www.googleapis.com/auth/spreadsheets"]))
                client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").delete_rows(i + 2)
                st.cache_data.clear()
                st.rerun()
