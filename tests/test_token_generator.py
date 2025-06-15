import unittest
from unittest.mock import patch, mock_open, MagicMock
import json

class TestTokenGenerator(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    @patch("googleapiclient.discovery.build")
    @patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file")
    def test_token_generation_and_auth(
        self,
        mock_from_client_secrets_file,
        mock_build,
        mock_json_dump,
        mock_file
    ):
        # Mock credentials object and its to_json method
        mock_creds = MagicMock()
        mock_creds.to_json.return_value = json.dumps({"token": "abc123"})

        # Mock OAuth flow
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_from_client_secrets_file.return_value = mock_flow

        # Mock Gmail API build and profile fetch
        mock_service = MagicMock()
        mock_users = mock_service.users.return_value
        mock_users.getProfile.return_value.execute.return_value = {"emailAddress": "user@example.com"}
        mock_build.return_value = mock_service

        # Import the script to test
        import token_generator  # assumes your script is saved as token_generator.py

        # Assertions
        mock_from_client_secrets_file.assert_called_once_with('config/credentials.json', ['https://www.googleapis.com/auth/gmail.modify'])
        mock_json_dump.assert_called_once()
        mock_file.assert_called_with('config/tokens/token.json', 'w')
        mock_build.assert_called_once()
        mock_users.getProfile.assert_called_once()

if __name__ == '__main__':
    unittest.main()