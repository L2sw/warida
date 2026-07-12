import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# --- 認証とデータ取得 ---
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

# --- 清算アルゴリズム ---
def calculate_settlement(df):
    total_amount = df['金額'].sum()
    num_people = df['支払者'].nunique()
    if num_people == 0: return []
    
    avg_amount = total_amount / num_people
    balances = df.groupby('支払者')['金額'].sum() - avg_amount
    
    debtors = balances[balances < 0].sort_values()
    creditors = balances[balances > 0].sort_values(ascending=False)
    
    results = []
    d_idx, c_idx = 0, 0
    while d_idx < len(debtors) and c_idx < len(creditors):
        debtor, d_val = debtors.index[d_idx], -debtors.iloc[d_idx]
        creditor, c_val = creditors.index[c_idx], creditors.iloc[c_idx]
        
        amount = min(d_val, c_val)
        results.append({"支払人": debtor, "受取人": creditor, "金額": int(amount)})
        
        debtors.iloc[d_idx] += amount
        creditors.iloc[c_idx] -= amount
        if debtors.iloc[d_idx] >= -1: d_idx += 1
        if creditors.iloc[c_idx] <= 1: c_idx += 1
    return results

# --- UI ---
st.set_page_config(page_title="WariDA", layout="wide")
st.title("💸 WariDA Pro")

# (中略：名前入力・送信部分は前回のコードと同じ)
# ... (省略) ...

st.divider()
st.subheader("📋 支払い状況と清算結果")
df = load_data()
sessions = ["1次会", "2次会", "3次会", "4次会", "5次会"]
tabs = st.tabs(sessions)

for i, s_name in enumerate(sessions):
    with tabs[i]:
        filtered_df = df[df['会'] == s_name]
        summary_df = filtered_df.groupby('支払者')['金額'].sum().reset_index()
        
        if not summary_df.empty:
            st.write(f"**{s_name} 支払い合計**")
            st.table(summary_df)
            
            # 清算結果の表示
            st.write(f"**💰 {s_name} 清算結果**")
            settlements = calculate_settlement(filtered_df)
            if settlements:
                settle_df = pd.DataFrame(settlements)
                st.table(settle_df)
            else:
                st.write("過不足なし！")
        else:
            st.info("まだ履歴がありません")
