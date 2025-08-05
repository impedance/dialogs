#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import re

class TestMessageProcessing(unittest.TestCase):
    def test_telegram_message_with_image(self):
        """Test processing of Telegram message with image link"""
        message = "[img]https://static.wazzup24.com/images/bitrix/telegram.png[/img]&nbsp;  Телефон: холо"
        
        # Extract platform and text
        platform = re.search(r'\[img\].*telegram\.png', message).group()
        text = message.split('&nbsp;')[-1].strip()
        
        self.assertIn('telegram.png', platform)
        self.assertEqual(text, "Телефон: холо")

    def test_system_wz_message_exclusion(self):
        """Test that SYSTEM WZ messages are excluded"""
        message1 = "[img]https://static.wazzup24.com/images/bitrix/telegram.png[/img]&nbsp;  Сделка по обращению в Telegram (7857271142): === SYSTEM WZ === Сообщение удалено. Посмотрите в чатах Wazzup, какое сообщение удалил клиент"
        message2 = "=== SYSTEM WZ === Some other system message"
        
        self.assertTrue("=== SYSTEM WZ ===" in message1)
        self.assertTrue("=== SYSTEM WZ ===" in message2)

    def test_telegram_message_with_english_text(self):
        """Test processing of Telegram message with English text"""
        message = "[img]https://static.wazzup24.com/images/bitrix/telegram.png[/img]&nbsp;  Телефон: hello"
        
        # Extract platform and text
        platform = re.search(r'\[img\].*telegram\.png', message).group()
        text = message.split('&nbsp;')[-1].strip()
        
        self.assertIn('telegram.png', platform)
        self.assertEqual(text, "Телефон: hello")

    def test_message_processing_flow(self):
        """Test complete message processing flow"""
        messages = [
            "[img]https://static.wazzup24.com/images/bitrix/telegram.png[/img]&nbsp;  Телефон: холо",
            "[img]https://static.wazzup24.com/images/bitrix/telegram.png[/img]&nbsp;  Сделка по обращению в Telegram (7857271142): === SYSTEM WZ === Сообщение удалено. Посмотрите в чатах Wazzup, какое сообщение удалил клиент",
            "[img]https://static.wazzup24.com/images/bitrix/telegram.png[/img]&nbsp;  Телефон: hello"
        ]
        
        processed = []
        for msg in messages:
            if "=== SYSTEM WZ ===" not in msg:
                # Extract platform and text
                platform = re.search(r'\[img\].*telegram\.png', msg).group()
                text = msg.split('&nbsp;')[-1].strip()
                processed.append((platform, text))
        
        self.assertEqual(len(processed), 2)
        self.assertEqual(processed[0][1], "Телефон: холо")
        self.assertEqual(processed[1][1], "Телефон: hello")

if __name__ == "__main__":
    unittest.main()
