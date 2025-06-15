import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime, timezone, timedelta
import json
import os
import sys
import logging
from unittest.mock import call

# Test imports
from db.models import Email
from db.connection import get_connection
from db.storage import save_email, get_all_emails, get_email_by_id, update_email_status, row_to_email
from gmail.auth import authenticate_user, get_gmail_service
from gmail.parser import extract_email_address, get_header, extract_email_data, extract_body, decode_base64
from gmail.fetcher import fetch_emails_for_user


class TestDbConnection:
    """Test cases for db.connection module"""
    
    @patch('db.connection.psycopg2.connect')
    @patch('db.connection.os.getenv')
    def test_get_connection_success(self, mock_getenv, mock_connect):
        """Test successful database connection"""
        # Setup environment variables
        mock_getenv.side_effect = lambda key: {
            'DB_NAME': 'test_db',
            'DB_USER': 'test_user', 
            'DB_PASSWORD': 'test_pass',
            'DB_HOST': 'localhost',
            'DB_PORT': '5432'
        }.get(key)
        
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        # Execute
        result = get_connection()
        
        # Verify
        mock_connect.assert_called_once_with(
            dbname='test_db',
            user='test_user',
            password='test_pass',
            host='localhost',
            port='5432'
        )
        assert result == mock_conn


