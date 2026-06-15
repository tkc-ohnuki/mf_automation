import os
import time
from playwright.sync_api import sync_playwright
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# --- 設定項目 ---
# マネーフォワードの認証情報（GitHub Secrets から環境変数経由で取得）
MF_ID = os.environ.get("MF_ID")
MF_PW = os.environ.get("MF_PW")

# Google Drive API 用の認証情報（GitHub Secrets から環境変数経由で取得）
GOOGLE_TOKEN_JSON = os.environ.get("GOOGLE_TOKEN_JSON")
# Google Drive上の上書き対象CSVのファイルID
DRIVE_FILE_ID = os.environ.get("DRIVE_FILE_ID")

DOWNLOAD_PATH = "資産推移月次.csv"

def download_mf_csv():
    print("🚀 Playwright を起動中...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 画面サイズを標準的なデスクトップに固定してレンダリングの崩れを防ぐ
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        try:
            print("🔑 マネーフォワード Web版ログイン画面へ遷移します...")
            page.goto("https://moneyforward.com/users/sign_in")
            page.wait_for_load_state("load")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

            # --- ログイン情報入力（人間模倣タイピングによる完全同期） ---
            print("👤 メールアドレスの入力欄を探しています...")
            email_selector = "input[id='mfid_user[email]'], input[type='email']:not([type='hidden'])"
            page.wait_for_selector(email_selector, state="visible", timeout=15000)

            # 💡 fillを捨て、一度クリックしてフォーカスさせてから、人間のようにタイピングする
            print("👤 メールアドレスをタイピング中...")
            page.locator(email_selector).first.click()
            page.keyboard.type(MF_ID, delay=50) # 1文字ごとに50ミリ秒のディレイを入れるリアルさ
            page.wait_for_timeout(1000)

            print("🔒 パスワードの入力欄を探しています...")
            password_selector = "input[id='mfid_user[password]'], input[type='password']:not([type='hidden'])"
            page.wait_for_selector(password_selector, state="visible", timeout=15000)

            # 💡 パスワードも同様に、クリックしてから物理タイピングをエミュレート
            print("🔒 パスワードをタイピング中...")
            page.locator(password_selector).first.click()
            page.keyboard.type(MF_PW, delay=50)
            page.wait_for_timeout(1000)

            # 💡 完全に文字が認識された状態で、満を持してログインボタンを物理クリック
            print("🔘 ログインボタンをクリックしてサインインを実行します...")
            page.click("button#submitto")

            print("⏳ ログイン処理の完了を待機中...")
            page.wait_for_load_state("load")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(8000) # 認証完了・セッション確立のために長めに8秒ホールド
            print("🔓 ログイン処理フェーズを通過しました")

            # --- 3段階目：資産推移ページへ移動してCSVダウンロード ---
            print("📊 資産推移ページへ直接ジャンプします...")
            page.goto("https://moneyforward.com/bs/history")
            page.wait_for_load_state("load")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)

            print("📥 CSVのダウンロードボタンを探しています...")
            # ボタンが確実に操作可能になるまで明示的に待つ
            csv_btn_selector = "text=CSVダウンロード, a[href*='csv']"
            page.wait_for_selector(csv_btn_selector, state="visible", timeout=15000)

            print("📥 CSVのダウンロードを開始します...")
            with page.expect_download() as download_info:
                page.locator(csv_btn_selector).first.click()

            download = download_info.value
            download.save_as(DOWNLOAD_PATH)
            print(f"✨ CSVをローカルに保存しました: {DOWNLOAD_PATH}")
            browser.close()
            return True

        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
            print("📄 --- [DEBUG] 落ちた瞬間の画面のHTMLソースを取得します ---")
            try:
                print(page.content())
            except Exception as html_err:
                print(f"HTMLの取得に失敗: {html_err}")
            print("📄 --- [DEBUG] HTMLソース出力終了 ---")

            print("📸 エラー時点の画面スクショを 'error.png' として保存します...")
            try:
                page.screenshot(path="error.png", full_page=True)
            except Exception:
                pass

            browser.close()
            return False

def upload_to_google_drive():
    if not os.path.exists(DOWNLOAD_PATH):
        print("❌ アップロード対象のファイルが存在しません。")
        return

    print("🤖 Google Drive API を初期化中...")
    # GitHub Secretsに保存したJSON文字列から認証情報を復元
    with open("token.json", "w") as f:
        f.write(GOOGLE_TOKEN_JSON)

    scopes = ['https://www.googleapis.com/auth/drive.file']
    creds = Credentials.from_authorized_user_file('token.json', scopes)

    # トークンが期限切れの場合は自動更新
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    service = build('drive', 'v3', credentials=creds)

    print(f"⬆️ Google Drive (ID: {DRIVE_FILE_ID}) へ上書きアップロード中...")
    media = MediaFileUpload(DOWNLOAD_PATH, mimetype='text/csv', resumable=True)
    
    # 指定した既存のファイルIDに対して内容のみをアップデート（上書き）
    file = service.files().update(
        fileId=DRIVE_FILE_ID,
        media_body=media
    ).execute()
    
    print(f"🎉 アップロード完了！ファイル名: {file.get('name')} (ID: {file.get('id')})")

if __name__ == "__main__":
    if download_mf_csv():
        upload_to_google_drive()
