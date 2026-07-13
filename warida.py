import streamlit as st
import pandas as pd
import re
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 設定 ---
st.set_page_config(page_title="WariDA Pro", layout="wide")

# --- 2. ユーティリティ・関数 ---
def is_valid_name(name):
    # 4文字以内、記号不可（日本語・英数字のみ）
    return re.match(r'^[ぁ-んァ-ン一-龠A-Za-z0-9]{1,4}$', name) is not None

@st.cache_resource
def get_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds)

@st.cache_data(ttl=30)
def get_data():
    try:
        sheet = get_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
        values = sheet.get_all_values()
        if len(values) <= 1: return pd.DataFrame(columns=['会', '支払者', '金額'])
        df = pd.DataFrame(values[1:], columns=['会', '支払者', '金額'])
        df['金額'] = pd.to_numeric(df['金額'], errors='coerce').fillna(0).astype(int)
        return df
    except:
        return pd.DataFrame(columns=['会', '支払者', '金額'])

# --- 3. UIロジック ---
st.title("💸 WariDA Pro")

# 端末紐づけ：セッション管理
if 'my_name' not in st.session_state: st.session_state.my_name = ""

# 名前の入力・バリデーション
if not st.session_state.my_name:
    input_name = st.text_input("あなたの名前（4文字以内・記号不可）")
    if st.button("設定"):
        if is_valid_name(input_name):
            st.session_state.my_name = input_name
            st.rerun()
        else:
            st.error("入力エラー：4文字以内の日本語・英数字のみ入力可能です。")
    st.stop()

st.sidebar.write(f"ログイン中: **{st.session_state.my_name}**")
if st.sidebar.button("ログアウト"):
    st.session_state.my_name = ""
    st.rerun()

# 入力フォーム
with st.expander("支出を入力", expanded=True):
    col1, col2, col3 = st.columns([2, 2, 1])
    session = col1.selectbox("会", ["1次会", "2次会", "3次会", "4次会", "5次会"])
    amount = col2.number_input("金額", min_value=0, step=100)
    if col3.button("送信"):
        sheet = get_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
        sheet.append_row([session, st.session_state.my_name, int(amount)])
        st.cache_data.clear()
        st.rerun()

# 履歴表示（HTML表形式）
df = get_data()
tabs = st.tabs(["1次会", "2次会", "3次会", "4次会", "5次会"])
for i, s_name in enumerate(["1次会", "2次会", "3次会", "4次会", "5次会"]):
    with tabs[i]:
        s_df = df[df['会'] == s_name]
        summary = s_df.groupby('支払者')['金額'].sum().reset_index()
        
        # 表表示
        html = """<table style="width:100%; border-collapse: collapse;">
            <thead><tr style="border-bottom: 2px solid #555;">
                <th style="text-align:left; padding:8px;">名前</th>
                <th style="text-align:right; padding:8px;">金額</th>
                <th style="text-align:center; padding:8px;">操作</th>
            </tr></thead><tbody>"""
        for _, row in summary.iterrows():
            # 自分の行にだけ削除ボタンを表示
            delete_btn = ""
            if row['支払者'] == st.session_state.my_name:
                delete_btn = f'<a href="?del={i}">削除</a>' # 削除トリガー
            html += f"<tr><td style='padding:8px;'>{row['支払者']}</td><td style='text-align:right; padding:8px;'>¥{int(row['金額'])}</td><td style='text-align:center;'>{delete_btn}</td></tr>"
        html += "</tbody></table>"
        st.markdown(html, unsafe_allow_html=True)

        # 削除ボタンのロジック（URLパラメータ経由で再読み込み）
        if st.query_params.get("del") == str(i):
            sheet = get_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
            all_rows = sheet.get_all_values()
            new_rows = [r for r in all_rows[1:] if not (r[0] == s_name and r[1] == st.session_state.my_name)]
            sheet.batch_clear(["A2:C1000"])
            if new_rows: sheet.append_rows(new_rows)
            st.query_params.clear()
            st.cache_data.clear()
            st.rerun()

# --- 最終清算表 ---
st.subheader("💰 最終清算")
if not df.empty:
    balances = df.groupby('支払者')['金額'].sum()
    avg = balances.sum() / len(balances)
    res = pd.DataFrame({'差額': (balances - avg).astype(int)})
    st.table(res)

if st.button("⚠️ 全データ削除"):
    get_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").batch_clear(["A2:C1000"])
    st.cache_data.clear()
    st.rerun()
