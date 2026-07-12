import streamlit as st
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# ページ設定
st.set_page_config(page_title="💰 WariDA Pro", page_icon="💸")

# Google Sheets接続設定
def get_sheet():
    creds_dict = json.loads(st.secrets["gcp"]["data"])
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")

# セッション管理
if 'my_row_indices' not in st.session_state:
    st.session_state.my_row_indices = []

st.markdown("<h1 style='text-align: center; color: #ff6b6b;'>💸 WariDA Pro 💸</h1>", unsafe_allow_html=True)

# 接続とデータ取得
try:
    sheet = get_sheet()
    data = sheet.get_all_records()
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- 1. 入力セクション ---
st.subheader("📝 会の支払いを追加")
session_name = st.text_input("会の名前（例：1次会）")
session_cost = st.number_input("合計金額", min_value=0, step=100, format="%d")
participants = st.text_input("参加者（カンマ区切り：Aさん,Bさん,Cさん）")

if st.button("送信"):
    if session_name and session_cost >= 0 and participants:
        sheet.append_row([session_name, session_cost, participants])
        # 現在の行数をセッションに保存（ヘッダー考慮のため+2）
        st.session_state.my_row_indices.append(len(data) + 2)
        st.balloons()
        st.rerun()
    else:
        st.warning("すべて入力してください。")

st.divider()

# --- 2. 管理セクション（削除機能） ---
st.subheader("📊 記録一覧と削除")
if data:
    for i, row in enumerate(data):
        row_idx = i + 2
        col1, col2, col3 = st.columns([3, 1, 1])
        col1.write(f"{row['会名']} | {row['金額']}円 | {row['参加者']}")
        
        # 自分が送った行だけ削除ボタンを表示
        if row_idx in st.session_state.my_row_indices:
            if col3.button("❌ 削除", key=f"del_{row_idx}"):
                sheet.delete_rows(row_idx)
                st.session_state.my_row_indices.remove(row_idx)
                st.rerun()
        else:
            col3.caption("他人")
else:
    st.info("まだ記録はありません。")

st.divider()

# --- 3. 計算セクション ---
st.subheader("🧮 誰が誰にいくら渡す？（精算）")
if data:
    total_burden = {}
    paid_amount = {}
    
    for row in data:
        if not row.get('会名') or str(row.get('金額')) == "": continue
        
        try:
            cost = int(row['金額'])
            names = [n.strip() for n in str(row['参加者']).split(',')]
            payer = names[0] # 参加者の先頭を支払者とみなす
            
            per_person = cost / len(names)
            for name in names:
                total_burden[name] = total_burden.get(name, 0) + per_person
            paid_amount[payer] = paid_amount.get(payer, 0) + cost
        except (ValueError, ZeroDivisionError): continue
    
    # 差分計算（支払った額 - 負担すべき額）
    balance = {name: paid_amount.get(name, 0) - total_burden.get(name, 0) for name in total_burden}
    
    # 精算ロジック
    debtors = {k: v for k, v in balance.items() if v < 0}
    creditors = {k: v for k, v in balance.items() if v > 0}
    
    if not debtors and not creditors:
        st.write("精算する金額はありません。")
    else:
        for debtor, debt in debtors.items():
            for creditor, credit in creditors.items():
                if debt >= 0: break
                transfer = min(abs(debt), credit)
                if transfer > 0:
                    st.write(f"💸 **{debtor}さん** → **{creditor}さん** に **{transfer:.0f}円** 渡す")
                    debt += transfer
                    creditors[creditor] -= transfer
else:
    st.info("データがありません。")

# --- 4. リセットセクション ---
st.divider()
with st.expander("⚠️ 全データをリセット"):
    if st.button("🚨 全データを削除"):
        if len(data) > 0:
            sheet.delete_rows(2, len(data) + 1)
            st.session_state.my_row_indices = []
            st.rerun()
