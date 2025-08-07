#!/usr/bin/env python3
import re
import requests
import json
import time
import random
import logging
import argparse
from datetime import datetime
from typing import Optional, List, Dict

class Bitrix24DealExtractor:
    def __init__(self, webhook_url, disable_proxy=True, verify_ssl=True, 
                 rate_limit_delay=0.5, request_timeout=30, max_retries=5):
        """
        Initialize Bitrix24 API client
        
        Args:
            webhook_url: Bitrix24 REST API webhook URL
            disable_proxy: Disable system proxies if True
            verify_ssl: Verify SSL certificates if True
            rate_limit_delay: Delay between API requests in seconds
            request_timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.webhook_url = webhook_url.rstrip('/')
        self.verify_ssl = verify_ssl
        self.rate_limit_delay = rate_limit_delay
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        
        # API statistics tracking
        self.api_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retry_attempts': 0,
            'start_time': None
        }
        
        if disable_proxy:
            self.session.proxies = {'http': None, 'https': None}
            
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Bitrix24DealExtractor/2.0'
        })
        
        if not verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def make_request(self, method, params=None):
        """
        Make API request to Bitrix24 with retry mechanism
        
        Args:
            method: API method name
            params: Request parameters
            
        Returns:
            dict: API response or empty dict on error
        """
        return self.make_request_with_retry(method, params, self.max_retries)
    
    def make_request_with_retry(self, method, params=None, max_retries=5):
        """
        Make API request with retry mechanism for handling temporary errors
        
        Args:
            method: API method name
            params: Request parameters
            max_retries: Maximum number of retry attempts
            
        Returns:
            dict: API response or empty dict on error
        """
        url = f"{self.webhook_url}/{method}"
        last_exception = None
        
        if self.api_stats['start_time'] is None:
            self.api_stats['start_time'] = datetime.now()
            
        for attempt in range(max_retries + 1):
            self.api_stats['total_requests'] += 1
            
            try:
                # Rate limiting - delay between requests
                if attempt > 0 or self.api_stats['total_requests'] > 1:
                    delay = self.rate_limit_delay
                    if attempt > 0:
                        # Exponential backoff with jitter for retries
                        delay = (2 ** attempt) + random.uniform(0, 1)
                        self.api_stats['retry_attempts'] += 1
                    
                    if attempt == 0:
                        logging.debug(f"Rate limiting delay: {delay:.2f}s before {method}")
                    else:
                        logging.info(f"Retry delay: {delay:.2f}s before {method}")
                    time.sleep(delay)
                
                if attempt == 0:
                    logging.debug(f"API Request #{self.api_stats['total_requests']}: {method}")
                else:
                    logging.info(f"API Request #{self.api_stats['total_requests']}: {method} (retry {attempt}/{max_retries})")
                
                response = self.session.post(
                    url, 
                    json=params, 
                    verify=self.verify_ssl, 
                    timeout=self.request_timeout
                )
                response.raise_for_status()
                result = response.json()
                
                if 'error' in result:
                    error_msg = f"API Error: {result['error']} - {result.get('error_description', '')}"
                    logging.error(error_msg)
                    self.api_stats['failed_requests'] += 1
                    return {}
                
                self.api_stats['successful_requests'] += 1
                if attempt == 0:
                    logging.debug(f"API Request successful: {method}")
                else:
                    logging.info(f"API Request successful: {method} (after {attempt} retries)")
                return result.get('result', result)
                
            except requests.exceptions.HTTPError as e:
                last_exception = e
                status_code = e.response.status_code if e.response else 0
                
                # Retry on specific HTTP errors
                if status_code in [500, 502, 503, 504] and attempt < max_retries:
                    logging.warning(f"HTTP {status_code} error for {method}, retrying... (attempt {attempt + 1})")
                    continue
                else:
                    logging.error(f"HTTP Error {status_code} for {method}: {e}")
                    break
                    
            except (requests.exceptions.ConnectionError, 
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException) as e:
                last_exception = e
                if attempt < max_retries:
                    logging.warning(f"Connection error for {method}, retrying... (attempt {attempt + 1}): {e}")
                    continue
                else:
                    logging.error(f"Connection error for {method}: {e}")
                    break
                    
            except Exception as e:
                last_exception = e
                logging.error(f"Unexpected error for {method}: {e}")
                break
        
        # All attempts failed
        self.api_stats['failed_requests'] += 1
        error_msg = f"All {max_retries + 1} attempts failed for {method}"
        if last_exception:
            error_msg += f": {last_exception}"
        logging.error(error_msg)
        return {}
    
    def get_first_deal(self):
        """
        Get first deal from Bitrix24
        
        Returns:
            dict: Deal data or empty dict if none found
        """
        params = {
            'order': {'DATE_CREATE': 'ASC'},
            'select': ['ID', 'TITLE', 'STAGE_ID', 'OPPORTUNITY', 'DATE_CREATE']
        }
        result = self.make_request('crm.deal.list', params)
        return result[0] if result else {}

    def get_all_deals(self):
        """
        Retrieve all deals using pagination.

        Returns:
            list: List of all deal dictionaries
        """
        all_deals = []
        start = 0
        while True:
            params = {
                'order': {'DATE_CREATE': 'ASC'},
                'select': ['ID', 'TITLE', 'STAGE_ID', 'OPPORTUNITY', 'DATE_CREATE'],
                'start': start
            }
            batch = self.make_request('crm.deal.list', params)
            if not isinstance(batch, list) or not batch:
                break
            all_deals.extend(batch)
            start += len(batch)
            
            # Optimized pagination - Bitrix24 API returns max 50 records
            if len(batch) < 50:
                break
                
        return all_deals
    
    def get_deal_by_id(self, deal_id):
        """
        Get specific deal by ID using optimized crm.deal.get method
        
        Args:
            deal_id: Deal ID (string or integer)
            
        Returns:
            dict: Deal data or empty dict if not found
        """
        if not self.validate_deal_id(deal_id):
            logging.error(f"Invalid deal ID: {deal_id}")
            return {}
            
        params = {'ID': str(deal_id)}
        logging.info(f"Getting deal by ID: {deal_id}")
        
        result = self.make_request('crm.deal.get', params)
        
        if result:
            logging.info(f"Found deal: {result.get('TITLE', 'No title')}")
            return result
        else:
            logging.warning(f"Deal not found: {deal_id}")
            return {}
    
    def find_deals_by_number(self, deal_number):
        """
        Find deals by number in title or comments
        
        Args:
            deal_number: Number to search for (e.g., 301721445)
            
        Returns:
            list: List of matching deals
        """
        if not isinstance(deal_number, (str, int)):
            logging.error(f"Invalid deal number type: {type(deal_number)}")
            return []
            
        deal_number_str = str(deal_number)
        logging.info(f"Searching for deals with number: {deal_number_str}")
        
        # First, try to find by ID if it looks like an ID
        if deal_number_str.isdigit():
            direct_deal = self.get_deal_by_id(deal_number_str)
            if direct_deal:
                return [direct_deal]
        
        # Search by title containing the number
        params = {
            'filter': {'%TITLE': deal_number_str},
            'select': ['ID', 'TITLE', 'STAGE_ID', 'OPPORTUNITY', 'DATE_CREATE']
        }
        
        result = self.make_request('crm.deal.list', params)
        
        if isinstance(result, list):
            logging.info(f"Found {len(result)} deals by title search")
            return result
        else:
            logging.warning(f"No deals found with number: {deal_number_str}")
            return []
    
    def extract_deal_numbers_from_text(self, text):
        """
        Extract deal numbers from text using various patterns
        
        Args:
            text: Text to search in
            
        Returns:
            list: List of unique deal numbers found
        """
        if not isinstance(text, str):
            return []
            
        patterns = [
            r'сделка по обращению \((\d+)\)',  # "сделка по обращению (301721445)"
            r'обращению \((\d+)\)',            # "обращению (301721445)"  
            r'дело №(\d+)',                    # "дело №301721445"
            r'\((\d{6,})\)',                   # Numbers in parentheses with 6+ digits
            r'№(\d{6,})',                      # Numbers after № with 6+ digits
        ]
        
        found_numbers = set()
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found_numbers.update(matches)
        
        return list(found_numbers)
    
    def validate_deal_id(self, deal_id):
        """
        Validate deal ID format
        
        Args:
            deal_id: ID to validate
            
        Returns:
            bool: True if valid
        """
        if deal_id is None:
            return False
            
        if isinstance(deal_id, str):
            return deal_id.isdigit() and len(deal_id) > 0
        elif isinstance(deal_id, int):
            return deal_id > 0
        else:
            return False
    
    def get_deal_dialogues(self, deal_id):
        """
        Get all dialogues associated with a deal using pagination with deduplication

        Args:
            deal_id: ID of the deal

        Returns:
            list: List of all message dictionaries (deduplicated)
        """
        messages = []
        seen_ids = set()
        start = 0
        page_count = 0
        
        while True:
            params = {
                'filter': {'ENTITY_ID': deal_id, 'ENTITY_TYPE': 'DEAL'},
                'select': ['ID', 'COMMENT', 'CREATED', 'AUTHOR_ID'],
                'start': start
            }
            batch = self.make_request('crm.timeline.comment.list', params)
            if not isinstance(batch, list) or not batch:
                break
                
            # Deduplicate messages by ID
            new_messages = []
            for msg in batch:
                msg_id = msg.get('ID')
                if msg_id and msg_id not in seen_ids:
                    seen_ids.add(msg_id)
                    new_messages.append(msg)
            
            if not new_messages:
                logging.debug(f"No new messages in page {page_count + 1}, stopping pagination")
                break
                
            messages.extend(new_messages)
            start += len(batch)
            page_count += 1
            
            # Safety limit to prevent infinite loops
            if page_count > 100:
                logging.warning(f"Reached pagination limit (100 pages) for deal {deal_id}")
                break
                
        logging.info(f"Retrieved {len(messages)} unique messages for deal {deal_id} in {page_count} pages")
        return messages
    
    def print_deal_details(self, deal):
        """Print formatted deal information"""
        print("\n=== Deal Details ===")
        print(f"ID: {deal.get('ID', 'N/A')}")
        print(f"Title: {deal.get('TITLE', 'N/A')}")
        print(f"Stage: {deal.get('STAGE_ID', 'N/A')}")
        print(f"Value: {deal.get('OPPORTUNITY', 'N/A')}")
        if 'DATE_CREATE' in deal:
            created = datetime.fromisoformat(deal['DATE_CREATE']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"Created: {created}")
        else:
            print("Created: N/A")
    
    def print_dialogues(self, messages):
        """Print formatted dialogue messages"""
        if not messages:
            print("\nNo dialogues found")
            return
            
        for msg in messages:
            try:
                date_str = msg.get('CREATED', '')
                date = datetime.fromisoformat(date_str).strftime('%Y-%m-%d %H:%M:%S') if date_str else 'N/A'
                author = msg.get('AUTHOR_ID', 'N/A')
                text = msg.get('COMMENT', 'No message text')
                
                # Skip video messages and system messages
                if '[url=' in text or '=== SYSTEM WZ ===' in text:
                    continue
                    
                # Remove [img] tags and &nbsp;
                text = text.replace('&nbsp;', '')
                text = re.sub(r'\[img\].*?\[\/img\]', '', text)
                
                print(f"[{date}] User {author}:")
                print(text.strip())
                
            except Exception as e:
                continue
    
    def log_api_stats(self):
        """Print API usage statistics"""
        if self.api_stats['start_time']:
            duration = datetime.now() - self.api_stats['start_time']
            print(f"\n=== API Statistics ===")
            print(f"Total requests: {self.api_stats['total_requests']}")
            print(f"Successful: {self.api_stats['successful_requests']}")
            print(f"Failed: {self.api_stats['failed_requests']}")
            print(f"Retry attempts: {self.api_stats['retry_attempts']}")
            print(f"Duration: {duration.total_seconds():.1f} seconds")
            if self.api_stats['total_requests'] > 0:
                success_rate = (self.api_stats['successful_requests'] / self.api_stats['total_requests']) * 100
                print(f"Success rate: {success_rate:.1f}%")
    
    def save_results_to_json(self, results, filename):
        """
        Save results to JSON file with metadata
        
        Args:
            results: Results data to save
            filename: Output filename
        """
        output_data = {
            'execution_info': {
                'timestamp': datetime.now().isoformat(),
                'api_stats': self.api_stats.copy(),
                'config': {
                    'rate_limit_delay': self.rate_limit_delay,
                    'request_timeout': self.request_timeout,
                    'max_retries': self.max_retries
                }
            },
            'results': results
        }
        
        if self.api_stats['start_time']:
            duration = datetime.now() - self.api_stats['start_time']
            output_data['execution_info']['duration_seconds'] = duration.total_seconds()
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
            logging.info(f"Results saved to {filename}")
            print(f"Results saved to {filename}")
        except Exception as e:
            logging.error(f"Failed to save results: {e}")
            print(f"Failed to save results: {e}")

def setup_logging(debug=False):
    """Setup logging configuration"""
    level = logging.DEBUG if debug else logging.INFO
    format_str = '%(asctime)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('bitrix_extractor.log', encoding='utf-8')
        ]
    )

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Bitrix24 Deal Extractor with advanced features')
    
    parser.add_argument('--deal-id', type=int, 
                       help='Specific deal ID to process (e.g., 301721445)')
    parser.add_argument('--find-number', type=int, 
                       help='Find deal by number in title (e.g., 301721445)')
    parser.add_argument('--find-all-numbers', action='store_true',
                       help='Find all deal numbers in message texts')
    parser.add_argument('--first-only', action='store_true',
                       help='Process only first deal (faster)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    parser.add_argument('--output', 
                       help='Save results to JSON file')
    parser.add_argument('--max-retries', type=int, default=5,
                       help='Maximum retry attempts (default: 5)')
    parser.add_argument('--rate-limit', type=float, default=0.5,
                       help='Delay between requests in seconds (default: 0.5)')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Request timeout in seconds (default: 30)')
    
    return parser.parse_args()

def main():
    """Main function with full command line support"""
    args = parse_arguments()
    
    # Setup logging
    setup_logging(args.debug)
    logging.info("Starting Bitrix24 Deal Extractor v2.0")
    
    # Initialize extractor with custom parameters
    WEBHOOK_URL = "https://b24-mwh5lj.bitrix24.ru/rest/1/zutp42hzvz9lyl8h/"
    extractor = Bitrix24DealExtractor(
        WEBHOOK_URL, 
        rate_limit_delay=args.rate_limit,
        request_timeout=args.timeout,
        max_retries=args.max_retries
    )
    
    results = {
        'mode': 'unknown',
        'deals': [],
        'total_deals': 0,
        'deals_with_dialogues': 0
    }
    
    try:
        # Different execution modes based on arguments
        if args.deal_id:
            # Mode: Specific deal by ID
            results['mode'] = 'specific_deal_by_id'
            logging.info(f"Processing specific deal ID: {args.deal_id}")
            
            deal = extractor.get_deal_by_id(args.deal_id)
            if deal:
                messages = extractor.get_deal_dialogues(deal['ID'])
                deal_result = {
                    'deal': deal,
                    'messages': messages,
                    'message_count': len(messages)
                }
                results['deals'] = [deal_result]
                results['total_deals'] = 1
                if messages:
                    results['deals_with_dialogues'] = 1
                
                extractor.print_deal_details(deal)
                extractor.print_dialogues(messages)
            else:
                print(f"Deal {args.deal_id} not found")
                
        elif args.find_number:
            # Mode: Find deals by number
            results['mode'] = 'find_by_number'
            logging.info(f"Searching for deals with number: {args.find_number}")
            
            found_deals = extractor.find_deals_by_number(args.find_number)
            results['total_deals'] = len(found_deals)
            
            for deal in found_deals:
                messages = extractor.get_deal_dialogues(deal['ID'])
                deal_result = {
                    'deal': deal,
                    'messages': messages,
                    'message_count': len(messages)
                }
                results['deals'].append(deal_result)
                if messages:
                    results['deals_with_dialogues'] += 1
                
                extractor.print_deal_details(deal)
                extractor.print_dialogues(messages)
                
        elif args.find_all_numbers:
            # Mode: Find deals by extracting numbers from messages
            results['mode'] = 'find_all_numbers_in_messages'
            logging.info("Searching for deal numbers in all message texts")
            
            # This is a more complex operation - get all deals first
            all_deals = extractor.get_all_deals()
            found_numbers = set()
            
            for deal in all_deals:
                messages = extractor.get_deal_dialogues(deal['ID'])
                for message in messages:
                    comment = message.get('COMMENT', '')
                    numbers = extractor.extract_deal_numbers_from_text(comment)
                    found_numbers.update(numbers)
            
            logging.info(f"Found {len(found_numbers)} unique numbers in messages: {list(found_numbers)}")
            print(f"Found numbers in messages: {sorted(found_numbers)}")
            
            # Now find deals for each number
            for number in found_numbers:
                found_deals = extractor.find_deals_by_number(number)
                for deal in found_deals:
                    messages = extractor.get_deal_dialogues(deal['ID'])
                    deal_result = {
                        'deal': deal,
                        'messages': messages,
                        'message_count': len(messages),
                        'found_via_number': number
                    }
                    results['deals'].append(deal_result)
                    results['total_deals'] += 1
                    if messages:
                        results['deals_with_dialogues'] += 1
                    
                    extractor.print_deal_details(deal)
                    extractor.print_dialogues(messages)
                    
        elif args.first_only:
            # Mode: Only first deal (fast mode)
            results['mode'] = 'first_deal_only'
            logging.info("Processing only first deal")
            
            first_deal = extractor.get_first_deal()
            if first_deal:
                messages = extractor.get_deal_dialogues(first_deal['ID'])
                deal_result = {
                    'deal': first_deal,
                    'messages': messages,
                    'message_count': len(messages)
                }
                results['deals'] = [deal_result]
                results['total_deals'] = 1
                if messages:
                    results['deals_with_dialogues'] = 1
                
                extractor.print_deal_details(first_deal)
                extractor.print_dialogues(messages)
            else:
                print("No deals found")
        else:
            # Default mode: All deals with dialogues
            results['mode'] = 'all_deals_with_dialogues'
            logging.info("Processing all deals with dialogues")
            
            deals = extractor.get_all_deals()
            if not deals:
                print("No deals found")
                return
            
            results['total_deals'] = len(deals)
            
            for deal in deals:
                try:
                    messages = extractor.get_deal_dialogues(deal['ID'])
                    if not messages:
                        continue  # Skip deals without dialogues
                    
                    deal_result = {
                        'deal': deal,
                        'messages': messages,
                        'message_count': len(messages)
                    }
                    results['deals'].append(deal_result)
                    results['deals_with_dialogues'] += 1
                    
                    extractor.print_deal_details(deal)
                    extractor.print_dialogues(messages)
                    
                except Exception as e:
                    logging.error(f"Error processing deal {deal['ID']}: {e}")
                    print(f"Skipping deal {deal['ID']} due to error: {e}")
                    continue
        
        # Print summary
        if results['deals_with_dialogues'] == 0:
            print("\nNo deals with dialogues found")
        else:
            print(f"\nFound {results['deals_with_dialogues']} deals with dialogues")
            
        # Save results to JSON if requested
        if args.output:
            extractor.save_results_to_json(results, args.output)
        
        # Print API statistics
        extractor.log_api_stats()
        
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        print("\nOperation interrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    main()
