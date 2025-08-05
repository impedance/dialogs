#!/usr/bin/env python3
import requests
import json
import re
from datetime import datetime
from typing import Optional

class Bitrix24DealExtractor:
    def __init__(self, webhook_url, disable_proxy=True, verify_ssl=True):
        """
        Initialize Bitrix24 API client
        
        Args:
            webhook_url: Bitrix24 REST API webhook URL
            disable_proxy: Disable system proxies if True
            verify_ssl: Verify SSL certificates if True
        """
        self.webhook_url = webhook_url.rstrip('/')
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        
        if disable_proxy:
            self.session.proxies = {'http': None, 'https': None}
            
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Bitrix24DealExtractor/1.0'
        })
        
        if not verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def make_request(self, method, params=None):
        """
        Make API request to Bitrix24
        
        Args:
            method: API method name
            params: Request parameters
            
        Returns:
            dict: API response or empty dict on error
        """
        url = f"{self.webhook_url}/{method}"
        try:
            response = self.session.post(url, json=params, verify=self.verify_ssl, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result.get('result', {}) if 'error' not in result else {}
        except Exception as e:
            print(f"API request failed: {e}")
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
    
    def get_deal_dialogues(self, deal_id):
        """
        Get dialogues associated with a deal
        
        Args:
            deal_id: ID of the deal
            
        Returns:
            list: List of message dictionaries
        """
        params = {
            'filter': {'ENTITY_ID': deal_id, 'ENTITY_TYPE': 'DEAL'},
            'select': ['COMMENT', 'CREATED', 'AUTHOR_ID']
        }
        result = self.make_request('crm.timeline.comment.list', params)
        return result if isinstance(result, list) else []
    
    def _clean_and_filter_comment(self, text: str) -> Optional[str]:
        """
        Filters out system messages and cleans BBCode-like tags from comments.

        Args:
            text: The raw comment text.

        Returns:
            The cleaned comment text, or None if the message should be filtered out.
        """
        if not text or "=== SYSTEM WZ ===" in text:
            return None
        
        # Remove [img]...[/img] tags and the subsequent &nbsp;
        cleaned_text = re.sub(r'\[img\].*?\[/img\]&nbsp;\s*', '', text)
        return cleaned_text.strip()
    
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
            
        print("\n=== Associated Dialogues ===")
        for msg in messages:
            try:
                raw_text = msg.get('COMMENT', '')
                cleaned_text = self._clean_and_filter_comment(raw_text)

                if cleaned_text:
                    date_str = msg.get('CREATED', '')
                    date = datetime.fromisoformat(date_str).strftime('%Y-%m-%d %H:%M:%S') if date_str else 'N/A'
                    author = msg.get('AUTHOR_ID', 'N/A')
                    print(f"[{date}] User {author}:")
                    print(cleaned_text)
                    print()
            except Exception as e:
                print(f"Error formatting message: {e}")
                continue

def main():
    WEBHOOK_URL = "https://b24-mwh5lj.bitrix24.ru/rest/1/zutp42hzvz9lyl8h/"
    extractor = Bitrix24DealExtractor(WEBHOOK_URL)
    
    deal = extractor.get_first_deal()
    if deal:
        extractor.print_deal_details(deal)
        messages = extractor.get_deal_dialogues(deal['ID'])
        extractor.print_dialogues(messages)

if __name__ == "__main__":
    main()
