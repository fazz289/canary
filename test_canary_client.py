import unittest
from unittest.mock import patch, MagicMock
from canary_speech_client import CanarySpeechClient

class TestCanarySpeechClient(unittest.TestCase):
    def setUp(self):
        self.client = CanarySpeechClient(api_key="test_id:test_secret", region="eus")

    @patch("requests.post")
    def test_authenticate_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "accessToken": "fake.jwt.token",
            "refreshToken": "refresh"
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with patch("jwt.decode", return_value={"exp": 9999999999}):
            result = self.client.authenticate()
            self.assertTrue(result)
            self.assertEqual(self.client.access_token, "fake.jwt.token")

    @patch("requests.post")
    def test_create_subject_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "subject123"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.client.access_token = "token"
        subject_id = self.client.create_subject("proj", "name")
        self.assertEqual(subject_id, "subject123")

    @patch("requests.post")
    def test_begin_assessment_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "assess123", "uploadUrls": {"code": "url"}}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.client.access_token = "token"
        result = self.client.begin_assessment("survey", "subject")
        self.assertEqual(result[0], "assess123")
        self.assertIn("code", result[1])

    @patch("canary_speech_client.Path.exists", return_value=True)
    @patch("canary_speech_client.Path.suffix", new_callable=MagicMock(return_value=".wav"))
    @patch("wave.open")
    def test_validate_audio_file_wav(self, mock_wave_open, mock_suffix, mock_exists):
        mock_wave = MagicMock()
        mock_wave.getnchannels.return_value = 1
        mock_wave.getframerate.return_value = 16000
        mock_wave.getsampwidth.return_value = 2
        mock_wave.getnframes.return_value = 320000
        mock_wave_open.return_value.__enter__.return_value = mock_wave

        result = self.client.validate_audio_file("sample.wav")
        self.assertTrue(result)

    @patch("requests.put")
    @patch("canary_speech_client.Path.exists", return_value=True)
    @patch("canary_speech_client.Path.suffix", new_callable=MagicMock(return_value=".wav"))
    @patch("builtins.open", new_callable=MagicMock)
    def test_upload_recording_success(self, mock_put, mock_suffix, mock_exists, mock_open):
        self.client.access_token = "token"
        mock_put.return_value.raise_for_status.return_value = None
        with patch.object(self.client, "validate_audio_file", return_value=True):
            with patch("canary_speech_client.Path.stat", return_value=MagicMock(st_size=1024)):
                result = self.client.upload_recording("url", "file.wav")
                self.assertTrue(result)

    @patch("requests.post")
    def test_end_assessment_success(self, mock_post):
        mock_post.return_value.raise_for_status.return_value = None
        self.client.access_token = "token"
        result = self.client.end_assessment("assess_id")
        self.assertTrue(result)

    @patch("requests.get")
    def test_poll_assessment_completed(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "completed"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        self.client.access_token = "token"
        result = self.client.poll_assessment("assess_id", max_attempts=1, poll_interval=0)
        self.assertTrue(result)

    @patch("requests.get")
    def test_get_scores_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"scores": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        self.client.access_token = "token"
        scores = self.client.get_scores("assess_id")
        self.assertIsInstance(scores, dict)

if __name__ == "__main__":
    unittest.main()
