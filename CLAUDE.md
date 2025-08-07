# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Python project containing Bitrix24 API integrations for chat dialog and deal extraction. The codebase consists of Python scripts that use the Bitrix24 REST API to export and analyze data.

## Key Components

- **get-dialogs.py**: Chat dialog exporter containing the `Bitrix24ChatExporter` class
  - API connection and authentication via webhook URL
  - Paginated retrieval of all dialogs from Bitrix24
  - Message extraction from individual dialogs  
  - Export functionality to JSON and CSV formats
  - Connection testing and error handling

- **get_first_deal.py**: Deal extractor containing the `Bitrix24DealExtractor` class (v2.0)
  - Advanced deal extraction with multiple search modes
  - Smart message deduplication and pagination
  - CRM timeline comment retrieval with optimization
  - Comprehensive command-line interface
  - API statistics tracking and error handling
  - Smart logging (DEBUG for normal ops, INFO for errors/retries)

## Running the Scripts

### Chat Dialog Exporter
```bash
# Full export (default mode)
python3 get-dialogs.py

# Connection test only
python3 get-dialogs.py test
```

### Deal Extractor
```bash
# Search by deal number in title
python3 get_first_deal.py --find-number 185046537

# Process specific deal by ID
python3 get_first_deal.py --deal-id 27

# Fast mode - first deal only
python3 get_first_deal.py --first-only

# All deals with dialogues (default)
python3 get_first_deal.py

# Advanced search - find all numbers in messages
python3 get_first_deal.py --find-all-numbers

# Custom parameters
python3 get_first_deal.py --deal-id 27 --debug --output results.json --rate-limit 1.0
```

## Configuration

### Dialog Exporter
Webhook URL configured at line 324:
```python
WEBHOOK_URL = "https://b24-mwh5lj.bitrix24.ru/rest/1/vhbpg01ls83dn4rq/"
```

### Deal Extractor  
Webhook URL configured at line 504:
```python
WEBHOOK_URL = "https://b24-mwh5lj.bitrix24.ru/rest/1/zutp42hzvz9lyl8h/"
```

Configuration options:
- `rate_limit_delay`: Delay between API requests (default 0.5s)
- `request_timeout`: Request timeout (default 30s)
- `max_retries`: Maximum retry attempts (default 5)
- `disable_proxy`: Controls proxy usage (default True)
- `verify_ssl`: SSL certificate verification (default True)

## API Integration

### Dialog Exporter API methods:
- `profile` - User authentication test
- `im.recent.list` - Dialog list retrieval with pagination
- `im.dialog.messages.get` - Message extraction per dialog

### Deal Extractor API methods:
- `crm.deal.get` - Get specific deal by ID
- `crm.deal.list` - Search deals with filters and pagination
- `crm.timeline.comment.list` - Get deal messages/comments with smart pagination

## Features & Optimizations

### Deal Extractor v2.0 Improvements:
- **Message Deduplication**: Automatic removal of duplicate messages using ID tracking
- **Smart Pagination**: Stops when no new messages found, prevents infinite loops
- **Optimized Logging**: DEBUG level for normal operations, INFO for important events
- **Multiple Search Modes**: By ID, by number in title, extract numbers from text
- **Regex Pattern Matching**: Finds deal numbers in various text formats
- **API Statistics**: Comprehensive tracking of requests, success rates, timing
- **Error Recovery**: Exponential backoff with jitter for failed requests
- **Safety Limits**: 100-page pagination limit to prevent runaway requests

## Output Files

### Dialog Exporter:
- `bitrix24_dialogs_full.json` - Complete export with messages
- `bitrix24_dialogs_list.csv` - Dialog metadata only

### Deal Extractor:
- Custom JSON output with `--output filename.json`
- `bitrix_extractor.log` - Comprehensive logging
- Console output with formatted deal details and messages

## Dependencies

Standard library plus requests:
- requests
- json
- time
- typing
- datetime
- csv
- urllib3 (for SSL warning suppression)
- re (regex patterns)
- random (retry jitter)
- logging
- argparse

## API Documentation
https://github.com/bitrix-tools/b24-rest-docs
https://apidocs.bitrix24.ru/