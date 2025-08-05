# Technical Context: Bitrix Deal Dialogues Extractor

## Core Technologies
- Python 3.8+
- Bitrix24 REST API
- Requests library for HTTP operations

## Development Setup
1. Python virtual environment recommended
2. Required packages:
   ```bash
   pip install requests python-dotenv
   ```
3. Environment variables needed:
   - BITRIX_WEBHOOK_URL
   - BITRIX_AUTH_TOKEN

## Dependencies
- requests>=2.25.1
- python-dotenv>=0.19.0

## Technical Constraints
- Must handle Bitrix API rate limits
- Should work with both cloud and on-premise Bitrix
