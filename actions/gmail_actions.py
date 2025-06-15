from googleapiclient.discovery import build
from db.storage import update_email_status
from datetime import datetime

_label_cache = {}

def _get_label_id(service, user_id, label_name):
    key = f"{user_id}:{label_name.lower()}"
    if key in _label_cache:
        return _label_cache[key]

    labels = service.users().labels().list(userId=user_id).execute().get('labels', [])
    label_dict = {label["name"].lower(): label["id"] for label in labels}

    if label_name.lower() not in label_dict:
        print(f"Label '{label_name}' is not a valid Gmail label.")
        raise Exception(f"Label '{label_name}' is not a valid Gmail label.")

    label_id = label_dict[label_name.lower()]
    _label_cache[key] = label_id
    return label_id

def mark_as_read(service, msg_id, user_id, email_record):
    try:
        service.users().messages().modify(
            userId=user_id,
            id=msg_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        update_email_status(email_record.id, marked_as="read")
    except Exception as e:
        raise Exception(f"Failed to mark as read: {e}")

def mark_as_unread(service, msg_id, user_id, email_record):
    try:
        service.users().messages().modify(
            userId=user_id,
            id=msg_id,
            body={'addLabelIds': ['UNREAD']}
        ).execute()
        update_email_status(email_record.id, marked_as="unread")
    except Exception as e:
        raise Exception(f"Failed to mark as unread: {e}")

def move_to_label(service, msg_id, user_id, label_name, email_record):
    try:
        label_id = _get_label_id(service, user_id, label_name)
        # labels = service.users().labels().list(userId=user_id).execute().get('labels', [])
        # label_dict = {label['name'].lower(): label['id'] for label in labels}

        # label_key = label_name.lower()
        # print(label_key)
        # if label_key not in label_dict:
        #     print(f"Label '{label_name}' is not a valid Gmail label.")
        #     raise Exception(f"Label '{label_name}' is not a valid Gmail label.")

        # label_id = label_dict[label_key]

        # if not label_id:
        #     raise Exception(f"Label '{label_name}' not found in Gmail account.")

        service.users().messages().modify(
            userId=user_id,
            id=msg_id,
            body={'addLabelIds': [label_id]}
        ).execute()
        update_email_status(email_record.id, msg_moved_to=label_name)
    except Exception as e:
        raise Exception(f"Failed to move message to label '{label_name}': {e}")
