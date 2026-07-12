import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# --- (認証関数は変更なし) ---
def get_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
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
        return df
    return pd.DataFrame(columns=['会', '支払者', '金額'])

# --- 会ごとの清算ロジック ---
def calculate_session_settlement(session_df):
    participants = session_df['支払者'].unique()
    if len(participants) <= 1: return []
    
    total = session_df['金額'].sum()
    per_person = total / len(participants)
    
    actual = session_df.groupby('支払者')['金額'].sum()
    balances = actual - per_person
    
    debtors = balances[balances < -0.5].sort_values()
    creditors = balances[balances > 0.5].sort_values(ascending=False)
    
    results = []
    d_idx, c_idx = 0, 0
    while d_idx < len(debtors) and c_idx < len(creditors):
        debtor, d_val = debtors.index[d_idx], -debtors.iloc[d_idx]
        creditor, c_val = creditors.index[c_idx], creditors.iloc[c_idx]
        
        amount = min(d_val, c_val)
        if amount > 0.5:
            results.append({"支払人": debtor, "受取人": creditor, "金額": int(amount)})
        
        debtors.iloc[d_idx] += amount
        creditors.iloc[c_idx] -= amount
        if debtors.iloc[d_idx] >= -0.5: d_idx += 1
        if creditors.iloc[c_idx] <= 0.5: c_idx += 1
    return results

# --- UI ---
st.set_page_config(page_title="WariDA", layout="wide")
st.title("💸 WariDA Pro")

# (名前入力等の部分は省略)

st.divider()
df = load_data()
sessions = ["1次会", "2次会", "3次会", "4次会", "5次会"]
tabs = st.tabs(sessions)

# 各会ごとの集計と清算
for i, s_name in enumerate(sessions):
    with tabs[i]:
        session_df = df[df['会'] == s_name]
        
        if not session_df.empty:
            st.subheader(f"📊 {s_name} の内訳と清算")
            
            # 内訳表
            summary = session_df.groupby('支払者')['金額'].sum().reset_index()
            st.table(summary)
            
            # 清算結果（その会に参加した人同士のみで計算される）
            st.write(f"**{s_name} の清算（この会のメンバー間で精算してください）**")
            results = calculate_session_settlement(session_df)
            if results:
                st.table(pd.DataFrame(results))
            else:
                st.success("この会は清算不要です")
        else:
            st.info("データなし")