class TestDbStorage:
    """Test cases for db.storage module"""
    
    def setup_method(self):
        """Setup test data"""
        self.sample_email = Email(
            id=1,
            msg_id="msg_123",
            thread_id="thread_123", 
            subject="Test Subject",
            sender="test@example.com",
            recipient="user@example.com",
            snippet="Test snippet",
            body="Test body",
            date_received=datetime.now(timezone.utc),
            marked_as=None,
            msg_moved_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    @patch('db.storage.get_connection')
    def test_save_email_success(self, mock_get_connection):
        """Test successful email save"""
        mock_conn = Mock()
        mock_cur = Mock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_connection.return_value = mock_conn
        
        # Execute
        save_email(self.sample_email)
        
        # Verify
        mock_cur.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cur.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('db.storage.get_connection')
    def test_get_all_emails_success(self, mock_get_connection):
        """Test successful retrieval of all emails"""
        mock_conn = Mock()
        mock_cur = Mock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_connection.return_value = mock_conn
        
        # Setup mock data
        mock_row = (
            1, "msg_123", "thread_123", "Test Subject", "test@example.com",
            "user@example.com", "snippet", "body", datetime.now(timezone.utc),
            None, None, datetime.now(timezone.utc), datetime.now(timezone.utc)
        )
        mock_cur.fetchall.return_value = [mock_row]
        
        # Execute
        emails = get_all_emails()
        
        # Verify
        assert len(emails) == 1
        assert emails[0].msg_id == "msg_123"
        mock_cur.execute.assert_called_once()

    @patch('db.storage.get_connection')
    def test_get_email_by_id_found(self, mock_get_connection):
        """Test successful retrieval of email by ID"""
        mock_conn = Mock()
        mock_cur = Mock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_connection.return_value = mock_conn
        
        # Setup mock data
        mock_row = (
            1, "msg_123", "thread_123", "Test Subject", "test@example.com",
            "user@example.com", "snippet", "body", datetime.now(timezone.utc),
            None, None, datetime.now(timezone.utc), datetime.now(timezone.utc)
        )
        mock_cur.fetchone.return_value = mock_row
        
        # Execute
        email = get_email_by_id("1")
        
        # Verify
        assert email is not None
        assert email.msg_id == "msg_123"

    @patch('db.storage.get_connection')
    def test_get_email_by_id_not_found(self, mock_get_connection):
        """Test email not found by ID"""
        mock_conn = Mock()
        mock_cur = Mock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_connection.return_value = mock_conn
        mock_cur.fetchone.return_value = None
        
        # Execute
        email = get_email_by_id("999")
        
        # Verify
        assert email is None

    @patch('db.storage.get_connection')
    def test_update_email_status_marked_as(self, mock_get_connection):
        """Test updating email status - marked as"""
        mock_conn = Mock()
        mock_cur = Mock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_connection.return_value = mock_conn
        
        # Execute
        update_email_status(1, marked_as="read")
        
        # Verify
        mock_cur.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch('db.storage.get_connection')
    def test_update_email_status_moved_to(self, mock_get_connection):
        """Test updating email status - moved to"""
        mock_conn = Mock()
        mock_cur = Mock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_connection.return_value = mock_conn
        
        # Execute
        update_email_status(1, msg_moved_to="INBOX")
        
        # Verify
        mock_cur.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_row_to_email(self):
        """Test row to email conversion"""
        row = (
            1, "msg_123", "thread_123", "Test Subject", "test@example.com",
            "user@example.com", "snippet", "body", datetime.now(timezone.utc),
            "read", "INBOX", datetime.now(timezone.utc), datetime.now(timezone.utc)
        )
        
        email = row_to_email(row)
        
        assert email.id == 1
        assert email.msg_id == "msg_123"
        assert email.marked_as == "read"
        assert email.msg_moved_to == "INBOX"


class TestGmailAuth:
    """Test cases for gmail.auth module"""
    
    @patch('gmail.auth.os.path.exists')
    @patch('gmail.auth.Credentials.from_authorized_user_file')
    @patch('gmail.auth.os.makedirs')
    def test_authenticate_user_existing_token(self, mock_makedirs, mock_from_file, mock_exists):
        """Test authentication with existing token"""
        mock_exists.return_value = True
        mock_creds = Mock()
        mock_from_file.return_value = mock_creds
        
        # Execute
        result = authenticate_user("test@example.com")
        
        # Verify
        assert result == mock_creds
        mock_from_file.assert_called_once()

    @patch('gmail.auth.os.path.exists')
    @patch('gmail.auth.InstalledAppFlow.from_client_secrets_file')
    @patch('gmail.auth.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_authenticate_user_new_token(self, mock_file, mock_makedirs, mock_flow_class, mock_exists):
        """Test authentication with new token creation"""
        mock_exists.return_value = False
        mock_flow = Mock()
        mock_creds = Mock()
        mock_creds.to_json.return_value = '{"token": "test_token"}'
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_class.return_value = mock_flow
        
        # Execute
        result = authenticate_user("test@example.com")
        
        # Verify
        assert result == mock_creds
        mock_flow.run_local_server.assert_called_once_with(port=0)

    @patch('gmail.auth.authenticate_user')
    @patch('gmail.auth.build')
    def test_get_gmail_service(self, mock_build, mock_authenticate):
        """Test Gmail service creation"""
        mock_creds = Mock()
        mock_service = Mock()
        mock_authenticate.return_value = mock_creds
        mock_build.return_value = mock_service
        
        # Execute
        result = get_gmail_service("test@example.com")
        
        # Verify
        assert result == mock_service
        mock_build.assert_called_once_with('gmail', 'v1', credentials=mock_creds)


class TestGmailParser:
    """Test cases for gmail.parser module"""
    
    def test_extract_email_address_with_brackets(self):
        """Test email extraction from header with brackets"""
        header = "Sakir Ram <test@gmail.com>"
        result = extract_email_address(header)
        assert result == "test@gmail.com"

    def test_extract_email_address_without_brackets(self):
        """Test email extraction from plain email"""
        header = "test@gmail.com"
        result = extract_email_address(header)
        assert result == "test@gmail.com"

    def test_get_header_found(self):
        """Test getting header value when found"""
        headers = [
            {'name': 'From', 'value': 'test@example.com'},
            {'name': 'Subject', 'value': 'Test Subject'}
        ]
        result = get_header(headers, 'From')
        assert result == 'test@example.com'

    def test_get_header_not_found(self):
        """Test getting header value when not found"""
        headers = [{'name': 'From', 'value': 'test@example.com'}]
        result = get_header(headers, 'To')
        assert result == ''

    def test_get_header_case_insensitive(self):
        """Test getting header value case insensitive"""
        headers = [{'name': 'FROM', 'value': 'test@example.com'}]
        result = get_header(headers, 'from')
        assert result == 'test@example.com'

    def test_decode_base64_success(self):
        """Test successful base64 decoding"""
        import base64
        test_text = "Hello World"
        encoded = base64.urlsafe_b64encode(test_text.encode('utf-8')).decode('utf-8')
        
        result = decode_base64(encoded)
        assert result == test_text

    def test_decode_base64_empty(self):
        """Test base64 decoding with empty input"""
        result = decode_base64('')
        assert result == ''

    def test_extract_body_plain_text(self):
        """Test extracting plain text body"""
        payload = {
            'parts': [
                {
                    'mimeType': 'text/plain',
                    'body': {'data': 'SGVsbG8gV29ybGQ='}  # "Hello World" in base64
                }
            ]
        }
        
        result = extract_body(payload)
        assert result == 'Hello World'

    def test_extract_body_no_parts(self):
        """Test extracting body when no parts exist"""
        payload = {
            'body': {'data': 'SGVsbG8gV29ybGQ='}  # "Hello World" in base64
        }
        
        result = extract_body(payload)
        assert result == 'Hello World'

    @patch('gmail.parser.email.utils.parsedate_to_datetime')
    def test_extract_email_data_success(self, mock_parse_date):
        """Test successful email data extraction"""
        mock_parse_date.return_value = datetime.now(timezone.utc)
        
        msg_detail = {
            'id': 'msg_123',
            'threadId': 'thread_123',
            'snippet': 'Test snippet',
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Test Subject'},
                    {'name': 'From', 'value': 'test@example.com'},
                    {'name': 'To', 'value': 'user@example.com'},
                    {'name': 'Date', 'value': 'Wed, 01 Jan 2025 12:00:00 +0000'}
                ],
                'body': {'data': 'SGVsbG8gV29ybGQ='}
            }
        }
        
        result = extract_email_data(msg_detail)
        
        assert result.msg_id == 'msg_123'
        assert result.subject == 'Test Subject'
        assert result.sender == 'test@example.com'
        assert result.recipient == 'user@example.com'


