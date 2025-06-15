from db.schema import init_db
import os
from dotenv import load_dotenv
from gmail.fetcher import fetch_emails_for_user
import sys

load_dotenv()

def main():
    init_db()

    if len(sys.argv) < 2:
        print("Usage: python main_fetch.py user_email@gmail.com")
        exit(1)

    email = sys.argv[1]
    days = int(os.getenv("days"))

    # Check if optional --days argument is passed
    if "--days" in sys.argv:
        try:
            days_index = sys.argv.index("--days") + 1
            days = int(sys.argv[days_index])
        except (IndexError, ValueError):
            print("Invalid --days argument. Usage: --days <number>")
            exit(1)
    fetch_emails_for_user(email, days=days)

if __name__ == "__main__":
    main()
