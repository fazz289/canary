#!/usr/bin/env python3
"""
Canary Speech API Client
Implements the typical workflow for the Canary Speech API v3.

Usage:
    python canary_speech_client.py --audio-file path/to/audio.wav

Requirements:
    pip install requests pyjwt
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

import jwt
import requests


class CanarySpeechClient:
    # API endpoints for different regions
    REGIONS = {
        'eus': 'https://rest.eus.canaryspeech.com',  # East US
        'ne': 'https://rest.ne.canaryspeech.com',    # North Europe
        'jpe': 'https://rest.jpe.canaryspeech.com'   # Japan East
    }

    def __init__(self, api_key: str, region: str = 'eus'):
        """
        Initialize the Canary Speech API client.

        Args:
            api_key: API key in format "CLIENT_ID:SECRET"
            region: Region code ('eus', 'ne', or 'jpe')
        """
        self.api_key = api_key
        self.base_url = self.REGIONS.get(region)
        if not self.base_url:
            raise ValueError(f"Invalid region: {region}. Must be one of {list(self.REGIONS.keys())}")

        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    def authenticate(self) -> bool:
        """
        Authenticate with the API and obtain access tokens.

        Returns:
            bool: True if authentication successful, False otherwise
        """
        url = f"{self.base_url}/v3/auth/tokens/get"
        headers = {
            'Csc-Api-Key': self.api_key,
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(url, headers=headers)
            response.raise_for_status()

            data = response.json()
            self.access_token = data.get('accessToken')
            self.refresh_token = data.get('refreshToken')

            if self.access_token:
                # Decode JWT to get expiration
                decoded = jwt.decode(self.access_token, options={"verify_signature": False})
                exp_timestamp = decoded.get('exp', 0)
                exp_datetime = datetime.fromtimestamp(exp_timestamp)
                print(f"✓ Authentication successful")
                print(f"  Token expires: {exp_datetime}")
                return True
            else:
                print("✗ Authentication failed: No access token received")
                return False

        except requests.exceptions.RequestException as e:
            print(f"✗ Authentication error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Response: {e.response.text}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token."""
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def create_subject(self, project_id: str, subject_name: str):
        """
        Create a new subject.

        Args:
            project_id: The project ID provided by Canary Speech
            subject_name: The name of the subject

        Returns:
            str: Subject ID if successful, None otherwise
        """
        url = f"{self.base_url}/v3/api/create-subject"
        payload = {
            'projectId': project_id,
            'name': subject_name
        }

        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()

            data = response.json()
            subject_id = data.get('id')
            print(f"✓ Subject created: {subject_id}")
            return subject_id

        except requests.exceptions.RequestException as e:
            print(f"✗ Error creating subject: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Response: {e.response.text}")
            return None

    def begin_assessment(self, survey_code: str, subject_id: str) -> Optional[Tuple[str, Dict]]:
        """
        Begin an assessment and get upload URLs.

        Args:
            survey_code: The survey code provided by Canary Speech
            subject_id: The subject ID for this assessment

        Returns:
            Tuple of (assessment_id, upload_urls_dict) if successful, None otherwise
        """
        url = f"{self.base_url}/v3/api/assessment/begin"
        payload = {
            'surveyCode': survey_code,
            'subjectId': subject_id,
            'generateUploadUrls': True
        }

        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()

            data = response.json()
            assessment_id = data.get('id')
            upload_urls = data.get('uploadUrls', {})

            print(f"✓ Assessment started: {assessment_id}")
            print(f"  Upload URLs available for {len(upload_urls)} recording(s)")
            return assessment_id, upload_urls

        except requests.exceptions.RequestException as e:
            print(f"✗ Error beginning assessment: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Response: {e.response.text}")
            return None

    def validate_audio_file(self, audio_file_path: str) -> bool:
        """
        Validate audio file meets Canary Speech requirements.

        Per documentation at https://docs.canaryspeech.com/v3/recording-guidelines/
        Minimum: 16kHz, 16-bit, mono WAV (uncompressed)
        Recommended: 48kHz, 16-bit, mono WAV (uncompressed)

        Args:
            audio_file_path: Path to the audio file

        Returns:
            bool: True if valid (or unable to validate), False if clearly invalid
        """
        file_path = Path(audio_file_path)

        # Check file exists
        if not file_path.exists():
            print(f"✗ Audio file not found: {audio_file_path}")
            return False

        # Check file extension
        extension = file_path.suffix.lower()
        if extension not in ['.wav', '.mp3', '.m4a', '.ogg', '.flac']:
            print(f"⚠ Warning: Unsupported file extension: {extension}")
            print(f"  Recommended: .wav (uncompressed)")
            print(f"  Supported: .wav, .mp3, .m4a, .ogg, .flac")

        # Try to read WAV header for validation (optional, requires wave module)
        if extension == '.wav':
            try:
                import wave
                with wave.open(audio_file_path, 'rb') as wav:
                    channels = wav.getnchannels()
                    sample_rate = wav.getframerate()
                    sample_width = wav.getsampwidth()
                    duration = wav.getnframes() / float(sample_rate)

                    # Validate per documentation requirements
                    warnings = []
                    errors = []

                    # Sample rate check
                    if sample_rate < 16000:
                        errors.append(f"Sample rate too low: {sample_rate}Hz (minimum: 16000Hz)")
                    elif sample_rate < 48000:
                        warnings.append(f"Sample rate {sample_rate}Hz is acceptable but 48000Hz recommended")

                    # Bit depth check
                    bit_depth = sample_width * 8
                    if bit_depth < 16:
                        errors.append(f"Bit depth too low: {bit_depth}-bit (minimum: 16-bit)")
                    elif bit_depth > 16:
                        warnings.append(f"Bit depth {bit_depth}-bit is higher than required 16-bit")

                    # Channel check
                    if channels > 2:
                        warnings.append(f"Multi-channel audio ({channels} channels). 1 channel per speaker recommended")

                    # Duration check (40-45 seconds recommended per documentation)
                    if duration < 20:
                        warnings.append(f"Audio duration {duration:.1f}s is short (20-45s recommended)")
                    elif duration < 40:
                        warnings.append(f"Audio duration {duration:.1f}s is acceptable (40-45s optimal)")

                    # Print validation results
                    if errors:
                        print("✗ Audio validation failed:")
                        for error in errors:
                            print(f"  • {error}")
                        return False

                    if warnings:
                        print("⚠ Audio validation warnings:")
                        for warning in warnings:
                            print(f"  • {warning}")
                    else:
                        print(f"✓ Audio validation passed:")
                        print(f"  • Sample rate: {sample_rate}Hz")
                        print(f"  • Bit depth: {bit_depth}-bit")
                        print(f"  • Channels: {channels}")
                        print(f"  • Duration: {duration:.1f}s")

            except Exception as e:
                # If validation fails, warn but don't block
                print(f"⚠ Unable to validate WAV file: {e}")
                print(f"  Proceeding with upload...")

        return True

    def upload_recording(self, upload_url: str, audio_file_path: str) -> bool:
        """
        Upload an audio recording to the provided URL.

        Per Canary Speech documentation, the audio must:
        - Be in WAV format with WAV header (required)
        - Have Content-Type: audio/wav in HTTP request
        - Meet minimum specs: 16kHz, 16-bit, mono
        - Recommended specs: 48kHz, 16-bit, mono

        Args:
            upload_url: The pre-signed URL from begin_assessment
            audio_file_path: Path to the audio file

        Returns:
            bool: True if upload successful, False otherwise
        """
        # Validate audio file first
        if not self.validate_audio_file(audio_file_path):
            return False

        file_path = Path(audio_file_path)

        # Per documentation: Content-Type must be audio/wav
        extension = file_path.suffix.lower()

        if extension == '.wav':
            # Documentation requires audio/wav for WAV files
            content_type = 'audio/wav'
        else:
            print(f"⚠ Warning: Non-WAV format not be optimal for analysis")
            print(f"  Recommended: Uncompressed WAV with proper header")

        try:
            with open(audio_file_path, 'rb') as audio_file:
                headers = {'Content-Type': content_type}
                response = requests.put(upload_url, data=audio_file, headers=headers)
                response.raise_for_status()

            file_size = file_path.stat().st_size / 1024  # KB
            print(f"✓ Audio uploaded successfully ({file_size:.1f} KB)")
            return True

        except requests.exceptions.RequestException as e:
            print(f"✗ Error uploading audio: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Response: {e.response.text}")
            return False

    def end_assessment(self, assessment_id: str) -> bool:
        """
        End an assessment and trigger scoring.

        Args:
            assessment_id: The assessment ID from begin_assessment
            non_verbal_responses: Optional non-verbal response data

        Returns:
            bool: True if successful, False otherwise
        """
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        url = f"{self.base_url}/v3/api/assessment/end"
        payload = {
            'assessmentId': assessment_id,
            'responseData': [
                {
                    'timestamp': timestamp,
                    'code': 'free_speech',
                    'type': 'recordedResponse',
                    'data': {
                        'duration': 53.4
                    }
                }
            ]
        }


        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()

            print(f"✓ Assessment ended: {assessment_id}")
            print("  Scoring in progress...")
            return True

        except requests.exceptions.RequestException as e:
            print(f"✗ Error ending assessment: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Response: {e.response.text}")
            return False

    def poll_assessment(self, assessment_id: str, max_attempts: int = 150,
                        poll_interval: int = 2) -> bool:
        """
        Poll the assessment until scores are ready.

        Args:
            assessment_id: The assessment ID to poll
            max_attempts: Maximum number of polling attempts (default 150 = 5 minutes)
            poll_interval: Seconds between polls (default 2, per documentation)

        Returns:
            bool: True if scores are ready, False if timeout
        """
        url = f"{self.base_url}/v3/api/assessment/poll"
        params = {'assessmentId': assessment_id}

        print(f"⏳ Polling for scores (max {max_attempts * poll_interval}s)...")

        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.get(url, headers=self._get_headers(), params=params)
                response.raise_for_status()

                data = response.json()
                status = data.get('status', 'unknown')

                if status == 'completed':
                    print(f"✓ Scores ready (after {attempt * poll_interval}s)")
                    return True
                elif status == 'failed':
                    print(f"✗ Assessment failed")
                    return False
                elif status in ['processing', 'pending']:
                    if attempt % 10 == 0:  # Print progress every 20 seconds
                        print(f"  Still processing... ({attempt * poll_interval}s elapsed)")
                    time.sleep(poll_interval)
                else:
                    print(f"  Unknown status: {status}")
                    time.sleep(poll_interval)

            except requests.exceptions.RequestException as e:
                print(f"✗ Polling error: {e}")
                return False

        print(f"✗ Timeout: Scores not ready after {max_attempts * poll_interval}s")
        return False

    def get_scores(self, assessment_id: str) -> Optional[Dict]:
        """
        Retrieve the scores for a completed assessment.

        Args:
            assessment_id: The assessment ID

        Returns:
            dict: Score data if successful, None otherwise
        """
        url = f"{self.base_url}/v3/api/list-scores"
        params = {'assessmentId': assessment_id}

        try:
            response = requests.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()

            data = response.json()
            print("✓ Scores retrieved successfully")
            return data

        except requests.exceptions.RequestException as e:
            print(f"✗ Error retrieving scores: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Response: {e.response.text}")
            return None


