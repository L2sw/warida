import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# --- 設定 ---
st.set_page_config(page_title="WariDA Pro", layout="wide")

# --- 接続 (シングルトン) ---
@st.cache_resource
def get_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds)

# --- データ取得 (TTLでキャッシュ) ---
@st.cache_data(ttl=60)
def get_data():
    sheet = get_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
    rows = sheet.get_all_values()
    if len(rows) <= 1: return pd.DataFrame(columns=['会', '支払者', '金額'])
    df = pd.DataFrame(rows[1:], columns=['会', '支払者', '金額'])
    df['金額'] = pd.to_numeric(df['金額'], errors='coerce').fillna(0)
    return df

# --- UI ---
st.title("💸 WariDA Pro")

# 名前設定
if 'my_name' not in st.session_state: st.session_state.my_name = ""
st.session_state.my_name = st.text_input("あなたの名前", st.session_state.my_name)

if st.session_state.my_name:
    # 入力セクション
    with st.expander("入力する", expanded=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        session = col1.selectbox("会", ["1次会", "2次会", "3次会", "4次会", "5次会"])
        amount = col2.number_input("金額", min_value=0, step=100)
        if col3.button("送信"):
            sheet = get_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
            sheet.append_row([session, st.session_state.my_name, int(amount)])
            st.cache_data.clear()
            st.rerun()

    st.divider()
    df = get_data()

    # 会ごとの表示（集約表示）
    st.subheader("履歴一覧")
    tabs = st.tabs(["1次会", "2次会", "3次会", "4次会", "5次会"])
    for i, s_name in enumerate(["1次会", "2次会", "3次会", "4次会", "5次会"]):
        with tabs[i]:
            s_df = df[df['会'] == s_name]
            if not s_df.empty:
                summary = s_df.groupby('支払者')['金額'].sum().reset_index()
                st.table(summary)
            else:
                st.write("データなし")

    st.divider()
    # 最終清算表（HTMLテーブルによる列表示）
    st.subheader("💰 最終清算（支払指示）")
    if not df.empty:
        # 計算ロジック
        balances = df.groupby('支払者')['金額'].sum()
        avg = balances.sum() / len(df['支払者'].unique())
        diffs = balances - avg
        
        # 結果をテーブル形式で作成
        st.write("※各参加者の過不足は以下の通りです")
        st.table(diffs.apply(lambda x: f"{int(x)} 円"))
    
    st.divider()
    if st.button("全データをクリアする"):
        sheet = get_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
        sheet.batch_clear(["A2:C1000"])
        st.cache_data.clear()
        st.rerun()
else:
    st.info("名前を入力すると開始できます")
