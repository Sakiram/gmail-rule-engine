import sys
import os
import pytest
from unittest.mock import patch

@patch("main_fetch.init_db")
@patch("main_fetch.fetch_emails_for_user")
@patch("main_fetch.load_dotenv")
def test_main_fetch_valid_args(mock_load_dotenv, mock_fetch_emails, mock_init_db):
    test_email = "test_user@gmail.com"
    test_days = "5"

    with patch.dict(os.environ, {"days": test_days}):
        test_args = ["main_fetch.py", test_email, "--days", test_days]
        with patch.object(sys, "argv", test_args):
            from main_fetch import main
            main()
            mock_init_db.assert_called_once()
            mock_fetch_emails.assert_called_once_with(test_email, days=int(test_days))


def test_main_fetch_no_args():
    test_args = ["main_fetch.py"]
    with patch.object(sys, "argv", test_args):
        from main_fetch import main
        with pytest.raises(SystemExit):
            main()


def test_main_fetch_invalid_days():
    test_args = ["main_fetch.py", "user@gmail.com", "--days", "notanumber"]
    with patch.object(sys, "argv", test_args):
        from main_fetch import main
        with pytest.raises(SystemExit):
            main()
