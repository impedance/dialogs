# Technical Context: Bitrix Deal Dialogues Extractor

## Core Technologies
- Python 3.8+
- Bitrix24 REST API
- Requests library for HTTP operations
- Pandas for data structuring (optional)
- python-dotenv for configuration management

## Development Setup
1. Python virtual environment recommended
2. Required packages:
   ```bash
   pip install requests python-dotenv pandas
   ```
3. Environment variables needed:
   - BITRIX_WEBHOOK_URL
   - BITRIX_AUTH_TOKEN
   - OUTPUT_DIR (optional)

## Dependencies
- requests>=2.25.1
- python-dotenv>=0.19.0
- pandas>=1.3.0 (optional for CSV export)

## Technical Constraints
- Must handle Bitrix API rate limits (2 requests/sec)
- Should work with both cloud and on-premise Bitrix
- Must support Python 3.8+ on Windows/Linux/macOS

## Tool Usage Patterns
- API calls wrapped in rate-limited functions
- Configuration through .env file
- Logging to both console and file
- Modular design for easy maintenance
