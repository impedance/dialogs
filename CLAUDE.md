# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a single-file Python project containing a Bitrix24 chat dialog exporter. The codebase consists of a single Python script that uses the Bitrix24 REST API to export chat dialogs and messages.

## Key Components

- **get-dialogs.py**: Main script containing the `Bitrix24ChatExporter` class that handles:
  - API connection and authentication via webhook URL
  - Paginated retrieval of all dialogs from Bitrix24
  - Message extraction from individual dialogs  
  - Export functionality to JSON and CSV formats
  - Connection testing and error handling

## Running the Script

The script can be executed in two modes:

```bash
# Full export (default mode)
python3 get-dialogs.py

# Connection test only
python3 get-dialogs.py test
```

## Configuration

The script requires configuration of the webhook URL at line 324:
```python
WEBHOOK_URL = "https://b24-mwh5lj.bitrix24.ru/rest/1/vhbpg01ls83dn4rq/"
```

The exporter supports configuration options:
- `disable_proxy`: Controls proxy usage (default True)
- `verify_ssl`: SSL certificate verification (default True)
- `max_messages_per_dialog`: Limits messages per dialog (default 100)

## API Integration

Uses Bitrix24 REST API methods:
- `profile` - User authentication test
- `im.recent.list` - Dialog list retrieval with pagination
- `im.dialog.messages.get` - Message extraction per dialog

## Output Files

- `bitrix24_dialogs_full.json` - Complete export with messages
- `bitrix24_dialogs_list.csv` - Dialog metadata only

## Dependencies

Standard library only:
- requests
- json
- time
- typing
- datetime
- csv
- urllib3 (for SSL warning suppression)


https://github.com/bitrix-tools/b24-rest-docs
https://apidocs.bitrix24.ru/