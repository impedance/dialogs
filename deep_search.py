#!/usr/bin/env python3
import requests
import json

webhook_url = 'https://b24-mwh5lj.bitrix24.ru/rest/1/vhbpg01ls83dn4rq/'

print('=== Глубокий поиск сообщений "тест" и "тост" ===')

# ID чатов которые мы нашли
chat_ids = ['1', '3', '5', '7', '9', '11']

def get_all_messages_from_dialog(dialog_id, max_pages=20):
    all_messages = []
    last_id = None
    
    for page in range(max_pages):
        params = {'DIALOG_ID': dialog_id, 'LIMIT': 50}
        if last_id:
            params['LAST_ID'] = last_id
            
        try:
            response = requests.post(f'{webhook_url}/im.dialog.messages.get', json=params)
            if response.status_code != 200:
                break
                
            result = response.json()
            if 'result' not in result or not result['result'].get('messages'):
                break
                
            messages = result['result']['messages']
            all_messages.extend(messages)
            
            if len(messages) < 50:  # Последняя страница
                break
                
            last_id = min(msg['id'] for msg in messages)
        except:
            break
    
    return all_messages

for chat_id in chat_ids:
    print(f'\n--- Глубокий поиск в диалоге {chat_id} ---')
    
    # Пробуем разные варианты ID
    for dialog_id in [chat_id, f'chat{chat_id}']:
        try:
            messages = get_all_messages_from_dialog(dialog_id)
            if messages:
                print(f'Диалог {dialog_id}: найдено {len(messages)} сообщений')
                
                # Ищем тест и тост
                found_messages = []
                for msg in messages:
                    text = msg.get('text', '').lower()
                    if 'тест' in text or 'тост' in text:
                        found_messages.append(msg)
                
                if found_messages:
                    print(f'*** НАЙДЕНО {len(found_messages)} сообщений с "тест/тост":')
                    for msg in found_messages:
                        print(f'    - Автор {msg.get("author_id")}: "{msg.get("text", "")}"')
                        print(f'      Дата: {msg.get("date")}')
                
                # Показываем несколько примеров реальных сообщений
                real_messages = []
                for msg in messages:
                    text = msg.get('text', '')
                    author_id = msg.get('author_id', 0)
                    if (author_id != 0 and text.strip() and 
                        '[URL=' not in text and 
                        'непрочитанных из' not in text):
                        real_messages.append(msg)
                
                if real_messages:
                    print(f'  Найдено {len(real_messages)} реальных сообщений. Примеры:')
                    for i, msg in enumerate(real_messages[:3]):
                        print(f'    {i+1}. {msg.get("text", "")[:60]}...')
                
                break  # Нашли сообщения, переходим к следующему чату
        except:
            continue

print('\n=== Поиск завершен ===')