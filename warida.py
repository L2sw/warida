import streamlit as st
import gspread
import json
import base64
import pandas as pd
from google.oauth2.service_account import Credentials

def get_client():
    # 1. JSONを読み込む
    creds_dict = json.loads(st.secrets["gcp"]["data"])
    
    # 2. Base64文字列をデコードして秘密鍵を復元
    # 既存の private_key が Base64化されていると仮定してデコード
    decoded_key = base64.b64decode(creds_dict["private_key"]).decode('utf-8')
    creds_dict["private_key"] = decoded_key
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

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

st.set_page_config(page_title="WariDA", layout="wide")
st.title("💸 WariDA Pro")

if 'my_name' not in st.session_state: st.session_state.my_name = None

if not st.session_state.my_name:
    name_input = st.text_input("あなたの名前")
    if st.button("確定"):
        st.session_state.my_name = name_input
        st.rerun()
else:
    session = st.selectbox("会を選択", ["1次会", "2次会", "3次会", "4次会", "5次会"])
    amount = st.number_input("金額", min_value=0, step=100)
    if st.button("送信"):
        client = get_client()
        client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").append_row([session, st.session_state.my_name, amount])
        st.cache_data.clear()
        st.rerun()

st.divider()
df = load_data()
st.dataframe(df, use_container_width=True)

for i, row in df.iterrows():
    if row['支払者'] == st.session_state.my_name:
        if st.button(f"❌ 削除 ({row['会']} | {row['金額']}円)", key=f"del_{i}"):
            client = get_client()
            client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").delete_rows(i + 2)
            st.cache_data.clear()
            st.rerun()
