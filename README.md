# Canary Speech API Client

A Python implementation of the Canary Speech API v3 typical workflow for vocal analysis and assessment scoring.

## Overview

This client implements the complete workflow described in the [Canary Speech API documentation](https://docs.canaryspeech.com/v3/overview/index.html#typical-workflow):

1. **Authentication** - Obtain OAuth 2.0 access tokens
2. **Create Subject** - Create a subject for assessment tracking
3. **Begin Assessment** - Start assessment and get upload URLs
4. **Upload Recording** - Upload audio file for analysis
5. **End Assessment** - Trigger scoring mechanisms
6. **Poll for Completion** - Wait for processing to complete
7. **Retrieve Scores** - Get and display the final scores

## Requirements

- Python 3.9+
- macOS, Linux, or Windows
- Internet connection
- Valid Canary Speech API credentials

## Installation

### 1. Clone or Download the repo

### 2. Install Dependencies

```bash
pip install -f requirements.txt
```

Or create a virtual environment (recommended):

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -f requirements.txt
```

### 3. Set Up Credentials

You'll need the following from Canary Speech:
- **API Key** (format: `CLIENT_ID:SECRET`)
- **Project ID**
- **Survey Code**
- **Region** (eus, ne, or jpe)

You can provide these via command-line arguments or environment variables.

## Usage

### Basic Usage

```bash
python canary_speech_client.py \
  --audio-file path/to/recording.wav \
  --api-key "your-api-key" \
  --project-id "your-project-id" \
  --survey-code "your-survey-code" \
  --subject-name "your-subject-name" \
  --region eus  # Optional, defaults to eus
```

### Using Environment Variables

Set up your credentials once:

```bash
export CANARY_API_KEY="1A2B3C:YWJjZGVmZ2hhYmNkZWZnaGFiY2RlZmdoYWJjZGVmZ2hhYmNk"
export CANARY_PROJECT_ID="your-project-id"
export CANARY_SURVEY_CODE="your-survey-code"
export CANARY_REGION="eus"  # Optional, defaults to eus
```

Then run with just the audio file and subject name:

```bash
python canary_speech_client.py --audio-file recording.wav --subject-name "Test_Subject"
```
