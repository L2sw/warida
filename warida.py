import streamlit as st
import gspread
import json
import re
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="💰 WariDA Pro", page_icon="💸", layout="wide")

@st.cache_data(ttl=10)
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
    st.error("読み込みエラーです。更新ボタンを押してください。")
    st.stop()

# --- 入力エリア ---
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

# --- 1. 支払い履歴（個人ごとに集計して表示） ---
st.subheader("📋 支払い履歴（合計）")
if not df.empty:
    summary = df.groupby(['会', '支払者'])['金額'].sum().reset_index()
    st.dataframe(summary, use_container_width=True)
    
    # 削除機能（本人限定）
    target_idx = st.selectbox("削除する履歴を選択", df.index)
    if st.button("選択した履歴を削除"):
        if df.loc[target_idx, '支払者'] == st.session_state.my_name:
            client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp"]["data"]), ["https://www.googleapis.com/auth/spreadsheets"]))
            client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").delete_rows(target_idx + 2)
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("自分の入力のみ削除可能です。")

# --- 2. 精算結果（誰が誰にいくら払うか） ---
st.subheader("⚖️ 精算結果（誰がいくら渡す？）")
if not df.empty:
    for session in df['会'].unique():
        s_df = df[df['会'] == session]
        total = s_df['金額'].sum()
        members = df['支払者'].unique()
        avg = total / len(members)
        
        st.write(f"**[{session}]**")
        for m in members:
            paid = s_df[s_df['支払者'] == m]['金額'].sum()
            diff = paid - avg
            if diff < 0:
                st.write(f"💸 {m} さんが **{abs(diff):.0f} 円** 払う必要があります")
else:
    st.info("データがありません。")
