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

# 自分が送信した記録の「行番号」を記憶する箱
if 'my_row_indices' not in st.session_state:
    st.session_state.my_row_indices = []

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
session_cost = st.number_input("合計金額", min_value=0, step=100, format="%d")
participants = st.text_input("参加者（カンマ区切り：Aさん,Bさん,Cさん）")

if st.button("送信"):
    if session_name and session_cost >= 0 and participants:
        # 書き込み実行
        sheet.append_row([session_name, session_cost, participants])
        # 新しく追加された行番号をセッションに記憶する
        # (ヘッダー除いて現在の行数 + 1)
        st.session_state.my_row_indices.append(len(data) + 2)
        st.balloons()
        st.rerun()
    else:
        st.warning("すべて入力してください。")

st.divider()

# --- 管理セクション ---
st.subheader("📊 記録一覧と削除")
if data:
    for i, row in enumerate(data):
        row_idx = i + 2  # スプレッドシート上の行番号
        
        col1, col2, col3 = st.columns([3, 1, 1])
        col1.write(f"{row['会名']} | {row['金額']}円 | {row['参加者']}")
        
        # 自分のブラウザで送信した行番号かチェック
        if row_idx in st.session_state.my_row_indices:
            if col3.button("❌ 削除", key=f"del_{row_idx}"):
                sheet.delete_rows(row_idx)
                # 削除したらリストからも除去
                st.session_state.my_row_indices.remove(row_idx)
                st.rerun()
        else:
            col3.caption("他人")
else:
    st.info("まだ記録はありません。")

st.divider()

# --- 計算 ---
st.subheader("🧮 誰がいくら払うべき？")
if data:
    debts = {}
    for row in data:
        if not row.get('会名') or str(row.get('金額')) == "": continue
        try:
            cost = int(row['金額'])
            names = [n.strip() for n in str(row['参加者']).split(',')]
            per_person = cost / len(names)
            for name in names:
                debts[name] = debts.get(name, 0) + per_person
        except (ValueError, ZeroDivisionError): continue
            
    for name, amount in debts.items():
        st.write(f"👤 {name}：{amount:.0f}円")

# --- リセット ---
with st.expander("⚠️ 全データをリセット"):
    if st.button("🚨 全データを削除"):
        sheet.delete_rows(2, len(data) + 1)
        st.session_state.my_row_indices = []
        st.rerun()