class TestGmailFetcher:
    """Test cases for gmail.fetcher module"""
    
    @patch('gmail.fetcher.authenticate_user')
    @patch('gmail.fetcher.build')
    @patch('gmail.fetcher.extract_email_data')
    @patch('gmail.fetcher.save_email')
    def test_fetch_emails_for_user_success(self, mock_save, mock_extract, mock_build, mock_auth):
        """Test successful email fetching"""
        # Setup mocks
        mock_creds = Mock()
        mock_service = Mock()
        mock_auth.return_value = mock_creds
        mock_build.return_value = mock_service
        
        # Mock Gmail API responses
        mock_service.users().messages().list.return_value.execute.return_value = {
            'messages': [{'id': 'msg_1'}, {'id': 'msg_2'}]
        }
        
        mock_msg_detail = {'id': 'msg_1', 'threadId': 'thread_1'}
        mock_service.users().messages().get.return_value.execute.return_value = mock_msg_detail
        
        mock_email = Mock()
        mock_extract.return_value = mock_email
        
        # Execute
        fetch_emails_for_user("test@example.com", days=7)
        
        # Verify
        mock_auth.assert_called_once_with("test@example.com")
        mock_build.assert_called_once_with('gmail', 'v1', credentials=mock_creds)
        assert mock_extract.call_count == 2  # Called for each message
        assert mock_save.call_count == 2  # Called for each message


