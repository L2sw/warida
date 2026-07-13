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

# --- 厳密な清算ロジック ---
def calculate_final_settlement(df):
    balances = {}
    all_participants = df['支払者'].unique()
    for p in all_participants:
        balances[p] = 0.0
        
    for session in df['会'].unique():
        session_df = df[df['会'] == session]
        participants = session_df['支払者'].unique()
        total = session_df['金額'].sum()
        per_person = total / len(participants)
        
        actual = session_df.groupby('支払者')['金額'].sum()
        for p in participants:
            balances[p] += (actual.get(p, 0) - per_person)
            
    debtors = {p: -v for p, v in balances.items() if v < -0.1}
    creditors = {p: v for p, v in balances.items() if v > 0.1}
    
    results = []
    for d_name, d_val in debtors.items():
        for c_name, c_val in creditors.items():
            if d_val > 0.1 and c_val > 0.1:
                pay = min(d_val, c_val)
                results.append({"支払人": d_name, "受取人": c_name, "金額": int(pay)})
                d_val -= pay
                creditors[c_name] -= pay
                
    return pd.DataFrame(results) if results else pd.DataFrame(columns=["支払人", "受取人", "金額"])

# --- UI ---
st.set_page_config(page_title="WariDA Pro", layout="wide")
st.title("💸 WariDA Pro")

# 更新ボタンの処理
if st.button("🔄 ページを更新して最新にする"):
    st.cache_data.clear()
    st.rerun()

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

# 会ごとの内訳と削除
df = load_data()
sessions = ["1次会", "2次会", "3次会", "4次会", "5次会"]
tabs = st.tabs(sessions)

for i, s_name in enumerate(sessions):
    with tabs[i]:
        session_df = df[df['会'] == s_name]
        if not session_df.empty:
            summary = session_df.groupby('支払者')['金額'].sum().reset_index()
            for _, row in summary.iterrows():
                col1, col2, col3 = st.columns([2, 2, 1])
                col1.write(row['支払者'])
                col2.write(f"{int(row['金額'])} 円")
                if row['支払者'] == st.session_state.my_name:
                    if col3.button("❌", key=f"del_{s_name}_{row['支払者']}"):
                        client = get_client()
                        sheet = client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
                        all_rows = sheet.get_all_values()
                        new_rows = [r for r in all_rows if not (r[0] == s_name and r[1] == row['支払者'])]
                        sheet.clear()
                        sheet.update(all_rows[0:1] + new_rows)
                        st.cache_data.clear()
                        st.rerun()
        else:
            st.info("データなし")

# 最終清算結果
st.divider()
st.subheader("💰 最終的な支払い指示書")
res_df = calculate_final_settlement(df)

if not res_df.empty:
    final_view = res_df.groupby(['支払人', '受取人'])['金額'].sum().reset_index()
    st.table(final_view)
else:
    st.success("清算不要です")
