import streamlit as st
import pandas as pd
import re
import gspread
from google.oauth2.service_account import Credentials

# --- 設定 ---
st.set_page_config(page_title="WariDA Pro", layout="wide")

# 名前制限のバリデーション (4文字以内、記号不可)
def is_valid_name(name):
    pattern = r'^[ぁ-んァ-ン一-龠A-Za-z0-9]{1,4}$'
    return re.match(pattern, name) is not None

# 接続用キャッシュ (メモリ効率化)
@st.cache_resource
def get_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds)

# データ取得 (TTL 30秒で負荷分散)
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

# --- UI ---
st.title("💸 WariDA Pro")

# 端末紐づけ：セッション状態を活用
if 'my_name' not in st.session_state: st.session_state.my_name = ""

if not st.session_state.my_name:
    input_name = st.text_input("あなたの名前（4文字以内・記号不可）")
    if st.button("設定"):
        if is_valid_name(input_name):
            st.session_state.my_name = input_name
            st.rerun()
        else:
            st.error("不正な名前です。記号不可・4文字以内で入力してください。")
    st.stop() # 名前が確定するまで後続処理をストップ

st.write(f"ログイン中: **{st.session_state.my_name}** さん")

# --- 送信フォーム ---
with st.expander("支出を入力", expanded=True):
    col1, col2, col3 = st.columns([2, 2, 1])
    session = col1.selectbox("会", ["1次会", "2次会", "3次会", "4次会", "5次会"])
    amount = col2.number_input("金額", min_value=0, step=100)
    if col3.button("送信"):
        sheet = get_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
        sheet.append_row([session, st.session_state.my_name, int(amount)])
        st.cache_data.clear()
        st.rerun()

# --- 履歴表示（表形式） ---
df = get_data()
tabs = st.tabs(["1次会", "2次会", "3次会", "4次会", "5次会"])
for i, s_name in enumerate(["1次会", "2次会", "3次会", "4次会", "5次会"]):
    with tabs[i]:
        summary = df[df['会'] == s_name].groupby('支払者')['金額'].sum().reset_index()
        html = """<table style="width:100%; border-collapse: collapse;">
            <thead><tr style="border-bottom: 2px solid #555;">
                <th style="text-align:left; padding:5px;">支払者</th>
                <th style="text-align:right; padding:5px;">合計金額</th>
            </tr></thead><tbody>"""
        for _, row in summary.iterrows():
            html += f"<tr><td style='padding:5px;'>{row['支払者']}</td><td style='text-align:right; padding:5px;'>¥{int(row['金額'])}</td></tr>"
        html += "</tbody></table>"
        st.markdown(html, unsafe_allow_html=True)

        # 削除ボタン（自分の履歴のみ表示）
        if not summary[summary['支払者'] == st.session_state.my_name].empty:
            if st.button(f"この会の {st.session_state.my_name} さんの履歴を削除", key=f"del_{i}"):
                sheet = get_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
                rows = sheet.get_all_values()
                new_rows = [r for r in rows[1:] if not (r[0] == s_name and r[1] == st.session_state.my_name)]
                sheet.batch_clear(["A2:C1000"])
                if new_rows: sheet.append_rows(new_rows)
                st.cache_data.clear()
                st.rerun()

# --- 最終清算計算 ---
st.subheader("💰 最終清算")
def calculate_settlements(df):
    if df.empty: return None
    balances = {p: 0.0 for p in df['支払者'].unique()}
    for s in df['会'].unique():
        s_df = df[df['会'] == s]
        parts = s_df['支払者'].unique()
        per = s_df['金額'].sum() / len(parts)
        for p in parts: balances[p] += (s_df[s_df['支払者']==p]['金額'].sum() - per)
    debtors = sorted([(p, -v) for p, v in balances.items() if v < -0.01], key=lambda x: x[1], reverse=True)
    creditors = sorted([(p, v) for p, v in balances.items() if v > 0.01], key=lambda x: x[1], reverse=True)
    res = []
    d, c = 0, 0
    while d < len(debtors) and c < len(creditors):
        a = min(debtors[d][1], creditors[c][1])
        res.append({"支払人": debtors[d][0], "受取人": creditors[c][0], "金額": int(a)})
        debtors[d] = (debtors[d][0], debtors[d][1] - a)
        creditors[c] = (creditors[c][0], creditors[c][1] - a)
        if debtors[d][1] < 0.01: d += 1
        if creditors[c][1] < 0.01: c += 1
    return pd.DataFrame(res)

res = calculate_settlements(df)
if res is not None and not res.empty: st.table(res)
else: st.write("清算不要")

if st.button("全データをクリア"):
    get_client().open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").batch_clear(["A2:C1000"])
    st.cache_data.clear()
    st.rerun()
