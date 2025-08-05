#!/usr/bin/env python3
import requests
import json

webhook_url = 'https://b24-mwh5lj.bitrix24.ru/rest/1/vhbpg01ls83dn4rq/'

print('=== Поиск диалогов по разным ID ===')
possible_ids = ['1', '2', '3', '4', '5', '6', '7', '8', '10', '11', '12', 
                'chat1', 'chat2', 'chat3', 'chat4', 'chat6', 'chat7', 'chat8', 'chat9', 'chat10']

found_dialogs = []

for dialog_id in possible_ids:
    try:
        params = {'DIALOG_ID': dialog_id, 'LIMIT': 20}
        response = requests.post(f'{webhook_url}/im.dialog.messages.get', json=params)
        result = response.json()
        
        if 'result' in result and result['result'].get('messages'):
            messages = result['result']['messages']
            print(f'Диалог {dialog_id}: {len(messages)} сообщений')
            
            user_messages = []
            for msg in messages:
                text = msg.get('text', '')
                author_id = msg.get('author_id', 0)
                
                # Простая проверка на реальные сообщения
                if author_id != 0 and text.strip() and '[URL=' not in text:
                    user_messages.append(msg)
                    if 'тест' in text.lower() or 'тост' in text.lower():
                        print(f'*** НАЙДЕНО в диалоге {dialog_id}: {text}')
                        print(f'    Автор: {author_id}, Дата: {msg.get("date")}')
            
            if user_messages:
                print(f'  -> {len(user_messages)} пользовательских сообщений')
                found_dialogs.append(dialog_id)
                for i, msg in enumerate(user_messages[:3]):
                    print(f'     {i+1}. Автор {msg.get("author_id")}: {msg.get("text", "")[:60]}...')
            
    except Exception as e:
        pass

print(f'\nНайдены диалоги с реальными сообщениями: {found_dialogs}')