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

try:
    db_sheet = get_sheet("warikan_db")
    member_sheet = get_sheet("メンバー")
    data = db_sheet.get_all_records()
    members = [row['名前'] for row in member_sheet.get_all_records()]
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- 入力 ---
st.subheader("📝 自分の支払いを登録")
my_name = st.selectbox("あなたのお名前", members)
amount = st.number_input("支払った金額", min_value=0, step=100)
# 参加者を選択（デフォルトは全メンバー）
selected_participants = st.multiselect("参加者を選択", members, default=members)

if st.button("送信"):
    if amount >= 0 and selected_participants:
        # スプレッドシートには「支払った人(my_name)」「金額」「参加者」を記録
        participants_str = ",".join(selected_participants)
        db_sheet.append_row([my_name, amount, participants_str])
        st.balloons()
        st.rerun()
    else:
        st.warning("金額と参加者を設定してください。")

st.divider()

# --- 計算 ---
st.subheader("🧮 精算結果")
if data:
    total_burden = {m: 0 for m in members}
    paid_total = {m: 0 for m in members}
    
    for row in data:
        cost = int(row['金額'])
        payer = row['支払者'] # スプレッドシート列名を「支払者」にしてください
        names = [n.strip() for n in str(row['参加者']).split(',')]
        
        per_person = cost / len(names)
        for name in names:
            total_burden[name] += per_person
        paid_total[payer] += cost
    
    balance = {m: paid_total[m] - total_burden[m] for m in members}
    
    debtors = sorted({k: v for k, v in balance.items() if v < 0}.items(), key=lambda x: x[1])
    creditors = sorted({k: v for k, v in balance.items() if v > 0}.items(), key=lambda x: x[1], reverse=True)
    
    for debtor, debt in debtors:
        for creditor, credit in creditors:
            if debt >= 0: break
            transfer = min(abs(debt), credit)
            if transfer > 0:
                st.write(f"💸 **{debtor}さん** → **{creditor}さん** に **{transfer:.0f}円** 渡す")
                debt += transfer
                creditors[creditors.index((creditor, credit))] = (creditor, credit - transfer)
else:
    st.info("データがありません。")
