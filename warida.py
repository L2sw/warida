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

# シートの1行目を「会名, 金額, 支払者, 参加者」にする必要があります
st.markdown("<h1 style='text-align: center; color: #ff6b6b;'>💸 WariDA Pro 💸</h1>", unsafe_allow_html=True)

try:
    sheet = get_sheet()
    data = sheet.get_all_records()
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- 入力 ---
st.subheader("📝 支払いを記録")
session_name = st.text_input("会の名前（例：1次会）")
amount = st.number_input("金額", min_value=0, step=100)
payer = st.text_input("支払った人（例：Aさん）")
participants = st.text_input("参加者（カンマ区切り：Aさん,Bさん,Cさん）")

if st.button("送信"):
    if session_name and amount >= 0 and payer and participants:
        sheet.append_row([session_name, amount, payer, participants])
        st.balloons()
        st.rerun()
    else:
        st.warning("すべて入力してください。")

st.divider()

# --- 計算 ---
st.subheader("🧮 精算結果")
if data:
    total_burden = {}
    paid_total = {}
    
    for row in data:
        cost = int(row['金額'])
        payer = row['支払者']
        names = [n.strip() for n in str(row['参加者']).split(',')]
        
        # 負担額計算
        per_person = cost / len(names)
        for name in names:
            total_burden[name] = total_burden.get(name, 0) + per_person
        
        # 支払額計算
        paid_total[payer] = paid_total.get(payer, 0) + cost
    
    # 差分（払った額 - 負担額）
    balance = {}
    all_people = set(list(total_burden.keys()) + list(paid_total.keys()))
    for p in all_people:
        balance[p] = paid_total.get(p, 0) - total_burden.get(p, 0)
    
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