def display_scores(scores: Dict) -> None:
    """
    Display assessment scores in a readable format.

    Args:
        scores: Score data from the API
    """
    print("\n" + "="*60)
    print("ASSESSMENT SCORES")
    print("="*60)

    # Display assessment metadata
    if 'assessmentId' in scores:
        print(f"\nAssessment ID: {scores['assessmentId']}")
    if 'subject_id' in scores:
        print(f"Subject ID: {scores['subjectIid']}")

    # Display scores
    if 'scores' in scores:
        print("\nScores:")
        for score_item in scores['scores']:
            score_type = score_item.get('code', 'unknown')
            value = score_item.get('data', {}).get('result', 'N/A')
            print(f"\n  {score_type}:")
            print(f"    Result: {value}")

    # Display full JSON for reference
    print("\n" + "-"*60)
    print("Full Response (JSON):")
    print("-"*60)
    print(json.dumps(scores, indent=2))
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Canary Speech API Client - Submit audio for vocal analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python canary_speech_client.py --audio-file recording.wav

Environment variables (alternative to command-line args):
  CANARY_API_KEY      - API key (format: CLIENT_ID:SECRET)
  CANARY_PROJECT_ID   - Project ID
  CANARY_SURVEY_CODE  - Survey code
  CANARY_REGION       - Region (eus, ne, or jpe)
        """
    )

    parser.add_argument('--audio-file', required=True,
                        help='Path to audio file (WAV file)')
    parser.add_argument('--api-key',
                        help='API key (or set CANARY_API_KEY env var)')
    parser.add_argument('--project-id',
                        help='Project ID (or set CANARY_PROJECT_ID env var)')
    parser.add_argument('--survey-code',
                        help='Survey code (or set CANARY_SURVEY_CODE env var)')
    parser.add_argument('--subject-name', required=True,
                        help='Name used to create a subject')
    parser.add_argument('--region', default='eus', choices=['eus', 'ne', 'jpe'],
                        help='API region (default: eus)')
    parser.add_argument('--response-code',
                        help='Response code for the recording (default: first available)')

    args = parser.parse_args()

    # Get credentials from args or environment
    import os
    api_key = args.api_key or os.environ.get('CANARY_API_KEY')
    project_id = args.project_id or os.environ.get('CANARY_PROJECT_ID')
    survey_code = args.survey_code or os.environ.get('CANARY_SURVEY_CODE')
    region = args.region or os.environ.get('CANARY_REGION', 'eus')

    # Validate required parameters
    if not api_key:
        print("✗ Error: API key required (--api-key or CANARY_API_KEY)")
        sys.exit(1)
    if not project_id:
        print("✗ Error: Project ID required (--project-id or CANARY_PROJECT_ID)")
        sys.exit(1)
    if not survey_code:
        print("✗ Error: Survey code required (--survey-code or CANARY_SURVEY_CODE)")
        sys.exit(1)

    print("Canary Speech API Client")
    print("="*60)
    print(f"Audio file: {args.audio_file}")
    print(f"Region: {region}")
    print("="*60 + "\n")

    # Initialize client
    client = CanarySpeechClient(api_key, region)

    # Step 1: Authenticate
    print("Step 1: Authenticating...")
    if not client.authenticate():
        sys.exit(1)
    print()

    # Step 2: Create or use subject
    subject_name = args.subject_name
    if not subject_name:
        print("✗ Error: Subject name required to create a new subject")
        sys.exit(1)
    print(f"Step 2: Creating subject '{subject_name}'...")
    subject_id = client.create_subject(project_id, subject_name)
    if not subject_id:
        sys.exit(1)
    print()

    # Step 3: Begin assessment
    print("Step 3: Beginning assessment...")
    result = client.begin_assessment(survey_code, subject_id)
    if not result:
        sys.exit(1)
    assessment_id, upload_urls = result
    print()

    # Step 4: Upload recording
    print("Step 4: Uploading recording...")
    if not upload_urls:
        print("✗ No upload URLs available")
        sys.exit(1)

    # Use specified response code or first available
    response_code = args.response_code
    if response_code and response_code not in upload_urls:
        print(f"✗ Response code '{response_code}' not found")
        print(f"  Available: {list(upload_urls.keys())}")
        sys.exit(1)

    if not response_code:
        response_code = list(upload_urls.keys())[0]
        print(f"  Using response code: {response_code}")

    upload_url = upload_urls[response_code]
    if not client.upload_recording(upload_url, args.audio_file):
        sys.exit(1)
    print()

    # Step 5: End assessment
    print("Step 5: Ending assessment...")
    if not client.end_assessment(assessment_id):
        sys.exit(1)
    print()

    # Step 6: Poll for completion
    print("Step 6: Waiting for scores...")
    if not client.poll_assessment(assessment_id):
        sys.exit(1)
    print()

    # Step 7: Retrieve and display scores
    print("Step 7: Retrieving scores...")
    scores = client.get_scores(assessment_id)
    if scores:
        display_scores(scores)
    else:
        sys.exit(1)

    print("✓ Workflow completed successfully!")


if __name__ == '__main__':
    main()
