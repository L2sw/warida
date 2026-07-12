import streamlit as st
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# ページ設定
st.set_page_config(page_title="💰 WariDA Pro", page_icon="💸")

# 接続設定
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

# タイトル
st.markdown("<h1 style='text-align: center; color: #ff6b6b;'>💸 WariDA Pro 💸</h1>", unsafe_allow_html=True)

# 接続処理
try:
    sheet = get_sheet()
    data = sheet.get_all_records()
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- 入力セクション ---
st.subheader("📝 会の支払いを追加")
session_name = st.text_input("会の名前（例：1次会）")
session_cost = st.number_input("合計金額", min_value=0, step=100, format="%d")
participants = st.text_input("参加者（カンマ区切り：Aさん,Bさん,Cさん）")

if st.button("送信"):
    if session_name and session_cost >= 0 and participants:
        sheet.append_row([session_name, session_cost, participants])
        st.balloons()
        st.rerun()
    else:
        st.warning("すべて入力してください。")

st.divider()

# --- 計算セクション ---
st.subheader("🧮 誰がいくら払うべき？")
if data:
    debts = {}
    for row in data:
        # 空行や不正な行をスキップ
        if not row.get('会名') or str(row.get('金額')) == "":
            continue
            
        try:
            cost = int(row['金額'])
            names = [n.strip() for n in str(row['参加者']).split(',')]
            per_person = cost / len(names)
            
            for name in names:
                debts[name] = debts.get(name, 0) + per_person
        except (ValueError, ZeroDivisionError):
            continue
            
    if debts:
        st.write("### 参加者ごとの総負担額")
        for name, amount in debts.items():
            st.write(f"👤 {name}：{amount:.0f}円")
    else:
        st.info("有効なデータがありません。")
else:
    st.info("まだ記録はありません。")

# --- 管理セクション ---
st.divider()
st.subheader("⚙️ データ管理")

# 記録一覧の表示と削除
if data:
    with st.expander("📊 記録の一覧と削除"):
        for i, row in enumerate(data):
            st.write(f"{row['会名']} | {row['金額']}円 | {row['参加者']}")
            if st.button(f"削除: {row['会名']}", key=f"del_{i}"):
                sheet.delete_rows(i + 2)
                st.rerun()

# 全リセット
with st.expander("⚠️ 全データをリセット"):
    if st.button("🚨 全データを削除"):
        if len(data) > 0:
            sheet.delete_rows(2, len(data) + 1)
            st.rerun()
