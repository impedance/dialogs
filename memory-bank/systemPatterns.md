# System Patterns: Bitrix Deal Dialogues Extractor

## Architecture Overview
- Modular design with clear separation of concerns:
  1. Authentication module
  2. API client module
  3. Data processing module
  4. Output generation module

## Key Technical Decisions
- Using Bitrix REST API instead of direct database access
- Implementing rate limiting at the application level
- JSON as primary data interchange format
- Optional CSV export via Pandas

## Design Patterns
- Repository pattern for API interactions
- Factory pattern for output format selection
- Strategy pattern for different deal filtering approaches
- Observer pattern for progress reporting

## Component Relationships
1. Main script coordinates:
   - Authentication
   - Deal retrieval
   - Dialogue extraction
   - Data export

2. Error handling centralized in main execution flow

## Critical Implementation Paths
1. Authentication and session management
2. Paginated deal retrieval
3. Dialogue extraction per deal
4. Data transformation and export
5. Error recovery and retry logic
