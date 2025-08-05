Generated diff
diff --git a/get_first_deal.py b/get_first_deal.py
index a535f2a..1b901a8 100644
--- a/get_first_deal.py
+++ b/get_first_deal.py
@@ -1,7 +1,9 @@
 #!/usr/bin/env python3
 import requests
 import json
+import re
 from datetime import datetime
+from typing import Optional
 
 class Bitrix24DealExtractor:
     def __init__(self, webhook_url, disable_proxy=True, verify_ssl=True):
@@ -95,6 +97,22 @@
         result = self.make_request('crm.timeline.comment.list', params)
         return result if isinstance(result, list) else []
     
+    def _clean_and_filter_comment(self, text: str) -> Optional[str]:
+        """
+        Filters out system messages and cleans BBCode-like tags from comments.
+
+        Args:
+            text: The raw comment text.
+
+        Returns:
+            The cleaned comment text, or None if the message should be filtered out.
+        """
+        if not text or "=== SYSTEM WZ ===" in text:
+            return None
+        
+        # Remove [img]...[/img] tags and the subsequent &nbsp;
+        cleaned_text = re.sub(r'\[img\].*?\[/img\]&nbsp;\s*', '', text)
+        return cleaned_text.strip()
+
     def print_deal_details(self, deal):
         """Print formatted deal information"""
         print("\n=== Deal Details ===")
@@ -115,13 +133,14 @@
         print("\n=== Associated Dialogues ===")
         for msg in messages:
             try:
-                date_str = msg.get('CREATED', '')
-                date = datetime.fromisoformat(date_str).strftime('%Y-%m-%d %H:%M:%S') if date_str else 'N/A'
-                author = msg.get('AUTHOR_ID', 'N/A')
-                text = msg.get('COMMENT', 'No message text')
-                print(f"[{date}] User {author}:")
-                print(text)
-                print()
+                raw_text = msg.get('COMMENT', '')
+                cleaned_text = self._clean_and_filter_comment(raw_text)
+
+                if cleaned_text:
+                    date_str = msg.get('CREATED', '')
+                    date = datetime.fromisoformat(date_str).strftime('%Y-%m-%d %H:%M:%S') if date_str else 'N/A'
+                    author = msg.get('AUTHOR_ID', 'N/A')
+                    print(f"[{date}] User {author}:")
+                    print(cleaned_text)
+                    print()
             except Exception as e:
                 print(f"Error formatting message: {e}")
                 continue
diff --git a/test_get_first_deal.py b/test_get_first_deal.py
new file mode 100644
index 0000000..8a07f6f
--- /dev/null
+++ b/test_get_first_deal.py
@@ -0,0 +1,61 @@
+import unittest
+from unittest.mock import patch, MagicMock
+import io
+from contextlib import redirect_stdout
+
+from get_first_deal import Bitrix24DealExtractor
+
+class TestBitrix24DealExtractor(unittest.TestCase):
+
+    def setUp(self):
+        self.webhook_url = "https://fake.bitrix24.ru/rest/1/fake_token/"
+        self.extractor = Bitrix24DealExtractor(self.webhook_url)
+        self.mock_deal = {
+            'ID': '123', 'TITLE': 'Test Deal', 'STAGE_ID': 'NEW', 'OPPORTUNITY': '5000',
+            'DATE_CREATE': '2023-10-27T10:00:00+03:00'
+        }
+        self.mock_messages = [
+            {'COMMENT': '[img]https://example.com/a.png[/img]&nbsp;  Hello world', 'CREATED': '2023-10-27T10:05:00+03:00', 'AUTHOR_ID': '1'},
+            {'COMMENT': 'This is a clean message.', 'CREATED': '2023-10-27T10:06:00+03:00', 'AUTHOR_ID': '2'},
+            {'COMMENT': 'Another message with system alert: === SYSTEM WZ === This should be filtered.', 'CREATED': '2023-10-27T10:07:00+03:00', 'AUTHOR_ID': '1'},
+            {'COMMENT': '', 'CREATED': '2023-10-27T10:08:00+03:00', 'AUTHOR_ID': '3'},
+        ]
+
+    @patch('get_first_deal.requests.Session.post')
+    def test_get_first_deal(self, mock_post):
+        mock_response = MagicMock()
+        mock_response.json.return_value = {'result': [self.mock_deal]}
+        mock_post.return_value = mock_response
+
+        deal = self.extractor.get_first_deal()
+        self.assertEqual(deal, self.mock_deal)
+
+    @patch('get_first_deal.requests.Session.post')
+    def test_get_deal_dialogues(self, mock_post):
+        mock_response = MagicMock()
+        mock_response.json.return_value = {'result': self.mock_messages}
+        mock_post.return_value = mock_response
+
+        messages = self.extractor.get_deal_dialogues('123')
+        self.assertEqual(messages, self.mock_messages)
+
+    def test_clean_and_filter_comment(self):
+        system_message = "Some text with === SYSTEM WZ ==="
+        self.assertIsNone(self.extractor._clean_and_filter_comment(system_message))
+
+        bbcode_message = "[img]some_url.png[/img]&nbsp;  This is the actual message."
+        expected_clean = "This is the actual message."
+        self.assertEqual(self.extractor._clean_and_filter_comment(bbcode_message), expected_clean)
+
+        clean_message = "A perfectly normal message."
+        self.assertEqual(self.extractor._clean_and_filter_comment(clean_message), clean_message)
+
+        self.assertIsNone(self.extractor._clean_and_filter_comment(""))
+
+    def test_print_dialogues_output(self):
+        f = io.StringIO()
+        with redirect_stdout(f):
+            self.extractor.print_dialogues(self.mock_messages)
+        output = f.getvalue()
+
+        self.assertIn("Hello world", output)
+        self.assertIn("This is a clean message.", output)
+        self.assertNotIn("=== SYSTEM WZ ===", output)
+        self.assertNotIn("[img]", output)
+        self.assertNotIn("&nbsp;", output)
+
+if __name__ == '__main__':
+    unittest.main()
