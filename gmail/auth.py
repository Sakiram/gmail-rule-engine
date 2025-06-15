import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
TOKEN_DIR = 'config/tokens'
CREDENTIALS_PATH = 'config/credentials.json'

def authenticate_user(email: str):
    os.makedirs(TOKEN_DIR, exist_ok=True)
    token_path = os.path.join(TOKEN_DIR, f"{email}.json")

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return creds

def get_gmail_service(email: str):
    creds = authenticate_user(email)
    return build('gmail', 'v1', credentials=creds)
