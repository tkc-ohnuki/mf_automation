# マネーフォワードME CSV自動同期ツール (GitHub Actions + Playwright)

毎日自動でマネーフォワードから「資産推移月次.csv」をダウンロードし、Googleドライブ上の既存CSVファイルを上書き更新する仕組みです。

## 📁 構成ファイル
- `script.py`: Playwrightによる自動操作とGoogle Drive APIによる上書きアップロードを行うコアスクリプト。
- `.github/workflows/workflow.yml`: 毎日深夜に自動実行するためのGitHub Actions設定ファイル。

## 🛠️ 事前準備・セッティング手順

### ステップ 1: Google Drive の「ファイルID」を取得する
1. Googleドライブを開き、上書き対象にしたい既存の「資産推移月次.csv」を右クリック ➔ 「リンクをコピー」します。
2. コピーしたURL内の `https://drive.google.com/file/d/【ここの英数字】/view?...` の【ここの英数字】の部分が **ファイルID** です。これをメモしておきます。

### ステップ 2: Google Drive API の認証トークン（JSON）を作る
GitHub Actionsからご自身のGoogleドライブにアクセスするための「鍵（リフレッシュトークン付きのToken）」をローカル環境で1度だけ生成します。

1. **Google Cloud Console** でプロジェクトを作成し、**Google Drive API** を有効化します。
2. 「OAuth 同意画面」を「テスト」で作成し、ご自身のGoogleアカウントをテストユーザーに追加します。
3. 「認証情報」から **OAuth 2.0 クライアント ID**（デスクトップアプリ用）を作成し、`credentials.json` という名前でダウンロードします。
4. ローカルPCで以下の簡単なPythonコードを実行し、ブラウザで認証を通します。
