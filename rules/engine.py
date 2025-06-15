from datetime import datetime, timedelta, timezone
import re

class RuleEngine:
    def __init__(self, overall_predicate, rules):
        self.overall_predicate = overall_predicate.lower()
        self.rules = rules

    def match(self, email):
        results = [self._match_single_rule(rule, email) for rule in self.rules]
        if self.overall_predicate == "all":
            return all(results)
        elif self.overall_predicate == "any":
            return any(results)
        else:
            raise Exception(f"Invalid overall predicate: {self.overall_predicate}")

    def _match_single_rule(self, rule, email):
        field = rule.get("field", "").lower()
        predicate = rule.get("predicate", "").lower()
        value = rule.get("value", "")

        field_map = {
            "from": "sender",
            "to": "recipient",
            "subject": "subject",
            "message": "body",
            "date_received": "date_received"
        }

        actual_field = field_map.get(field)
        if not actual_field:
            raise Exception(f"Unsupported field in rule: {field}")

        email_value = getattr(email, actual_field, None)

        if field in ["from", "to", "subject", "message"]:
            if email_value is None:
                return False
            return self._match_text_predicate(str(email_value), predicate, value)

        elif field == "date_received":
            return self._match_date_predicate(email.date_received, predicate, int(value))

        else:
            raise Exception(f"Unsupported field: {field}")

    def _match_text_predicate(self, text, predicate, value):
        if predicate == "contains":
            return value.lower() in text.lower()
        elif predicate == "not_contains":
            return value.lower() not in text.lower()
        elif predicate == "equals":
            return text.lower() == value.lower()
        elif predicate == "not_equals":
            return text.lower() != value.lower()
        else:
            raise Exception(f"Unsupported text predicate: {predicate}")

    def _match_date_predicate(self, date_received, predicate, offset):
        # Ensure date_received is a datetime object
        if not isinstance(date_received, datetime):
            try:
                date_received = datetime.fromisoformat(str(date_received))
            except Exception:
                date_received = datetime.now(timezone.utc)  # Fallback

        now = datetime.now(tz=date_received.tzinfo)
        if "days" in predicate:
            delta = timedelta(days=offset)
        elif "months" in predicate:
            delta = timedelta(days=30 * offset)
        else:
            raise Exception(f"Invalid date predicate: {predicate}")

        if predicate.startswith("less_than"):
            return (now - date_received) < delta
        elif predicate.startswith("greater_than"):
            return (now - date_received) > delta
        else:
            raise Exception(f"Unsupported date predicate: {predicate}")
