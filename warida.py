import streamlit as st
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# 1. Googleスプレッドシートへの接続設定（Secretsを使用）
def get_sheet():
    # StreamlitのSecrets設定から JSON文字列を読み込み、辞書に変換
    creds_dict = json.loads(st.secrets["gcp_service_account"])
    
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets"
    ]
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # ★あなたのスプレッドシートのIDをここにコピペしてください
    spreadsheet_key = "あなたのスプレッドシートIDをここに貼り付け"
    
    return client.open_by_key(spreadsheet_key).sheet1

# アプリのタイトル
st.title("💰 みんなの割り勘アプリ")

# シートの取得
try:
    sheet = get_sheet()
except Exception as e:
    st.error(f"接続エラーが発生しました: {e}")
    st.stop()

# 2. 入力フォーム
name = st.text_input("名前")
amount = st.number_input("支払った金額", min_value=0)

if st.button("送信"):
    if name:
        sheet.append_row([name, amount])
        st.success(f"{name}さんの {amount}円 を記録しました！")
    else:
        st.warning("名前を入力してください。")

# 3. データの表示と計算
if st.button("計算する"):
    data = sheet.get_all_records()
    
    if not data:
        st.write("まだデータがありません。")
    else:
        st.write("### 現在の入力状況")
        st.table(data)
        
        # 計算ロジック
        total = sum(d['金額'] for d in data)
        avg = total / len(data)
        
        st.write(f"---")
        st.write(f"合計金額: {total}円 / 1人あたり: {avg:.0f}円")
        
        for d in data:
            diff = d['金額'] - avg
            if diff < 0:
                st.error(f"{d['名前']}さん：あと {abs(diff):.0f} 円支払う")
            else:
                st.info(f"{d['名前']}さん： {diff:.0f} 円受け取る")
