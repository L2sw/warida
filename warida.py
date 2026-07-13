import streamlit as st
import pandas as pd
from datetime import datetime

# Streamlitの基本設定
st.set_page_config(page_title="WariDA Pro", layout="wide")

# CSSによるタイル表示設定
st.markdown("""
<style>
    .compact-table { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin-bottom: 20px; }
    .compact-item { background-color: #262730; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #444; }
</style>
""", unsafe_allow_html=True)

# 1. 接続関数 (動的インポートでメモリ節約)
@st.cache_resource
def get_gspread_client():
    import gspread
    from google.oauth2.service_account import Credentials
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds)

# 2. データ取得関数 (ttlでAPIアクセスを抑制)
@st.cache_data(ttl=60)
def get_data():
    try:
        sheet = get_gspread_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
        rows = sheet.get_all_values()
        if len(rows) <= 1: return pd.DataFrame(columns=['会', '支払者', '金額'])
        df = pd.DataFrame(rows[1:], columns=['会', '支払者', '金額'])
        df['金額'] = pd.to_numeric(df['金額'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"接続エラー: {e}")
        return pd.DataFrame(columns=['会', '支払者', '金額'])

# 3. 清算計算ロジック
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

# --- メイン UI ---
st.title("💸 WariDA Pro")

if 'my_name' not in st.session_state: st.session_state.my_name = ""
st.session_state.my_name = st.text_input("あなたの名前", st.session_state.my_name)

if st.session_state.my_name:
    # 送信フォーム
    with st.expander("支出を入力", expanded=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        session = col1.selectbox("会", ["1次会", "2次会", "3次会", "4次会", "5次会"])
        amount = col2.number_input("金額", min_value=0, step=100)
        if col3.button("送信"):
            sheet = get_gspread_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
            # 既存の合計を計算してから更新、または追記するロジック
            df = get_data()
            mask = (df['会'] == session) & (df['支払者'] == st.session_state.my_name)
            if mask.any():
                all_rows = sheet.get_all_values()
                for r_idx, r in enumerate(all_rows[1:], 2):
                    if r[0] == session and r[1] == st.session_state.my_name:
                        new_val = int(r[2]) + int(amount)
                        sheet.update_cell(r_idx, 3, new_val)
                        break
            else:
                sheet.append_row([session, st.session_state.my_name, int(amount)])
            st.cache_data.clear()
            st.rerun()

    # 表示セクション
    df = get_data()
    tabs = st.tabs(["1次会", "2次会", "3次会", "4次会", "5次会"])
    for i, s_name in enumerate(["1次会", "2次会", "3次会", "4次会", "5次会"]):
        with tabs[i]:
            s_df = df[df['会'] == s_name]
            st.markdown('<div class="compact-table">', unsafe_allow_html=True)
            for _, row in s_df.iterrows():
                st.markdown(f'<div class="compact-item">{row["支払者"]}<br><strong>¥{int(row["金額"])}</strong></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button(f"{s_name} の自分の履歴を消去", key=f"del_{i}"):
                sheet = get_gspread_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
                rows = sheet.get_all_values()
                new_rows = [r for r in rows[1:] if not (r[0] == s_name and r[1] == st.session_state.my_name)]
                sheet.batch_clear(["A2:C1000"])
                if new_rows: sheet.append_rows(new_rows)
                st.cache_data.clear()
                st.rerun()

    # 清算表
    st.subheader("💰 最終清算")
    res = calculate_settlements(df)
    if not res.empty:
        st.table(res)
    else:
        st.success("清算不要")

    if st.button("⚠️ 全データ削除"):
        get_gspread_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").batch_clear(["A2:C1000"])
        st.cache_data.clear()
        st.rerun()
else:
    st.info("名前を入力すると開始できます")
