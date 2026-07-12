import streamlit as st
import gspread
import json
import re
import pandas as pd
from google.oauth2.service_account import Credentials

# 認証情報を読み込む関数をシンプルにする
def get_client():
    creds_dict = json.loads(st.secrets["gcp"]["data"])
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
        df['金額'] = pd.to_numeric(df['金額'])
    else:
        df = pd.DataFrame(columns=['会', '支払者', '金額'])
    return df
