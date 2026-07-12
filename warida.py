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
    try:
        client = get_client()
        sheet = client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
        rows = sheet.get_all_values()
        if len(rows) > 1:
            df = pd.DataFrame(rows[1:], columns=['会', '支払者', '金額'])
            df['金額'] = pd.to_numeric(df['金額'], errors='coerce').fillna(0)
            return df
        return pd.DataFrame(columns=['会', '支払者', '金額'])
    except Exception as e:
        st.error(f"接続エラー: {e}")
        return pd.DataFrame(columns=['会', '支払者', '金額'])

# --- 正確な清算ロジック ---
def calculate_fair_settlement(df):
    if df.empty: return []
    
    # 実際の実績（誰がいくら支払ったか）
    actual_paid = df.groupby('支払者')['金額'].sum()
    
    # 負担額（会ごとに参加者で割る）
    total_should_pay = pd.Series(dtype=float)
    
    for session in df['会'].unique():
        session_df = df[df['会'] == session]
        participants = session_df['支払者'].unique()
        session_total = session_df['金額'].sum()
        per_person = session_total / len(participants)
        
        for p in participants:
            total_should_pay[p] = total_should_pay.get(p, 0) + per_person
            
    # 全員の名前セット
    all_names = set(actual_paid.index) | set(total_should_pay.index)
    
    # 収支計算 (実績 - 負担)
    balances = pd.Series({name: actual_paid.get(name, 0) - total_should_pay.get(name, 0) for name in all_names})
    
    # 清算（プラスの人＝受取人、マイナスの人＝支払人）
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

# --- UI設定 ---
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
st.subheader("📋 会ごとの支払い内訳")
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
