import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

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

# --- 新しい清算ロジック: 各会の参加者のみで計算 ---
def calculate_fair_settlement(df):
    # 各参加者がトータルでいくら払うべきかを算出する
    # 各会ごとに: (会の合計額) / (その会の人数) を負担額とする
    total_should_pay = pd.Series(dtype=float)
    
    for session in df['会'].unique():
        session_df = df[df['会'] == session]
        participants = session_df['支払者'].unique()
        session_total = session_df['金額'].sum()
        per_person = session_total / len(participants)
        
        for p in participants:
            total_should_pay[p] = total_should_pay.get(p, 0) + per_person
            
    # 実際の実績
    actual_paid = df.groupby('支払者')['金額'].sum()
    # 収支 = 実際の支払い - 負担すべき額
    balances = actual_paid.sub(total_should_pay, fill_value=0)
    
    # 清算計算
    debtors = balances[balances < 0].sort_values()
    creditors = balances[balances > 0].sort_values(ascending=False)
    
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

if 'my_name' not in st.session_state: st.session_state.my_name = None
if not st.session_state.my_name:
    st.session_state.my_name = st.text_input("あなたの名前")
    if st.button("確定"): st.rerun()
else:
    st.write(f"ログイン中: **{st.session_state.my_name}** さん")
    session = st.selectbox("会を選択", ["1次会", "2次会", "3次会", "4次会", "5次会"])
    amount = st.number_input("追加する金額", min_value=0, step=100, format="%d")
    
    if st.button("送信（加算）"):
        client = get_client()
        client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").append_row([session, st.session_state.my_name, amount])
        st.cache_data.clear()
        st.rerun()

st.divider()
df = load_data()
sessions = ["1次会", "2次会", "3次会", "4次会", "5次会"]
tabs = st.tabs(sessions)

for i, s_name in enumerate(sessions):
    with tabs[i]:
        filtered_df = df[df['会'] == s_name]
        summary = filtered_df.groupby('支払者')['金額'].sum().reset_index()
        if not summary.empty:
            for idx, row in summary.iterrows():
                col1, col2, col3 = st.columns([2, 2, 1])
                col1.write(row['支払者'])
                col2.write(f"{int(row['金額'])} 円")
                # 自分の場合のみ削除ボタン
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
        else:
            st.info("データなし")

st.divider()
st.subheader("💰 最終清算結果")
if not df.empty:
    settlements = calculate_fair_settlement(df)
    if settlements:
        st.table(pd.DataFrame(settlements))
    else:
        st.success("清算不要")