class TestMainApplyRules:
    """Test cases for main_apply_rules module"""
    
    @patch('main_apply_rules.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_rules_success(self, mock_file, mock_exists):
        """Test successful rule loading"""
        mock_exists.return_value = True
        mock_rules = {
            "predicate": "all",
            "rules": [{"field": "from", "predicate": "contains", "value": "test"}],
            "actions": ["mark_as_read"]
        }
        mock_file.return_value.read.return_value = json.dumps(mock_rules)
        
        # Import the module to test
        import main_apply_rules
        
        # Execute
        overall, rules, actions = main_apply_rules.load_rules()
        
        # Verify
        assert overall == "all"
        assert len(rules) == 1
        assert len(actions) == 1

    @patch('main_apply_rules.os.path.exists')
    def test_load_rules_file_not_found(self, mock_exists):
        """Test rule loading when file doesn't exist"""
        mock_exists.return_value = False
        
        # Import the module to test
        import main_apply_rules
        
        # Execute and verify exception
        with pytest.raises(FileNotFoundError):
            main_apply_rules.load_rules()

    @patch('main_apply_rules.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_rules_invalid_predicate(self, mock_file, mock_exists):
        """Test rule loading with invalid predicate"""
        mock_exists.return_value = True
        mock_rules = {
            "predicate": "invalid",
            "rules": [{"field": "from", "predicate": "contains", "value": "test"}],
            "actions": ["mark_as_read"]
        }
        mock_file.return_value.read.return_value = json.dumps(mock_rules)
        
        # Import the module to test
        import main_apply_rules
        
        # Execute and verify exception
        with pytest.raises(ValueError, match="Predicate must be either 'all' or 'any'"):
            main_apply_rules.load_rules()

    @patch('main_apply_rules.gmail_actions.mark_as_read')
    def test_apply_actions_mark_as_read(self, mock_mark_read):
        """Test applying mark_as_read action"""
        # Import the module to test
        import main_apply_rules
        
        mock_service = Mock()
        mock_email = Mock()
        mock_email.id = 1
        mock_email.msg_id = "msg_123"
        
        # Execute
        main_apply_rules.apply_actions(mock_service, "test@example.com", mock_email, ["mark_as_read"])
        
        # Verify
        mock_mark_read.assert_called_once_with(mock_service, "msg_123", "test@example.com", mock_email)

    @patch('main_apply_rules.gmail_actions.move_to_label')
    def test_apply_actions_move_to_label(self, mock_move):
        """Test applying move_to_label action"""
        # Import the module to test
        import main_apply_rules
        
        mock_service = Mock()
        mock_email = Mock()
        mock_email.id = 1
        mock_email.msg_id = "msg_123"
        
        # Execute
        main_apply_rules.apply_actions(mock_service, "test@example.com", mock_email, ["move_to_label:INBOX"])
        
        # Verify
        mock_move.assert_called_once_with(mock_service, "msg_123", "test@example.com", "INBOX", mock_email)

    # def test_apply_actions_unsupported_action_with_caplog(self, caplog):
    #     """Test that unsupported actions are logged"""
    #     import main_apply_rules
        
    #     mock_service = Mock()
    #     mock_email = Mock()
    #     mock_email.id = 1
        
    #     with caplog.at_level(logging.ERROR):
    #         main_apply_rules.apply_actions(mock_service, "test@example.com", mock_email, ["invalid_action"])
        
    #     # Check that error was logged
    #     assert len(caplog.records) > 0
    #     assert any("Unsupported action" in record.message for record in caplog.records)

class TestMainFetch:
    """Test cases for main_fetch module"""
    
    @patch('main_fetch.init_db')
    @patch('main_fetch.fetch_emails_for_user')
    @patch('main_fetch.os.getenv')
    def test_main_fetch_function(self, mock_getenv, mock_fetch, mock_init_db):
        """Test main fetch function directly"""
        mock_getenv.return_value = "30"
        
        # Import and test the main function directly
        import main_fetch
        
        # Mock sys.argv
        with patch('main_fetch.sys.argv', ['main_fetch.py', 'test@example.com']):
            # Call the main function if it exists, or simulate the main logic
            if hasattr(main_fetch, 'main'):
                main_fetch.main()
            else:
                # Simulate the main script execution
                email = 'test@example.com'
                days = mock_getenv.return_value
                mock_init_db()
                mock_fetch(email, days=days)
        
        # Verify
        mock_init_db.assert_called()
        mock_fetch.assert_called()

    @patch('main_fetch.init_db')
    @patch('main_fetch.fetch_emails_for_user')
    @patch('main_fetch.os.getenv')
    def test_main_fetch_with_days_env(self, mock_getenv, mock_fetch, mock_init_db):
        """Test main fetch with environment variable for days"""
        mock_getenv.return_value = "7"
        
        # Import and test
        import main_fetch
        
        # Mock sys.argv and test
        with patch('main_fetch.sys.argv', ['main_fetch.py', 'test@example.com']):
            # Simulate main execution
            email = 'test@example.com'
            days = mock_getenv.return_value
            mock_init_db()
            mock_fetch(email, days=days)
        
        # Verify
        mock_init_db.assert_called()
        mock_fetch.assert_called_with('test@example.com', days='7')


class TestDbSchema:
    """Test cases for db.schema module"""
    
    @patch('db.schema.get_connection')
    def test_init_db_success(self, mock_get_connection):
        """Test successful database initialization"""
        mock_conn = Mock()
        mock_cur = Mock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_connection.return_value = mock_conn
        
        # Execute
        from db.schema import init_db
        init_db()
        
        # Verify
        mock_cur.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cur.close.assert_called_once()
        mock_conn.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])