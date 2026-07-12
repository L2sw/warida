import streamlit as st
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="💰 WariDA Pro", page_icon="💸")

def get_sheet():
    creds_dict = json.loads(st.secrets["gcp"]["data"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")

st.markdown("<h1 style='text-align: center; color: #ff6b6b;'>💸 WariDA Pro 💸</h1>", unsafe_allow_html=True)

try:
    sheet = get_sheet()
    data = sheet.get_all_records()
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- 入力 ---
st.subheader("📝 会の支払いを追加")
session_name = st.text_input("会の名前（例：1次会）")
session_cost = st.number_input("合計金額", min_value=0, step=100)
participants = st.text_input("参加者（カンマ区切りで入力：Aさん,Bさん,Cさん）")

if st.button("送信"):
    if session_name and session_cost > 0 and participants:
        sheet.append_row([session_name, session_cost, participants])
        st.balloons()
        st.rerun()
    else:
        st.warning("すべて入力してください。")

st.divider()

# --- 計算ロジック ---
st.subheader("🧮 誰がいくら払うべき？")
if data:
    # 負担額の集計用辞書
    debts = {}
    
    for row in data:
        cost = int(row['金額'])
        names = [n.strip() for n in row['参加者'].split(',')]
        per_person = cost / len(names)
        
        for name in names:
            debts[name] = debts.get(name, 0) + per_person
            
    # 結果表示
    st.write("### 参加者ごとの総負担額")
    for name, amount in debts.items():
        st.write(f"👤 {name}：{amount:.0f}円")
else:
    st.info("まだデータがありません。")

# --- リセット ---
with st.expander("⚠️ 全データをリセット"):
    if st.button("本当に消す"):
        sheet.delete_rows(2, len(data) + 1)
        st.rerun()
