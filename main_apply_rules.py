import os
import sys
import json
import logging
from db.storage import get_all_emails
from db.models import Email
from gmail.auth import get_gmail_service
from actions import gmail_actions
from rules.engine import RuleEngine

# logging Setup
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
    
    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list):
        raise ValueError("rules.json must contain a list of rule sets.")

    for rule_set in data:
        overall = rule_set.get("predicate", "").lower()
        rules = rule_set.get("rules", [])
        actions = rule_set.get("actions", [])
        if overall not in ["all", "any"]:
            raise ValueError("Each rule set must have 'predicate' as 'all' or 'any'")
        if not rules:
            raise ValueError("Each rule set must include at least one rule.")
        if not actions:
            raise ValueError("Each rule set must include at least one action.")
        print(f"Loaded rules: {rules}")

    return data

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
        rule_sets = load_rules()
        emails = get_all_emails()
        service = get_gmail_service(user_email)

        for email in emails:
            for rule_set in rule_sets:
                try:
                    engine = RuleEngine(rule_set["predicate"], rule_set["rules"])
                    if engine.match(email):
                        print(f"Matched rule set for email ID {email.id}")
                        apply_actions(service, user_email, email, rule_set["actions"])
                except Exception as e:
                    logging.error(f"Error applying rule set to email ID {email.id}: {e}")
                    print(f"Error applying rules for email ID {email.id}: {e}")

    except Exception as e:
        logging.critical(f"Critical failure: {e}")
        print(f"Fatal error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python main_apply_rules.py <user_email>")
    else:
        main(sys.argv[1])
