from googleapiclient.discovery import build
from datetime import datetime, timedelta, timezone
from gmail.auth import authenticate_user
from gmail.parser import extract_email_data
from db.storage import save_email

def fetch_emails_for_user(user_email: str, days: int = 30):
    """
    Authenticate the user and fetch emails from their Gmail inbox.
    """
    creds = authenticate_user(user_email)
    service = build('gmail', 'v1', credentials=creds)

    # Compute UNIX timestamp for cutoff date
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)    
    cutoff_unix = int(cutoff_date.timestamp())
    query = f"after:{cutoff_unix}"

    print(f"Fetching emails back from {days} days for user email: {user_email}...")

    all_messages = []
    next_page_token = None

    while True:
        response = service.users().messages().list(
            userId='me',
            labelIds=['INBOX'],
            q=query,
            pageToken=next_page_token
        ).execute()

        messages = response.get('messages', [])
        all_messages.extend(messages)

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    print(f"Found {len(all_messages)} messages")

    for message in all_messages:
        msg_detail = service.users().messages().get(
            userId='me',
            id=message['id'],
            format='full'
        ).execute()

        email = extract_email_data(msg_detail)
        if not email:
            print(f"Skipped message ID {message['id']} - extract_email_data returned None")
            continue
        save_email(email)

    print("Emails fetched and saved.")
