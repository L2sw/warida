import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials

# --- 設定 ---
st.set_page_config(page_title="WariDA Pro", layout="wide")

# 堅牢なCSSグリッドレイアウト
st.markdown("""
<style>
    .grid-fixed {
        display: grid;
        grid-template-columns: repeat(4, 1fr); /* 常に4列固定 */
        gap: 10px;
        margin-top: 10px;
    }
    .grid-card {
        background-color: #262730;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #444;
        text-align: center;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

# --- 接続とデータ取得 ---
@st.cache_resource
def get_client():
    import gspread
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds)

@st.cache_data(ttl=30)
def get_data():
    try:
        sheet = get_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
        rows = sheet.get_all_values()
        if len(rows) <= 1: return pd.DataFrame(columns=['会', '支払者', '金額'])
        df = pd.DataFrame(rows[1:], columns=['会', '支払者', '金額'])
        df['金額'] = pd.to_numeric(df['金額'], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame(columns=['会', '支払者', '金額'])

# --- 清算計算 ---
def calculate_settlements(df):
    if df.empty: return pd.DataFrame(columns=["支払人", "受取人", "金額"])
    balances = {p: 0.0 for p in df['支払者'].unique()}
    for session in df['会'].unique():
        s_df = df[df['会'] == session]
        participants = s_df['支払者'].unique()
        if len(participants) == 0: continue
        per_person = s_df['金額'].sum() / len(participants)
        for p in participants:
            balances[p] += (s_df[s_df['支払者'] == p]['金額'].sum() - per_person)
            
    debtors = sorted([(p, -v) for p, v in balances.items() if v < -0.01], key=lambda x: x[1], reverse=True)
    creditors = sorted([(p, v) for p, v in balances.items() if v > 0.01], key=lambda x: x[1], reverse=True)
    
    results = []
    d_idx, c_idx = 0, 0
    while d_idx < len(debtors) and c_idx < len(creditors):
        d_name, d_val = debtors[d_idx]
        c_name, c_val = creditors[c_idx]
        amount = min(d_val, c_val)
        results.append({"支払人": d_name, "受取人": c_name, "金額": int(amount)})
        debtors[d_idx] = (d_name, d_val - amount)
        creditors[c_idx] = (c_name, c_val - amount)
        if debtors[d_idx][1] < 0.01: d_idx += 1
        if creditors[c_idx][1] < 0.01: c_idx += 1
    return pd.DataFrame(results)

# --- UI ---
st.title("💸 WariDA Pro")

if 'my_name' not in st.session_state: st.session_state.my_name = ""
st.session_state.my_name = st.text_input("名前", st.session_state.my_name)

if st.session_state.my_name:
    # 送信
    col1, col2, col3 = st.columns([2, 1, 1])
    session = col1.selectbox("会", ["1次会", "2次会", "3次会", "4次会", "5次会"])
    amount = col2.number_input("金額", min_value=0, step=100)
    if col3.button("送信"):
        sheet = get_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
        sheet.append_row([session, st.session_state.my_name, int(amount)])
        st.cache_data.clear()
        st.rerun()

    df = get_data()
    
    # コンパクトなグリッド表示
    tabs = st.tabs(["1次会", "2次会", "3次会", "4次会", "5次会"])
    for i, s_name in enumerate(["1次会", "2次会", "3次会", "4次会", "5次会"]):
        with tabs[i]:
            s_df = df[df['会'] == s_name]
            # 集約して表示
            summary = s_df.groupby('支払者')['金額'].sum().reset_index()
            st.markdown('<div class="grid-fixed">', unsafe_allow_html=True)
            for _, row in summary.iterrows():
                st.markdown(f'<div class="grid-card">{row["支払者"]}<br><b>¥{int(row["金額"])}</b></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # 清算表（3列固定）
    st.subheader("💰 最終清算")
    res = calculate_settlements(df)
    if not res.empty:
        st.table(res)
    else:
        st.write("精算不要")

    if st.button("全削除"):
        get_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").batch_clear(["A2:C1000"])
        st.cache_data.clear()
        st.rerun()
