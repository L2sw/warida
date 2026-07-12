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
    # 各シートの取得
    db_sheet = client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
    member_sheet = client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("メンバー")
    
    # データを取得
    db_data = pd.DataFrame(db_sheet.get_all_records())
    
    # メンバーリストは1列目を自動取得（見出し名に依存しない）
    member_df = pd.DataFrame(member_sheet.get_all_records())
    members = member_df.iloc[:, 0].tolist() if not member_df.empty else []
    
    return db_data, members

# 実行
st.markdown("<h1 style='text-align: center; color: #ff6b6b;'>💸 WariDA Pro 💸</h1>", unsafe_allow_html=True)

try:
    df, members = load_data()
except Exception as e:
    st.error(f"読み込みエラーです。スプレッドシートのシート名と列を確認してください。詳細: {e}")
    st.stop()

# --- (以下、入力・計算ロジックは前回と同様です) ---
