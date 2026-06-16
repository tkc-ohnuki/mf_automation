import os
import json
from playwright.sync_api import sync_playwright
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# --- 設定項目 ---
MF_ID = os.environ.get("MF_ID")
MF_PW = os.environ.get("MF_PW")
GOOGLE_TOKEN_JSON = os.environ.get("GOOGLE_TOKEN_JSON")
DRIVE_FILE_ID = os.environ.get("DRIVE_FILE_ID")
MF_COOKIES = os.environ.get("MF_COOKIES")

DOWNLOAD_PATH = "資産推移月次.csv"

def download_mf_csv():
    print("🚀 Playwright を起動中...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Cookie復元（ある場合はログインスキップ）
        if MF_COOKIES:
            print("🍪 保存済みCookieを復元中...")
            cookies = json.loads(MF_COOKIES)
            context.add_cookies(cookies)

        page = context.new_page()
        try:
            if MF_COOKIES:
                # Cookieがある場合は直接資産推移ページへ
                print("📊 Cookie復元済み。資産推移ページへ直接ジャンプします...")
                page.goto("https://moneyforward.com/bs/history")
                page.wait_for_load_state("load")
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(3000)
                print(f"現在のURL: {page.url}")

                # セッション切れの場合はログインにフォールバック
                if "sign_in" in page.url or "email_otp" in page.url:
                    print("⚠️ Cookieが無効です。通常ログインにフォールバックします...")
                    _do_login(page)
            else:
                # Cookieがない場合は通常ログイン
                print("🔑 Cookieなし。通常ログインを実行します...")
                page.goto("https://moneyforward.com/users/sign_in")
                page.wait_for_load_state("load")
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)
                _do_login(page)

            print("📥 CSVを直接URLからダウンロードします...")
            with page.expect_download() as download_info:
                page.evaluate("window.location.href = 'https://moneyforward.com/bs/history/csv'")

            download = download_info.value
            download.save_as(DOWNLOAD_PATH)
            print(f"✨ CSVをローカルに保存しました: {DOWNLOAD_PATH}")

            browser.close()
            return True

        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
            print("📄 --- [DEBUG] 落ちた瞬間のHTMLソースを取得します ---")
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


def _do_login(page):
    """メール・パスワードによる通常ログイン処理"""
    # ステップ1: メールアドレス入力
    print("👤 メールアドレスを入力中...")
    email_input = page.locator("input#mfid_user\\[email\\]")
    email_input.wait_for(state="visible", timeout=15000)
    email_input.fill(MF_ID)
    page.wait_for_timeout(500)

    # ステップ2: 次へボタン（パスワード欄を展開）
    print("🔘 次へボタンをクリック（パスワード欄を展開）...")
    page.click("button#submitto")
    page.wait_for_timeout(3000)

    # ステップ3: パスワード入力
    print("🔒 パスワード入力欄の出現を待機中...")
    pw_input = page.locator("input#mfid_user\\[password\\]")
    pw_input.wait_for(state="visible", timeout=15000)

    print("🔒 パスワードを入力中...")
    pw_input.fill(MF_PW)
    page.wait_for_timeout(500)

    # ステップ4: ログイン実行
    print("🔘 ログインボタンをクリック（ログイン実行）...")
    page.click("button#submitto")

    print("⏳ ログイン処理の完了を待機中...")
    page.wait_for_load_state("load")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(8000)
    print(f"🔓 ログイン完了。現在のURL: {page.url}")

    # 資産推移ページへ移動
    print("📊 資産推移ページへ直接ジャンプします...")
    page.goto("https://moneyforward.com/bs/history")
    page.wait_for_load_state("load")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)


def upload_to_google_drive():
    if not os.path.exists(DOWNLOAD_PATH):
        print("❌ アップロード対象のファイルが存在しません。")
        return

    print("🤖 Google Drive API を初期化中...")
    with open("token.json", "w") as f:
        f.write(GOOGLE_TOKEN_JSON)

    scopes = ['https://www.googleapis.com/auth/drive.file']
    creds = Credentials.from_authorized_user_file('token.json', scopes)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    service = build('drive', 'v3', credentials=creds)

    print(f"⬆️ Google Drive (ID: {DRIVE_FILE_ID}) へ上書きアップロード中...")
    media = MediaFileUpload(DOWNLOAD_PATH, mimetype='text/csv', resumable=True)

    file = service.files().update(
        fileId=DRIVE_FILE_ID,
        media_body=media
    ).execute()

    print(f"🎉 アップロード完了！ファイル名: {file.get('name')} (ID: {file.get('id')})")


if __name__ == "__main__":
    if download_mf_csv():
        upload_to_google_drive()
