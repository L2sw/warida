import streamlit as st
import gspread
import json
import pandas as pd
from google.oauth2.service_account import Credentials

# --- 認証処理を一つに集約 ---
def get_client():
    # SecretsからJSONをロード
    creds_dict = json.loads(st.secrets["gcp"]["data"])
    
    # 秘密鍵の改行を正しく復元
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

# --- データ読み込み ---
@st.cache_data(ttl=5)
def load_data():
    client = get_client()
    sheet = client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
    rows = sheet.get_all_values()
    if len(rows) > 1:
        df = pd.DataFrame(rows[1:], columns=['会', '支払者', '金額'])
        df['金額'] = pd.to_numeric(df['金額'], errors='coerce').fillna(0)
    else:
        df = pd.DataFrame(columns=['会', '支払者', '金額'])
    return df

# --- UI構築 ---
st.set_page_config(page_title="WariDA", layout="wide")
st.title("💸 WariDA Pro")

if 'my_name' not in st.session_state:
    st.session_state.my_name = None

if not st.session_state.my_name:
    name_input = st.text_input("あなたの名前（4文字以内）")
    if st.button("確定"):
        st.session_state.my_name = name_input
        st.rerun()
else:
    st.write(f"ログイン中: **{st.session_state.my_name}** さん")
    session = st.selectbox("会を選択", ["1次会", "2次会", "3次会", "4次会", "5次会"])
    amount = st.number_input("金額", min_value=0, step=100)
    
    if st.button("送信"):
        client = get_client()
        client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").append_row([session, st.session_state.my_name, amount])
        st.cache_data.clear()
        st.rerun()

st.divider()
st.subheader("📋 支払い履歴")
df = load_data()
st.dataframe(df, use_container_width=True)

# 削除処理
for i, row in df.iterrows():
    if row['支払者'] == st.session_state.my_name:
        if st.button(f"❌ 削除 ({row['会']} | {row['金額']}円)", key=f"del_{i}"):
            client = get_client()
            client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").delete_rows(i + 2)
            st.cache_data.clear()
            st.rerun()
