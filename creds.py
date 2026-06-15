from google_auth_oauthlib.flow import InstalledAppFlow
import json

flow = InstalledAppFlow.from_client_secrets_file(
    'credentials.json', 
    scopes=['https://www.googleapis.com/auth/drive.file']
)
creds = flow.run_local_server(port=0)

# 文字列としてSecretsに貼るため、中身をプリント
print(creds.to_json())
