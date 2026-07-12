import streamlit as st
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# ページ設定
st.set_page_config(page_title="💰 割り勘キャッチャー", page_icon="💸")

def get_sheet():
    creds_dict = json.loads(st.secrets["gcp"]["data"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open_by_key("1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw").worksheet("warikan_db")

# タイトル（絵文字とカスタムCSSで少し可愛く）
st.markdown("<h1 style='text-align: center; color: #ff6b6b;'>💸 割り勘キャッチャー 💸</h1>", unsafe_allow_html=True)

try:
    sheet = get_sheet()
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- 入力画面 ---
st.subheader("📝 支払いを追加")
col1, col2 = st.columns(2)
with col1:
    name = st.text_input("名前")
with col2:
    amount = st.number_input("金額 (円)", min_value=0)

if st.button("🚀 送信して記録！"):
    if name:
        sheet.append_row([name, amount])
        st.balloons() # 可愛い演出
        st.success(f"{name}さんの {amount}円 をキャッチしたよ！")
    else:
        st.warning("名前を入力してね！")

st.divider()

# --- データ管理と削除画面 ---
st.subheader("📊 記録一覧 & 削除")
data = sheet.get_all_records()

if not data:
    st.info("まだ記録はないよ！")
else:
    # データ表示用テーブル
    for i, d in enumerate(data):
        col1, col2, col3 = st.columns([2, 1, 1])
        col1.write(f"👤 {d['名前']}")
        col2.write(f"💰 {d['金額']}円")
        # 削除ボタン（インデックス番号で特定）
        if col3.button("❌ 消す", key=f"del_{i}"):
            sheet.delete_rows(i + 2) # ヘッダー分+1と0始まりのインデックス調整
            st.rerun()

st.divider()

# --- 計算画面 ---
if st.button("🧮 割り勘計算スタート！"):
    total = sum(d['金額'] for d in data)
    avg = total / len(data)
    st.write(f"### 合計金額: {total}円")
    st.write(f"### 1人あたり: {avg:.0f}円")
    for d in data:
        diff = d['金額'] - avg
        if diff < 0:
            st.error(f"😢 {d['名前']}さん：あと {abs(diff):.0f} 円支払う")
        else:
            st.info(f"✨ {d['名前']}さん： {diff:.0f} 円受け取る")
