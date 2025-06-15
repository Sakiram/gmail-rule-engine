import pytest
from datetime import datetime, timedelta, timezone
from rules.engine import RuleEngine
from db.models import Email


class TestRuleEngine:
    """Test cases for the RuleEngine class"""
    
    def setup_method(self):
        """Setup test data for each test method"""
        self.sample_email = Email(
            id="1",
            msg_id="msg_123",
            thread_id="thread_123",
            subject="Test Invoice Subject",
            sender="user1@example.com",
            recipient="test@example.com",
            snippet="Test snippet",
            body="This is a test email body with invoice details",
            date_received=datetime.now(timezone.utc) - timedelta(hours=12),
            marked_as=None,
            msg_moved_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    def test_rule_engine_initialization(self):
        """Test RuleEngine initialization with different predicates"""
        rules = [{"field": "from", "predicate": "contains", "value": "test"}]
        
        # Test valid predicates
        engine_all = RuleEngine("all", rules)
        assert engine_all.overall_predicate == "all"
        assert engine_all.rules == rules
        
        engine_any = RuleEngine("any", rules)
        assert engine_any.overall_predicate == "any"

    def test_text_predicate_contains(self):
        """Test contains predicate for text fields"""
        rules = [{"field": "from", "predicate": "contains", "value": "user1"}]
        engine = RuleEngine("all", rules)
        
        assert engine.match(self.sample_email) == True
        
        # Test case insensitive
        rules = [{"field": "from", "predicate": "contains", "value": "USER1"}]
        engine = RuleEngine("all", rules)
        assert engine.match(self.sample_email) == True

    def test_text_predicate_not_contains(self):
        """Test not_contains predicate for text fields"""
        rules = [{"field": "from", "predicate": "not_contains", "value": "nonexistent"}]
        engine = RuleEngine("all", rules)
        
        assert engine.match(self.sample_email) == True
        
        rules = [{"field": "from", "predicate": "not_contains", "value": "user1"}]
        engine = RuleEngine("all", rules)
        assert engine.match(self.sample_email) == False

    def test_text_predicate_equals(self):
        """Test equals predicate for text fields"""
        rules = [{"field": "from", "predicate": "equals", "value": "user1@example.com"}]
        engine = RuleEngine("all", rules)
        
        assert engine.match(self.sample_email) == True
        
        rules = [{"field": "from", "predicate": "equals", "value": "different@example.com"}]
        engine = RuleEngine("all", rules)
        assert engine.match(self.sample_email) == False

    def test_text_predicate_not_equals(self):
        """Test not_equals predicate for text fields"""
        rules = [{"field": "from", "predicate": "not_equals", "value": "different@example.com"}]
        engine = RuleEngine("all", rules)
        
        assert engine.match(self.sample_email) == True
        
        rules = [{"field": "from", "predicate": "not_equals", "value": "user1@example.com"}]
        engine = RuleEngine("all", rules)
        assert engine.match(self.sample_email) == False

    def test_date_predicate_less_than_days(self):
        """Test less_than_days predicate"""
        rules = [{"field": "date_received", "predicate": "less_than_days", "value": 1}]
        engine = RuleEngine("all", rules)
        
        # Email is 12 hours old, should match less_than_days: 1
        assert engine.match(self.sample_email) == True
        
        # Test with older email
        old_email = Email(
            id="2", msg_id="msg_456", thread_id="thread_456",
            subject="Old email", sender="test@example.com", recipient="user@example.com",
            snippet="", body="", 
            date_received=datetime.now(timezone.utc) - timedelta(days=2),
            marked_as=None, msg_moved_to=None, created_at=None, updated_at=None
        )
        
        assert engine.match(old_email) == False

    def test_date_predicate_greater_than_days(self):
        """Test greater_than_days predicate"""
        rules = [{"field": "date_received", "predicate": "greater_than_days", "value": 1}]
        engine = RuleEngine("all", rules)
        
        # Email is 12 hours old, should not match greater_than_days: 1
        assert engine.match(self.sample_email) == False
        
        # Test with older email
        old_email = Email(
            id="2", msg_id="msg_456", thread_id="thread_456",
            subject="Old email", sender="test@example.com", recipient="user@example.com",
            snippet="", body="", 
            date_received=datetime.now(timezone.utc) - timedelta(days=2),
            marked_as=None, msg_moved_to=None, created_at=None, updated_at=None
        )
        
        assert engine.match(old_email) == True

    def test_multiple_rules_all_predicate(self):
        """Test multiple rules with 'all' predicate"""
        rules = [
            {"field": "from", "predicate": "contains", "value": "user1"},
            {"field": "to", "predicate": "contains", "value": "test"},
            {"field": "date_received", "predicate": "less_than_days", "value": 1}
        ]
        engine = RuleEngine("all", rules)
        
        # All rules should match
        assert engine.match(self.sample_email) == True
        
        # Change one rule to not match
        rules[0]["value"] = "nonexistent"
        engine = RuleEngine("all", rules)
        assert engine.match(self.sample_email) == False

    def test_multiple_rules_any_predicate(self):
        """Test multiple rules with 'any' predicate"""
        rules = [
            {"field": "from", "predicate": "contains", "value": "user1"},
            {"field": "to", "predicate": "contains", "value": "nonexistent"},
            {"field": "subject", "predicate": "contains", "value": "nonexistent"}
        ]
        engine = RuleEngine("any", rules)
        
        # Only first rule matches, should return True
        assert engine.match(self.sample_email) == True
        
        # Make all rules not match
        rules = [
            {"field": "from", "predicate": "contains", "value": "nonexistent1"},
            {"field": "to", "predicate": "contains", "value": "nonexistent2"},
            {"field": "subject", "predicate": "contains", "value": "nonexistent3"}
        ]
        engine = RuleEngine("any", rules)
        assert engine.match(self.sample_email) == False

    def test_field_mapping(self):
        """Test field mapping from rule field names to email attributes"""
        test_cases = [
            ("from", "sender", "user1@example.com"),
            ("to", "recipient", "test@example.com"),
            ("subject", "subject", "Test Invoice Subject"),
            ("message", "body", "This is a test email body with invoice details")
        ]
        
        for rule_field, _, expected_value in test_cases:
            rules = [{"field": rule_field, "predicate": "contains", "value": expected_value[:5]}]
            engine = RuleEngine("all", rules)
            assert engine.match(self.sample_email) == True

    def test_none_values_handling(self):
        """Test handling of None values in email fields"""
        email_with_none = Email(
            id="3", msg_id="msg_789", thread_id="thread_789",
            subject=None, sender=None, recipient=None,
            snippet=None, body=None, 
            date_received=datetime.now(timezone.utc),
            marked_as=None, msg_moved_to=None, created_at=None, updated_at=None
        )
        
        rules = [{"field": "from", "predicate": "contains", "value": "test"}]
        engine = RuleEngine("all", rules)
        
        # Should return False when field is None
        assert engine.match(email_with_none) == False

    def test_invalid_predicate_raises_exception(self):
        """Test that invalid predicates raise exceptions"""
        rules = [{"field": "from", "predicate": "invalid_predicate", "value": "test"}]
        engine = RuleEngine("all", rules)
        
        with pytest.raises(Exception, match="Unsupported text predicate"):
            engine.match(self.sample_email)

    def test_invalid_field_raises_exception(self):
        """Test that invalid fields raise exceptions"""
        rules = [{"field": "invalid_field", "predicate": "contains", "value": "test"}]
        engine = RuleEngine("all", rules)
        
        with pytest.raises(Exception, match="Unsupported field in rule"):
            engine.match(self.sample_email)

    def test_invalid_overall_predicate_raises_exception(self):
        """Test that invalid overall predicates raise exceptions"""
        rules = [{"field": "from", "predicate": "contains", "value": "test"}]
        engine = RuleEngine("invalid", rules)
        
        with pytest.raises(Exception, match="Invalid overall predicate"):
            engine.match(self.sample_email)

    def test_date_predicate_with_months(self):
        """Test date predicates with months"""
        rules = [{"field": "date_received", "predicate": "less_than_months", "value": 1}]
        engine = RuleEngine("all", rules)
        
        # Email is 12 hours old, should match less_than_months: 1
        assert engine.match(self.sample_email) == True
        
        # Test with very old email
        very_old_email = Email(
            id="4", msg_id="msg_old", thread_id="thread_old",
            subject="Very old email", sender="test@example.com", recipient="user@example.com",
            snippet="", body="", 
            date_received=datetime.now(timezone.utc) - timedelta(days=60),
            marked_as=None, msg_moved_to=None, created_at=None, updated_at=None
        )
        
        assert engine.match(very_old_email) == False

    def test_date_string_conversion(self):
        """Test date conversion from string format"""
        # Create email with string date that needs conversion
        email_str_date = Email(
            id="5", msg_id="msg_str", thread_id="thread_str",
            subject="String date email", sender="test@example.com", recipient="user@example.com",
            snippet="", body="", 
            date_received="2024-01-01T12:00:00+00:00",  # String format
            marked_as=None, msg_moved_to=None, created_at=None, updated_at=None
        )
        
        rules = [{"field": "date_received", "predicate": "greater_than_days", "value": 1}]
        engine = RuleEngine("all", rules)
        
        # Should handle string conversion and match (since it's an old date)
        assert engine.match(email_str_date) == True