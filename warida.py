import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# --- 設定 ---
st.set_page_config(page_title="WariDA Pro", layout="wide")

# --- 認証と接続 (シングルトンとして管理) ---
@st.cache_resource
def get_gspread_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def get_data():
    try:
        client = get_gspread_client()
        sheet = client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
        data = sheet.get_all_values()
        if len(data) <= 1: return pd.DataFrame(columns=['会', '支払者', '金額'])
        df = pd.DataFrame(data[1:], columns=['会', '支払者', '金額'])
        df['金額'] = pd.to_numeric(df['金額'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return pd.DataFrame(columns=['会', '支払者', '金額'])

# --- 計算ロジック ---
def calculate_settlements(df):
    if df.empty: return pd.DataFrame(columns=["支払人", "受取人", "金額"])
    
    balances = {}
    for p in df['支払者'].unique(): balances[p] = 0.0
        
    for session in df['会'].unique():
        s_df = df[df['会'] == session]
        parts = s_df['支払者'].unique()
        per_person = s_df['金額'].sum() / len(parts)
        
        actual = s_df.groupby('支払者')['金額'].sum()
        for p in parts:
            balances[p] += (actual.get(p, 0) - per_person)
            
    debtors = {p: -v for p, v in balances.items() if v < -0.1}
    creditors = {p: v for p, v in balances.items() if v > 0.1}
    
    res = []
    for d, d_val in debtors.items():
        for c, c_val in creditors.items():
            if d_val > 0.1 and c_val > 0.1:
                pay = min(d_val, c_val)
                res.append({"支払人": d, "受取人": c, "金額": int(pay)})
                d_val -= pay
                creditors[c] -= pay
                
    df_res = pd.DataFrame(res)
    return df_res.groupby(['支払人', '受取人'])['金額'].sum().reset_index() if not df_res.empty else df_res

# --- UI ---
st.title("💸 WariDA Pro")

if st.button("🔄 データを最新に更新"):
    st.cache_data.clear()
    st.rerun()

if 'my_name' not in st.session_state: st.session_state.my_name = ""
st.session_state.my_name = st.text_input("あなたの名前", st.session_state.my_name)

if st.session_state.my_name:
    session = st.selectbox("会を選択", ["1次会", "2次会", "3次会", "4次会", "5次会"])
    amount = st.number_input("金額", min_value=0, step=100)
    
    if st.button("送信（加算）"):
        try:
            client = get_gspread_client()
            sheet = client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
            sheet.append_row([session, st.session_state.my_name, amount])
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"書き込みエラー: {e}")

st.divider()

df = get_data()
tabs = st.tabs(["1次会", "2次会", "3次会", "4次会", "5次会"])
for i, s_name in enumerate(["1次会", "2次会", "3次会", "4次会", "5次会"]):
    with tabs[i]:
        s_df = df[df['会'] == s_name]
        if not s_df.empty:
            summary = s_df.groupby('支払者')['金額'].sum().reset_index()
            for _, row in summary.iterrows():
                cols = st.columns([2, 2, 1])
                cols[0].write(row['支払者'])
                cols[1].write(f"{int(row['金額'])} 円")
                if row['支払者'] == st.session_state.my_name:
                    if cols[2].button("❌", key=f"del_{s_name}_{row['支払者']}"):
                        client = get_gspread_client()
                        sheet = client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
                        all_rows = sheet.get_all_values()
                        new_rows = [r for r in all_rows if not (r[0] == s_name and r[1] == row['支払者'])]
                        sheet.clear()
                        sheet.append_rows(all_rows[0:1] + new_rows)
                        st.cache_data.clear()
                        st.rerun()
        else:
            st.info("データなし")

st.divider()
st.subheader("💰 最終的な支払い指示書")
res_df = calculate_settlements(df)
if not res_df.empty:
    st.table(res_df)
else:
    st.success("清算不要")
