import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def get_sheet():
    # Secretsから個別に読み込み
    creds_dict = {
        "type": st.secrets["gcp"]["type"].strip(),
        "project_id": st.secrets["gcp"]["project_id"].strip(),
        "private_key_id": st.secrets["gcp"]["private_key_id"].strip(),
        "private_key": st.secrets["gcp"]["private_key"].strip(),
        "client_email": st.secrets["gcp"]["client_email"].strip(),
        "client_id": st.secrets["gcp"]["client_id"].strip(),
        "auth_uri": st.secrets["gcp"]["auth_uri"].strip(),
        "token_uri": st.secrets["gcp"]["token_uri"].strip(),
        "auth_provider_x509_cert_url": st.secrets["gcp"]["auth_provider_x509_cert_url"].strip(),
        "client_x509_cert_url": st.secrets["gcp"]["client_x509_cert_url"].strip(),
    }
    
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets"
    ]
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # ID指定
    spreadsheet_key = "1FMOcjANKIfUgtzfBNCRgk1MAi-QxrvZb-yA_xiOy_Hw"
    sh = client.open_by_key(spreadsheet_key)
    
    # ★重要：ここを実際のシート名に合わせてください
    return sh.worksheet("warikan_db")

st.title("💰 みんなの割り勘アプリ")

try:
    sheet = get_sheet()
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# 以降は変更なし
name = st.text_input("名前")
amount = st.number_input("金額", min_value=0)

if st.button("送信"):
    if name:
        sheet.append_row([name, amount])
        st.success(f"{name}さんの {amount}円 を記録しました！")
    else:
        st.warning("名前を入力してください。")

if st.button("計算する"):
    data = sheet.get_all_records()
    if not data:
        st.write("まだデータがありません。")
    else:
        st.table(data)
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
