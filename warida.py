import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# --- 認証 ---
def get_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

# --- データ読み込み ---
@st.cache_data(ttl=5)
def load_data():
    try:
        client = get_client()
        sheet = client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
        rows = sheet.get_all_values()
        if len(rows) > 1:
            df = pd.DataFrame(rows[1:], columns=['会', '支払者', '金額'])
            df['金額'] = pd.to_numeric(df['金額'], errors='coerce').fillna(0)
            return df
        return pd.DataFrame(columns=['会', '支払者', '金額'])
    except Exception:
        return pd.DataFrame(columns=['会', '支払者', '金額'])

# --- 現実的な清算ロジック ---
def calculate_realistic_settlement(df):
    all_results = []
    # 最終的な個人の収支（実績 - 負担額の合計）
    final_balance = {}

    # 1. 各会ごとの処理
    for session in df['会'].unique():
        session_df = df[df['会'] == session]
        participants = session_df['支払者'].unique()
        session_total = session_df['金額'].sum()
        per_person = session_total / len(participants)
        
        actual = session_df.groupby('支払者')['金額'].sum()
        
        # 会ごとの収支を計算
        session_bal = {p: actual.get(p, 0) - per_person for p in participants}
        
        # 債務者と債権者に分ける
        debts = {p: -v for p, v in session_bal.items() if v < -0.1}
        credits = {p: v for p, v in session_bal.items() if v > 0.1}
        
        # 同じ会にいたメンバー内での直接精算
        for d_name, d_val in debts.items():
            for c_name, c_val in credits.items():
                if d_val > 0.1 and c_val > 0.1:
                    pay = min(d_val, c_val)
                    all_results.append({"支払人": d_name, "受取人": c_name, "金額": int(pay)})
                    debts[d_name] -= pay
                    credits[c_name] -= pay
                    d_val -= pay
        
        # 会で精算しきれなかった分を全体の収支に加算
        for p in participants:
            final_balance[p] = final_balance.get(p, 0) + session_bal.get(p, 0)

    # 2. 全体での最終精算
    final_debtors = {p: -v for p, v in final_balance.items() if v < -0.1}
    final_credits = {p: v for p, v in final_balance.items() if v > 0.1}
    
    for d_name, d_val in final_debtors.items():
        for c_name, c_val in final_credits.items():
            if d_val > 0.1 and c_val > 0.1:
                pay = min(d_val, c_val)
                all_results.append({"支払人": d_name, "受取人": c_name, "金額": int(pay)})
                d_val -= pay
                c_val -= pay
                final_credits[c_name] = c_val
                
    return all_results

# --- UI ---
st.set_page_config(page_title="WariDA Pro", layout="wide")
st.title("💸 WariDA Pro")

if 'my_name' not in st.session_state: st.session_state.my_name = None

if not st.session_state.my_name:
    st.session_state.my_name = st.text_input("あなたの名前")
    if st.button("確定"): st.rerun()
else:
    st.write(f"ログイン中: **{st.session_state.my_name}** さん")
    session = st.selectbox("会を選択", ["1次会", "2次会", "3次会", "4次会", "5次会"])
    amount = st.number_input("金額", min_value=0, step=100, format="%d")
    if st.button("送信（加算）"):
        client = get_client()
        client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").append_row([session, st.session_state.my_name, amount])
        st.cache_data.clear()
        st.rerun()

st.divider()
df = load_data()

# 各会ごとの集計表示
tabs = st.tabs(["1次会", "2次会", "3次会", "4次会", "5次会"])
for i, s_name in enumerate(["1次会", "2次会", "3次会", "4次会", "5次会"]):
    with tabs[i]:
        session_df = df[df['会'] == s_name]
        if not session_df.empty:
            summary = session_df.groupby('支払者')['金額'].sum().reset_index()
            for _, row in summary.iterrows():
                col1, col2, col3 = st.columns([2, 2, 1])
                col1.write(row['支払者'])
                col2.write(f"{int(row['金額'])} 円")
                if row['支払者'] == st.session_state.my_name:
                    if col3.button("❌", key=f"del_{s_name}"):
                        client = get_client()
                        sheet = client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
                        all_rows = sheet.get_all_values()
                        new_rows = [r for r in all_rows if not (r[0] == s_name and r[1] == st.session_state.my_name)]
                        sheet.clear()
                        sheet.update(all_rows[0:1] + new_rows)
                        st.cache_data.clear()
                        st.rerun()

st.divider()
st.subheader("💰 最終的な支払い指示書")
settlements = calculate_realistic_settlement(df)
if settlements:
    # 同一ペアの金額を合算
    res_df = pd.DataFrame(settlements)
    res_df = res_df.groupby(['支払人', '受取人'])['金額'].sum().reset_index()
    st.table(res_df)
else:
    st.success("清算不要です")
