from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import json

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

flow = InstalledAppFlow.from_client_secrets_file('config/credentials.json', SCOPES)
creds = flow.run_local_server(port=0)
creds_dict = json.loads(creds.to_json())

with open('config/tokens/token.json', 'w') as token:
    json.dump(creds_dict, token, indent=2)

service = build('gmail', 'v1', credentials=creds)
profile = service.users().getProfile(userId='me').execute()
print(f"Successfully authenticated as: {profile['emailAddress']}")
