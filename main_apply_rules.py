import os
import sys
import json
import logging
from db.storage import get_all_emails
from db.models import Email
from gmail.auth import get_gmail_service
from actions import gmail_actions
from rules.engine import RuleEngine

# Setup logging
logging.basicConfig(
    filename="logs/rule_application.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

RULES_FILE = "rules/rules.json"

def load_rules():
    """Load and validate rule config."""
    if not os.path.exists(RULES_FILE):
        raise FileNotFoundError(f"Rules file not found at: {RULES_FILE}")

    with open(RULES_FILE, "r") as file:
        data = json.load(file)

    overall = data.get("predicate", "").lower()
    rules = data.get("rules", [])
    actions = data.get("actions", [])

    if overall not in ["all", "any"]:
        raise ValueError("Predicate must be either 'all' or 'any'.")
    if not rules:
        raise ValueError("At least one rule must be defined.")
    if not actions:
        raise ValueError("At least one action must be defined.")
    print(f"Loaded rules: {rules}")
    return overall, rules, actions

def apply_actions(service, user_id, email_record: Email, actions):
    """Apply configured actions to matched email."""
    for action in actions:
        action = action.strip()

        try:
            if action == "mark_as_read":
                gmail_actions.mark_as_read(service, email_record.msg_id, user_id, email_record)

            elif action == "mark_as_unread":
                gmail_actions.mark_as_unread(service, email_record.msg_id, user_id, email_record)

            elif action.startswith("move_to_label:"):
                label_name = action.split(":", 1)[1].strip()
                gmail_actions.move_to_label(service, email_record.msg_id, user_id, label_name, email_record)

            else:
                raise ValueError(f"Unsupported action: {action}")

            logging.info(f"Applied '{action}' to email ID: {email_record.id}")

        except Exception as e:
            logging.error(f"Failed action '{action}' on email ID {email_record.id}: {e}")
            raise Exception

def main(user_email):
    """Main entry point to evaluate and apply rules."""
    try:
        overall, rules, actions = load_rules()
        engine = RuleEngine(overall, rules)
        emails = get_all_emails()
        service = get_gmail_service(user_email)

        for email in emails:
            try:
                if engine.match(email):
                    print(f"Matched rules for email ID {email.id}")
                    apply_actions(service, user_email, email, actions)
                    logging.info(f"Email ID {email.id} matched rules. Actions applied.")
                # else:
                #     print(f"No match for email ID {email.id}")
            except Exception as e:
                logging.error(f"Error processing email ID {email.id}: {e}")
                print(f"Error applying rules for email ID {email.id}: {e}")

    except Exception as e:
        logging.critical(f"Critical failure: {e}")
        print(f"Fatal error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python main_apply_rules.py <user_email>")
    else:
        main(sys.argv[1])
