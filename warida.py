import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

def get_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=5)
def load_data():
    client = get_client()
    sheet = client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
    rows = sheet.get_all_values()
    if len(rows) > 1:
        df = pd.DataFrame(rows[1:], columns=['会', '支払者', '金額'])
        df['金額'] = pd.to_numeric(df['金額'], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=['会', '支払者', '金額'])

st.set_page_config(page_title="WariDA", layout="wide")
st.title("💸 WariDA Pro")

if 'my_name' not in st.session_state:
    st.session_state.my_name = None

if not st.session_state.my_name:
    st.session_state.my_name = st.text_input("あなたの名前")
    if st.button("確定"): st.rerun()
else:
    st.write(f"ログイン中: **{st.session_state.my_name}** さん")
    session = st.selectbox("会を選択", ["1次会", "2次会", "3次会", "4次会", "5次会"])
    amount = st.number_input("追加する金額", min_value=0, step=100)
    
    if st.button("送信（加算）"):
        client = get_client()
        client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db").append_row([session, st.session_state.my_name, amount])
        st.cache_data.clear()
        st.rerun()

st.divider()
st.subheader("📋 支払い履歴（会別）")

df = load_data()
sessions = ["1次会", "2次会", "3次会", "4次会", "5次会"]
tabs = st.tabs(sessions)

for i, s_name in enumerate(sessions):
    with tabs[i]:
        # その会のデータを抽出して集計
        filtered_df = df[df['会'] == s_name]
        summary_df = filtered_df.groupby('支払者')['金額'].sum().reset_index()
        
        if not summary_df.empty:
            # 削除ボタン用のカラム作成
            for idx, row in summary_df.iterrows():
                col1, col2, col3 = st.columns([1, 3, 2])
                col1.write(f"No.{idx+1}")
                col2.write(f"{row['支払者']}: {row['金額']}円")
                
                # 本人のみ削除ボタンを表示
                if row['支払者'] == st.session_state.my_name:
                    if col3.button("❌ 削除", key=f"del_{s_name}_{idx}"):
                        # スプレッドシートから該当する会・支払者のデータをすべて削除
                        client = get_client()
                        sheet = client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")
                        all_rows = sheet.get_all_values()
                        new_rows = [row_data for row_data in all_rows if not (row_data[0] == s_name and row_data[1] == st.session_state.my_name)]
                        sheet.clear()
                        sheet.update(all_rows[0:1] + new_rows) # ヘッダー維持
                        st.cache_data.clear()
                        st.rerun()
        else:
            st.info("まだ履歴がありません")
