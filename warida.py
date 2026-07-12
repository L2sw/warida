import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# --- 設定：各会の参加者名簿（ここを編集してメンバーを管理） ---
PARTICIPANTS_MAP = {
    "1次会": ["q", "x", "y"],
    "2次会": ["k", "x", "y"],
    "3次会": [], "4次会": [], "5次会": []
}

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
    except Exception:
        return pd.DataFrame(columns=['会', '支払者', '金額'])

# --- 最適化された清算ロジック ---
def calculate_optimized_settlement(df):
    global_balances = {}
    
    for session, members in PARTICIPANTS_MAP.items():
        if not members: continue
        session_df = df[df['会'] == session]
        session_total = session_df['金額'].sum()
        per_person = session_total / len(members)
        
        actual = session_df.groupby('支払者')['金額'].sum()
        for m in members:
            balance = actual.get(m, 0) - per_person
            global_balances[m] = global_balances.get(m, 0) + balance
            
    # 債権者と債務者に分ける
    balances_series = pd.Series(global_balances)
    debtors = balances_series[balances_series < -0.1].sort_values()
    creditors = balances_series[balances_series > 0.1].sort_values(ascending=False)
    
    results = []
    # 貪欲法でマッチング
    for d_name, d_val in debtors.items():
        remaining_debt = -d_val
        for c_name, c_val in creditors.items():
            if c_val <= 0 or remaining_debt <= 0: continue
            pay_amount = min(remaining_debt, c_val)
            results.append({"支払人": d_name, "受取人": c_name, "金額": int(pay_amount)})
            creditors[c_name] -= pay_amount
            remaining_debt -= pay_amount
    return results

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
st.subheader("💰 最終的な支払い指示書")
settlements = calculate_optimized_settlement(df)
if settlements:
    st.table(pd.DataFrame(settlements))
else:
    st.success("清算不要")

# 会ごとの内訳と削除処理（前回のコードと同じ）
# ... (省略: 前回のコードの「会ごとの内訳と削除」部分をそのまま貼り付けてください)
