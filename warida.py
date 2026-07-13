import streamlit as st
import gspread
import pandas as pd
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- 設定 ---
st.set_page_config(page_title="WariDA Pro", layout="wide")

# --- CSS定義（タイル状表示用） ---
st.markdown("""
<style>
    .grid-container {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
        gap: 10px;
        margin-top: 10px;
    }
    .grid-item {
        border: 1px solid #444;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        background-color: #1a1a1a;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_gspread_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def get_sheet():
    return get_gspread_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")

def get_data():
    try:
        rows = get_sheet().get_all_values()
        if len(rows) <= 1: return pd.DataFrame(columns=['会', '支払者', '金額'])
        df = pd.DataFrame(rows[1:], columns=['会', '支払者', '金額'])
        df['金額'] = pd.to_numeric(df['金額'], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame(columns=['会', '支払者', '金額'])

def calculate_settlements(df):
    if df.empty: return pd.DataFrame(columns=["支払人", "受取人", "金額"])
    balances = {p: 0.0 for p in df['支払者'].unique()}
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

if st.button("🔄 更新"):
    st.cache_data.clear()
    st.rerun()

if 'my_name' not in st.session_state: st.session_state.my_name = ""
st.session_state.my_name = st.text_input("名前", st.session_state.my_name)

if st.session_state.my_name:
    col1, col2, col3 = st.columns([2, 1, 1])
    session = col1.selectbox("会", ["1次会", "2次会", "3次会", "4次会", "5次会"])
    amount = col2.number_input("金額", min_value=0, step=100)
    if col3.button("送信"):
        df = get_data()
        mask = (df['会'] == session) & (df['支払者'] == st.session_state.my_name)
        if mask.any():
            all_rows = get_sheet().get_all_values()
            for r_idx, r in enumerate(all_rows[1:], 2):
                if r[0] == session and r[1] == st.session_state.my_name:
                    get_sheet().update_cell(r_idx, 3, int(int(r[2]) + amount))
                    break
        else:
            get_sheet().append_row([session, st.session_state.my_name, int(amount)])
        st.rerun()

    st.divider()
    df = get_data()
    
    tabs = st.tabs(["1次会", "2次会", "3次会", "4次会", "5次会"])
    for i, s_name in enumerate(["1次会", "2次会", "3次会", "4次会", "5次会"]):
        with tabs[i]:
            s_df = df[df['会'] == s_name]
            # ここからCSSによるタイル表示
            st.markdown('<div class="grid-container">', unsafe_allow_html=True)
            for idx, row in s_df.iterrows():
                # HTMLでカードを作成
                st.markdown(f'''
                <div class="grid-item">
                    <small>{row['支払者']}</small><br>
                    <strong>¥{int(row['金額'])}</strong>
                </div>
                ''', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 削除ボタンは別の行に配置して誤操作を防ぐ
            if not s_df[s_df['支払者'] == st.session_state.my_name].empty:
                if st.button(f"{st.session_state.my_name} さんの履歴を消去", key=f"del_{i}"):
                    all_rows = get_sheet().get_all_values()
                    new_rows = [r for r in all_rows[1:] if not (r[0] == s_name and r[1] == st.session_state.my_name)]
                    get_sheet().batch_clear(["A2:C1000"])
                    if new_rows: get_sheet().append_rows(new_rows)
                    st.rerun()

    st.divider()
    st.subheader("💰 最終清算")
    st.table(calculate_settlements(df))

    st.divider()
    if st.button("⚠️ 全データ削除"):
        get_sheet().batch_clear(["A2:C1000"])
        st.rerun()
else:
    st.warning("名前を入力してください")
