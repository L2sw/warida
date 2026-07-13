import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="WariDA Pro", layout="wide")

# 1. 接続・データ取得（キャッシュ）
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

# 2. 清算計算
def calculate_settlements(df):
    if df.empty: return pd.DataFrame(columns=["支払人", "受取人", "金額"])
    balances = {p: 0.0 for p in df['支払者'].unique()}
    for session in df['会'].unique():
        s_df = df[df['会'] == session]
        parts = s_df['支払者'].unique()
        if len(parts) == 0: continue
        per_person = s_df['金額'].sum() / len(parts)
        for p in parts:
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

# 3. UI表示
st.title("💸 WariDA Pro")

if 'my_name' not in st.session_state: st.session_state.my_name = ""
st.session_state.my_name = st.text_input("あなたの名前", st.session_state.my_name)

if st.session_state.my_name:
    # 入力
    col1, col2, col3 = st.columns([2, 2, 1])
    session = col1.selectbox("会", ["1次会", "2次会", "3次会", "4次会", "5次会"])
    amount = col2.number_input("金額", min_value=0, step=100)
    if col3.button("送信"):
        sheet = get_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
        sheet.append_row([session, st.session_state.my_name, int(amount)])
        st.cache_data.clear()
        st.rerun()

    df = get_data()

    # ★ここが肝：HTMLテーブルによる固定表示（スマホでも列が崩れない）
    tabs = st.tabs(["1次会", "2次会", "3次会", "4次会", "5次会"])
    for i, s_name in enumerate(["1次会", "2次会", "3次会", "4次会", "5次会"]):
        with tabs[i]:
            summary = df[df['会'] == s_name].groupby('支払者')['金額'].sum().reset_index()
            html = """
            <table style="width:100%; border-collapse: collapse; font-size: 14px;">
                <thead><tr style="border-bottom: 2px solid #555;">
                    <th style="text-align:left; padding:5px;">支払者</th>
                    <th style="text-align:right; padding:5px;">合計金額</th>
                </tr></thead>
                <tbody>
            """
            for _, row in summary.iterrows():
                html += f"<tr><td style='padding:5px;'>{row['支払者']}</td><td style='text-align:right; padding:5px;'>¥{int(row['金額'])}</td></tr>"
            html += "</tbody></table>"
            st.markdown(html, unsafe_allow_html=True)

    # 最終清算
    st.subheader("💰 最終清算")
    res = calculate_settlements(df)
    st.table(res)

    if st.button("全削除"):
        get_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").batch_clear(["A2:C1000"])
        st.cache_data.clear()
        st.rerun()
