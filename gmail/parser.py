import base64
import email
from datetime import datetime, timezone
from db.models import Email
import re

def extract_email_address(header_value: str) -> str:
    """
    Extracts email address from headers like:
    - "Sakir Ram <sakiramganesan@gmail.com>" => "sakiramganesan@gmail.com"
    - "sakiramganesan@gmail.com" => "sakiramganesan@gmail.com"
    """
    match = re.search(r'<(.+?)>', header_value)
    if match:
        return match.group(1).strip()
    return header_value.strip()

def get_header(headers, name):
    for header in headers:
        if header['name'].lower() == name.lower():
            return header['value']
    return ''


def extract_email_data(msg_detail: dict) -> Email:
    headers = msg_detail['payload'].get('headers', [])
    payload = msg_detail['payload']

    msg_id = msg_detail['id']
    thread_id = msg_detail.get('threadId', '')
    subject = get_header(headers, 'Subject')
    sender_raw = get_header(headers, 'From')
    sender = extract_email_address(sender_raw)
    recipient_raw = get_header(headers, 'To')
    recipient = extract_email_address(recipient_raw)
    snippet = msg_detail.get('snippet', '')

    date_str = get_header(headers, 'Date')
    try:
        date_received = email.utils.parsedate_to_datetime(date_str)
    except Exception:
        date_received = datetime.now(timezone.utc)

    # Extract the plain text body
    body = extract_body(payload)

    return Email(
        id=None,
        msg_id=msg_id,
        thread_id=thread_id,
        subject=subject,
        sender=sender,
        recipient=recipient,
        snippet=snippet,
        body=body,
        date_received=date_received,
        marked_as=None,
        msg_moved_to=None,
        created_at=None,
        updated_at=None
    )


def extract_body(payload):
    """
    Extract plain text body from message payload.
    """
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                return decode_base64(part['body'].get('data', ''))
            elif part['mimeType'] == 'multipart/alternative':
                return extract_body(part)
    else:
        return decode_base64(payload.get('body', {}).get('data', ''))

    return ''


def decode_base64(data):
    if not data:
        return ''
    decoded_bytes = base64.urlsafe_b64decode(data.encode('UTF-8'))
    return decoded_bytes.decode('UTF-8', errors='ignore')
