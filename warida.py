import streamlit as st
import gspread
import pandas as pd
import json
from google.oauth2.service_account import Credentials

# --- 認証関数：アップロードされたファイルから認証 ---
def get_client(json_data):
    creds_dict = json.load(json_data)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

st.set_page_config(page_title="WariDA", layout="wide")
st.title("💸 WariDA Pro")

# --- JSONアップロード処理 ---
st.sidebar.header("⚙️ 設定")
uploaded_file = st.sidebar.file_uploader("Googleサービスアカウントキー (JSON) をアップロード", type=["json"])

if not uploaded_file:
    st.warning("左側のメニューから service-account.json をアップロードしてください。")
    st.stop()

# --- データ読み込み ---
@st.cache_data(ttl=5)
def load_data(file_content):
    # ファイルを一度読み込んでクライアントを作成
    file_content.seek(0)
    client = get_client(file_content)
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

if not st.session_state.my_name:
    st.session_state.my_name = st.text_input("名前")
    if st.button("確定"): st.rerun()
else:
    st.write(f"ログイン中: {st.session_state.my_name}")
    session = st.selectbox("会", ["1次会", "2次会", "3次会", "4次会", "5次会"])
    amount = st.number_input("金額", min_value=0, step=100)
    if st.button("送信"):
        uploaded_file.seek(0)
        client = get_client(uploaded_file)
        client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").append_row([session, st.session_state.my_name, amount])
        st.cache_data.clear()
        st.rerun()

st.divider()
df = load_data(uploaded_file)
st.subheader("📋 履歴")
st.dataframe(df, use_container_width=True)

for i, row in df.iterrows():
    if row['支払者'] == st.session_state.my_name:
        if st.button(f"❌ 削除 ({row['会']} | {row['金額']}円)", key=f"del_{i}"):
            uploaded_file.seek(0)
            client = get_client(uploaded_file)
            client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").delete_rows(i + 2)
            st.cache_data.clear()
            st.rerun()
