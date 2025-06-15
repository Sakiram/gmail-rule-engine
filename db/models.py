from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Email:
    id: str
    msg_id: str
    thread_id: str
    subject: Optional[str]
    sender: Optional[str]
    recipient: Optional[str]
    snippet: Optional[str]
    body: Optional[str]
    date_received: datetime
    marked_as: Optional[str]
    msg_moved_to: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
