import streamlit as st
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# ページ設定
st.set_page_config(page_title="💰 WariDA", page_icon="💸")

def get_sheet():
    creds_dict = json.loads(st.secrets["gcp"]["data"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")

# セッション管理：自分が送信した記録のキーをブラウザごとに保存
if 'my_entries' not in st.session_state:
    st.session_state.my_entries = []

st.markdown("<h1 style='text-align: center; color: #ff6b6b;'>💸 WariDA 💸</h1>", unsafe_allow_html=True)

try:
    sheet = get_sheet()
    data = sheet.get_all_records()
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- 入力画面 ---
st.subheader("📝 支払いを追加")
col1, col2 = st.columns(2)
with col1:
    name = st.text_input("名前（重複不可）")
with col2:
    # step=1で整数のみ、min_valueで0以上を強制
    amount = st.number_input("金額 (整数のみ)", min_value=0, step=1, format="%d")

if st.button("🚀 送信！"):
    # エラーチェック
    existing_names = [d['名前'] for d in data]
    if not name:
        st.warning("名前を入力してね！")
    elif name in existing_names:
        st.error(f"「{name}」さんはすでに登録されています！")
    else:
        sheet.append_row([name, amount])
        st.session_state.my_entries.append(name) # 自分の記録として保存
        st.balloons()
        st.rerun()

st.divider()

# --- データ管理と削除画面 ---
st.subheader("📊 みんなの支払い")
if not data:
    st.info("まだ記録はないよ！")
else:
    for i, d in enumerate(data):
        col1, col2, col3 = st.columns([2, 1, 1])
        col1.write(f"👤 {d['名前']}")
        col2.write(f"💰 {d['金額']}円")
        
        # 削除ボタン：自分の記録、または自分が送信した記録なら表示（または管理者権限）
        if d['名前'] in st.session_state.my_entries:
            if col3.button("❌ 消す", key=f"del_{i}"):
                sheet.delete_rows(i + 2)
                st.rerun()
        else:
            col3.caption("他人")

st.divider()

# --- 計算画面 ---
if st.button("🧮 計算！"):
    if not data:
        st.warning("データがないよ！")
    else:
        total = sum(d['金額'] for d in data)
        avg = total / len(data)
        st.write(f"### 合計: {total}円 / 1人: {avg:.0f}円")
        for d in data:
            diff = d['金額'] - avg
            if diff < 0:
                st.error(f"😢 {d['名前']}さん：あと {abs(diff):.0f} 円")
            else:
                st.info(f"✨ {d['名前']}さん： {diff:.0f} 円受け取る")
