import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from actions.gmail_actions import mark_as_read, mark_as_unread, move_to_label, _get_label_id
from db.models import Email


class TestGmailActions:
    """Test cases for Gmail actions module"""
    
    def setup_method(self):
        """Setup test data for each test method"""
        self.sample_email = Email(
            id="1",
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
        
        self.mock_service = Mock()
        self.user_id = "test@example.com"
        self.msg_id = "msg_123"

    @patch('actions.gmail_actions.update_email_status')
    def test_mark_as_read_success(self, mock_update_status):
        """Test successful mark as read operation"""
        # Setup mock
        self.mock_service.users().messages().modify.return_value.execute.return_value = {}
        
        # Execute
        mark_as_read(self.mock_service, self.msg_id, self.user_id, self.sample_email)
        
        # Verify Gmail API call
        self.mock_service.users().messages().modify.assert_called_once_with(
            userId=self.user_id,
            id=self.msg_id,
            body={'removeLabelIds': ['UNREAD']}
        )
        
        # Verify database update
        mock_update_status.assert_called_once_with(self.sample_email.id, marked_as="read")

    @patch('actions.gmail_actions.update_email_status')
    def test_mark_as_read_failure(self, mock_update_status):
        """Test mark as read operation failure"""
        # Setup mock to raise exception
        self.mock_service.users().messages().modify.side_effect = Exception("API Error")
        
        # Execute and verify exception
        with pytest.raises(Exception, match="Failed to mark as read: API Error"):
            mark_as_read(self.mock_service, self.msg_id, self.user_id, self.sample_email)
        
        # Verify database update was not called
        mock_update_status.assert_not_called()

    @patch('actions.gmail_actions.update_email_status')
    def test_mark_as_unread_success(self, mock_update_status):
        """Test successful mark as unread operation"""
        # Setup mock
        self.mock_service.users().messages().modify.return_value.execute.return_value = {}
        
        # Execute
        mark_as_unread(self.mock_service, self.msg_id, self.user_id, self.sample_email)
        
        # Verify Gmail API call
        self.mock_service.users().messages().modify.assert_called_once_with(
            userId=self.user_id,
            id=self.msg_id,
            body={'addLabelIds': ['UNREAD']}
        )
        
        # Verify database update
        mock_update_status.assert_called_once_with(self.sample_email.id, marked_as="unread")

    @patch('actions.gmail_actions.update_email_status')
    def test_mark_as_unread_failure(self, mock_update_status):
        """Test mark as unread operation failure"""
        # Setup mock to raise exception
        self.mock_service.users().messages().modify.side_effect = Exception("API Error")
        
        # Execute and verify exception
        with pytest.raises(Exception, match="Failed to mark as unread: API Error"):
            mark_as_unread(self.mock_service, self.msg_id, self.user_id, self.sample_email)
        
        # Verify database update was not called
        mock_update_status.assert_not_called()

    @patch('actions.gmail_actions.update_email_status')
    @patch('actions.gmail_actions._get_label_id')
    def test_move_to_label_success(self, mock_get_label_id, mock_update_status):
        """Test successful move to label operation"""
        # Setup mocks
        label_name = "CATEGORY_WORK"
        label_id = "Label_123"
        mock_get_label_id.return_value = label_id
        self.mock_service.users().messages().modify.return_value.execute.return_value = {}
        
        # Execute
        move_to_label(self.mock_service, self.msg_id, self.user_id, label_name, self.sample_email)
        
        # Verify label ID retrieval
        mock_get_label_id.assert_called_once_with(self.mock_service, self.user_id, label_name)
        
        # Verify Gmail API call
        self.mock_service.users().messages().modify.assert_called_once_with(
            userId=self.user_id,
            id=self.msg_id,
            body={'addLabelIds': [label_id]}
        )
        
        # Verify database update
        mock_update_status.assert_called_once_with(self.sample_email.id, msg_moved_to=label_name)

    @patch('actions.gmail_actions.update_email_status')
    @patch('actions.gmail_actions._get_label_id')
    def test_move_to_label_failure(self, mock_get_label_id, mock_update_status):
        """Test move to label operation failure"""
        # Setup mock to raise exception
        label_name = "CATEGORY_WORK"
        mock_get_label_id.side_effect = Exception("Label not found")
        
        # Execute and verify exception
        with pytest.raises(Exception, match="Failed to move message to label 'CATEGORY_WORK': Label not found"):
            move_to_label(self.mock_service, self.msg_id, self.user_id, label_name, self.sample_email)
        
        # Verify database update was not called
        mock_update_status.assert_not_called()

    def test_get_label_id_success_from_cache(self):
        """Test _get_label_id returns cached value"""
        # Setup cache
        from actions.gmail_actions import _label_cache
        cache_key = f"{self.user_id}:inbox"
        expected_label_id = "INBOX_ID"
        _label_cache[cache_key] = expected_label_id
        
        # Execute
        result = _get_label_id(self.mock_service, self.user_id, "INBOX")
        
        # Verify
        assert result == expected_label_id
        # Verify service was not called (cache hit)
        self.mock_service.users().labels().list.assert_not_called()
        
        # Cleanup cache
        _label_cache.clear()

    def test_get_label_id_success_from_api(self):
        """Test _get_label_id fetches from API and caches result"""
        # Clear cache
        from actions.gmail_actions import _label_cache
        _label_cache.clear()
        
        # Setup mock API response
        mock_labels = [
            {"name": "INBOX", "id": "INBOX_ID"},
            {"name": "CATEGORY_WORK", "id": "WORK_ID"},
            {"name": "SPAM", "id": "SPAM_ID"}
        ]
        self.mock_service.users().labels().list.return_value.execute.return_value = {'labels': mock_labels}
        
        # Execute
        result = _get_label_id(self.mock_service, self.user_id, "CATEGORY_WORK")
        
        # Verify
        assert result == "WORK_ID"
        
        # Verify API was called
        self.mock_service.users().labels().list.assert_called_once_with(userId=self.user_id)
        
        # Verify cache was populated
        cache_key = f"{self.user_id}:category_work"
        assert _label_cache[cache_key] == "WORK_ID"

    def test_get_label_id_invalid_label(self):
        """Test _get_label_id with invalid label name"""
        # Clear cache
        from actions.gmail_actions import _label_cache
        _label_cache.clear()
        
        # Setup mock API response
        mock_labels = [
            {"name": "INBOX", "id": "INBOX_ID"},
            {"name": "SPAM", "id": "SPAM_ID"}
        ]
        self.mock_service.users().labels().list.return_value.execute.return_value = {'labels': mock_labels}
        
        # Execute and verify exception
        with pytest.raises(Exception, match="Label 'INVALID_LABEL' is not a valid Gmail label"):
            _get_label_id(self.mock_service, self.user_id, "INVALID_LABEL")

    def test_get_label_id_case_insensitive(self):
        """Test _get_label_id is case insensitive"""
        # Clear cache
        from actions.gmail_actions import _label_cache
        _label_cache.clear()
        
        # Setup mock API response
        mock_labels = [
            {"name": "INBOX", "id": "INBOX_ID"},
            {"name": "Category_Work", "id": "WORK_ID"}
        ]
        self.mock_service.users().labels().list.return_value.execute.return_value = {'labels': mock_labels}
        result = _get_label_id(self.mock_service, self.user_id, "category_work")
        assert result == "WORK_ID"

    def test_get_label_id_empty_labels_response(self):
        """Test _get_label_id with empty labels response"""
        # Clear cache
        from actions.gmail_actions import _label_cache
        _label_cache.clear()
        self.mock_service.users().labels().list.return_value.execute.return_value = {'labels': []}
        with pytest.raises(Exception, match="Label 'INBOX' is not a valid Gmail label"):
            _get_label_id(self.mock_service, self.user_id, "INBOX")

    @patch('actions.gmail_actions.update_email_status')
    def test_integration_mark_as_read_and_move_to_label(self, mock_update_status):
        """Test integration of multiple actions on same email"""
        label_name = "CATEGORY_WORK"
        label_id = "WORK_ID"
        mock_labels = [{"name": "CATEGORY_WORK", "id": label_id}]
        self.mock_service.users().labels().list.return_value.execute.return_value = {'labels': mock_labels}
        self.mock_service.users().messages().modify.return_value.execute.return_value = {}
        mark_as_read(self.mock_service, self.msg_id, self.user_id, self.sample_email)
        move_to_label(self.mock_service, self.msg_id, self.user_id, label_name, self.sample_email)
        assert mock_update_status.call_count == 2
        mock_update_status.assert_any_call(self.sample_email.id, marked_as="read")
        mock_update_status.assert_any_call(self.sample_email.id, msg_moved_to=label_name)        
        assert self.mock_service.users().messages().modify.call_count == 2