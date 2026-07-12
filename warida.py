import streamlit as st
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="💰 WariDA Pro", page_icon="💸")

def get_sheet(sheet_name):
    creds_dict = json.loads(st.secrets["gcp"]["data"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet(sheet_name)

st.markdown("<h1 style='text-align: center; color: #ff6b6b;'>💸 WariDA Pro 💸</h1>", unsafe_allow_html=True)

# データ取得
try:
    db_sheet = get_sheet("warikan_db")
    member_sheet = get_sheet("メンバー")
    db_data = db_sheet.get_all_records()
    member_data = member_sheet.get_all_records()
    members = [row[list(row.keys())[0]] for row in member_data]
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- 入力 ---
st.subheader("📝 自分の支払いを登録")
session_name = st.text_input("会の名前（例：1次会）")
my_name = st.selectbox("あなたのお名前", members)
amount = st.number_input("支払った金額", min_value=0, step=100)
participants = st.multiselect("参加者を選択", members, default=members)

if st.button("送信"):
    if session_name and amount >= 0 and participants:
        db_sheet.append_row([session_name, my_name, amount, ",".join(participants)])
        st.balloons()
        st.rerun()

st.divider()

# --- 計算 ---
st.subheader("🧮 会ごとの精算結果")
if db_data:
    # 会ごとにデータをまとめる
    sessions = {}
    for row in db_data:
        keys = list(row.keys())
        s_name = row[keys[0]]
        if s_name not in sessions: sessions[s_name] = []
        sessions[s_name].append(row)
    
    for s_name, rows in sessions.items():
        st.write(f"### 📍 {s_name}")
        total_burden = {m: 0 for m in members}
        paid_total = {m: 0 for m in members}
        
        for row in rows:
            keys = list(row.keys())
            cost = int(row[keys[2]])
            payer = row[keys[1]]
            names = [n.strip() for n in str(row[keys[3]]).split(',')]
            
            per_person = cost / len(names)
            for name in names: total_burden[name] += per_person
            paid_total[payer] += cost
            
        balance = {m: paid_total.get(m, 0) - total_burden.get(m, 0) for m in members}
        debtors = sorted({k: v for k, v in balance.items() if v < 0}.items(), key=lambda x: x[1])
        creditors = sorted({k: v for k, v in balance.items() if v > 0}.items(), key=lambda x: x[1], reverse=True)
        
        for d, debt in debtors:
            for c, credit in creditors:
                if debt >= 0: break
                transfer = min(abs(debt), credit)
                if transfer > 0:
                    st.write(f"💸 {d}さん → {c}さんに {transfer:.0f}円")
                    debt += transfer
                    creditors[creditors.index((c, credit))] = (c, credit - transfer)
else:
    st.info("データがありません。")
