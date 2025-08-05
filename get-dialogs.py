#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для выгрузки всех диалогов из Битрикс24 через REST API
"""

import requests
import json
import time
from typing import List, Dict, Optional
from datetime import datetime
import csv
import re

class WazzupAPIClient:
    def __init__(self, api_key: str, base_url: str = "https://api.wazzup24.com/v3", disable_proxy: bool = True):
        """
        Клиент для работы с Wazzup API
        
        Args:
            api_key: API ключ для авторизации
            base_url: Базовый URL API (по умолчанию v3)
            disable_proxy: Отключить использование прокси
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        # Отключаем прокси если нужно
        if disable_proxy:
            self.session.proxies = {
                'http': None,
                'https': None,
            }
        
        # Устанавливаем заголовки
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'Bitrix24-Wazzup-Exporter/1.0'
        })
    
    def make_request(self, endpoint: str, method: str = 'GET', params: Dict = None, data: Dict = None) -> Dict:
        """
        Выполнение запроса к Wazzup API
        
        Args:
            endpoint: Эндпоинт API (без базового URL)
            method: HTTP метод (GET, POST, etc.)
            params: Параметры запроса (для GET)
            data: Данные для отправки (для POST/PUT)
        
        Returns:
            Ответ от API в виде словаря
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            print(f"🔗 Wazzup API: {method} {endpoint}")
            
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, timeout=30)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, params=params, timeout=30)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, params=params, timeout=30)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=params, timeout=30)
            else:
                raise ValueError(f"Неподдерживаемый HTTP метод: {method}")
            
            response.raise_for_status()
            
            # Проверяем, что ответ содержит JSON
            if response.headers.get('content-type', '').startswith('application/json'):
                result = response.json()
                print(f"✅ Запрос выполнен успешно")
                return result
            else:
                print(f"⚠️ Ответ не в формате JSON: {response.text[:200]}...")
                return {'text': response.text, 'status_code': response.status_code}
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка запроса к Wazzup API: {e}")
            return {'error': str(e)}
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            return {'error': f'JSON decode error: {e}', 'text': response.text[:500]}
    
    def get_contacts(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Получение списка контактов
        
        Args:
            limit: Количество контактов за запрос
            offset: Смещение для пагинации
            
        Returns:
            Список контактов
        """
        params = {
            'limit': limit,
            'offset': offset
        }
        
        result = self.make_request('contacts', params=params)
        
        if 'error' in result:
            return []
        
        # Структура ответа может отличаться, возвращаем весь результат для анализа
        return result.get('data', result) if isinstance(result, dict) else result
    
    def get_channels(self) -> List[Dict]:
        """
        Получение списка каналов (Telegram, WhatsApp и т.д.)
        
        Returns:
            Список каналов
        """
        result = self.make_request('channels')
        
        if 'error' in result:
            return []
            
        return result.get('data', result) if isinstance(result, dict) else result
    
    def get_deals(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Получение списка сделок
        
        Args:
            limit: Количество сделок за запрос
            offset: Смещение для пагинации
            
        Returns:
            Список сделок
        """
        params = {
            'limit': limit,
            'offset': offset
        }
        
        result = self.make_request('deals', params=params)
        
        if 'error' in result:
            return []
            
        return result.get('data', result) if isinstance(result, dict) else result
    
    def get_messages_for_contact(self, contact_id: str, limit: int = 100) -> List[Dict]:
        """
        Попытка получить сообщения для контакта
        Примечание: Wazzup API может не поддерживать прямое получение истории сообщений
        
        Args:
            contact_id: ID контакта
            limit: Лимит сообщений
            
        Returns:
            Список сообщений (если поддерживается)
        """
        # Пробуем разные возможные эндпоинты
        possible_endpoints = [
            f'contacts/{contact_id}/messages',
            f'messages/{contact_id}',
            f'dialogs/{contact_id}/messages',
            f'chats/{contact_id}/messages'
        ]
        
        for endpoint in possible_endpoints:
            print(f"🔍 Пробуем эндпоинт: {endpoint}")
            result = self.make_request(endpoint, params={'limit': limit})
            
            if 'error' not in result and result:
                print(f"✅ Найдены сообщения через: {endpoint}")
                return result.get('data', result) if isinstance(result, dict) else result
        
        print("❌ Не удалось найти рабочий эндпоинт для получения сообщений")
        return []
    
    def test_connection(self) -> bool:
        """
        Тестирование соединения с Wazzup API
        
        Returns:
            True если соединение успешно
        """
        print("🔍 Тестируем соединение с Wazzup API...")
        
        # Пробуем получить каналы - это базовый метод
        result = self.make_request('channels')
        
        if 'error' not in result:
            print("✅ Соединение с Wazzup API установлено")
            return True
        else:
            print(f"❌ Ошибка соединения с Wazzup API: {result.get('error')}")
            return False

class Bitrix24ChatExporter:
    def __init__(self, webhook_url: str, disable_proxy: bool = True, verify_ssl: bool = True):
        """
        Инициализация с URL вебхука
        
        Args:
            webhook_url: URL входящего вебхука (https://ваш_домен.bitrix24.ru/rest/user_id/webhook_code/)
            disable_proxy: Отключить использование прокси
            verify_ssl: Проверять SSL сертификаты
        """
        self.webhook_url = webhook_url.rstrip('/')
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        
        # Отключаем прокси если нужно
        if disable_proxy:
            self.session.proxies = {
                'http': None,
                'https': None,
            }
        
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Bitrix24ChatExporter/1.0'
        })
        
        # Отключаем предупреждения SSL если отключена верификация
        if not verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def make_request(self, method: str, params: Dict = None) -> Dict:
        """
        Выполнение запроса к API Битрикс24
        
        Args:
            method: Название метода API
            params: Параметры запроса
        
        Returns:
            Ответ от API
        """
        url = f"{self.webhook_url}/{method}"
        
        try:
            print(f"Выполняю запрос: {method}")
            
            if params:
                response = self.session.post(url, json=params, verify=self.verify_ssl, timeout=30)
            else:
                response = self.session.get(url, verify=self.verify_ssl, timeout=30)
            
            response.raise_for_status()
            result = response.json()
            
            if 'error' in result:
                print(f"Ошибка API: {result['error']} - {result.get('error_description', '')}")
                return {}
            
            print(f"Запрос выполнен успешно")
            return result
            
        except requests.exceptions.ProxyError as e:
            print(f"Ошибка прокси: {e}")
            print("Попробуйте отключить прокси или настроить его правильно")
            return {}
        except requests.exceptions.SSLError as e:
            print(f"Ошибка SSL: {e}")
            print("Попробуйте отключить проверку SSL сертификатов")
            return {}
        except requests.exceptions.Timeout as e:
            print(f"Таймаут запроса: {e}")
            return {}
        except requests.exceptions.RequestException as e:
            print(f"Ошибка запроса: {e}")
            return {}
        except json.JSONDecodeError as e:
            print(f"Ошибка разбора JSON: {e}")
            print(f"Ответ сервера: {response.text[:500]}")
            return {}
    
    def test_connection(self) -> bool:
        """
        Тестирование соединения с API
        
        Returns:
            True если соединение успешно
        """
        print("Тестирую соединение с Битрикс24...")
        
        # Пробуем простой запрос для проверки доступности API
        result = self.make_request('profile')  # Получение профиля текущего пользователя
        
        if result and 'result' in result:
            print("✅ Соединение успешно установлено")
            user_info = result['result']
            print(f"Пользователь: {user_info.get('NAME', '')} {user_info.get('LAST_NAME', '')}")
            return True
        else:
            print("❌ Не удалось установить соединение")
            return False
    
    def get_users_info(self) -> Dict:
        """
        Получение информации о пользователях
        
        Returns:
            Словарь с информацией о пользователях {user_id: user_data}
        """
        print("Получаю информацию о пользователях...")
        
        result = self.make_request('user.get')
        
        users_dict = {}
        if result and 'result' in result:
            users = result['result']
            for user in users:
                user_id = str(user.get('ID'))
                users_dict[user_id] = {
                    'ID': user.get('ID'),
                    'NAME': user.get('NAME', ''),
                    'LAST_NAME': user.get('LAST_NAME', ''),
                    'EMAIL': user.get('EMAIL', ''),
                    'WORK_POSITION': user.get('WORK_POSITION', ''),
                    'ACTIVE': user.get('ACTIVE', 'Y')
                }
            print(f"Найдено пользователей: {len(users_dict)}")
        
        return users_dict
    
    def get_all_dialogs(self, filter_messenger_only: bool = False) -> List[Dict]:
        """
        Получение всех диалогов с пагинацией
        
        Args:
            filter_messenger_only: Фильтровать только диалоги из мессенджеров (Wazzup)
        
        Returns:
            Список всех диалогов
        """
        print("Получение списка всех диалогов...")
        all_dialogs = []
        start = 0
        limit = 50  # Максимум 50 за запрос
        
        while True:
            print(f"Загружаю диалоги: start={start}")
            
            params = {
                'start': start,
            }
            
            result = self.make_request('im.recent.list', params)
            
            if not result or 'result' not in result:
                break
            
            dialogs = result['result'].get('items', [])
            
            if not dialogs:
                break
            
            # Фильтруем диалоги если нужно
            if filter_messenger_only:
                filtered_dialogs = []
                for dialog in dialogs:
                    if self.is_messenger_dialog(dialog):
                        filtered_dialogs.append(dialog)
                        print(f"✅ Найден мессенджер диалог: {dialog.get('title')}")
                    else:
                        print(f"❌ Пропускаю диалог: {dialog.get('title')} (тип: {dialog.get('type')})")
                dialogs = filtered_dialogs
            
            all_dialogs.extend(dialogs)
            print(f"Получено диалогов: {len(dialogs)}, всего: {len(all_dialogs)}")
            
            # Если получили меньше лимита, значит это последняя страница
            if len(dialogs) < limit:
                break
            
            start += limit
            time.sleep(0.5)  # Пауза между запросами
        
        print(f"Всего найдено диалогов: {len(all_dialogs)}")
        return all_dialogs
    
    def is_messenger_dialog(self, dialog: Dict) -> bool:
        """
        Проверяет, является ли диалог диалогом из мессенджера (Wazzup)
        
        Args:
            dialog: Данные диалога
        
        Returns:
            True если это диалог из мессенджера
        """
        # Проверяем тип диалога - мессенджеры обычно имеют тип "user"
        if dialog.get('type') != 'user':
            return False
        
        # Получаем информацию о пользователе
        user_info = dialog.get('user', {})
        
        # Проверяем, что это бот (мессенджер интеграция)
        if not user_info.get('bot', False):
            return False
        
        # Проверяем bot_data для определения Wazzup
        bot_data = user_info.get('bot_data', {})
        
        # Wazzup имеет специфический app_id
        wazzup_app_id = "app.5a8d2732b3d737.64069747"
        if bot_data.get('app_id') == wazzup_app_id:
            return True
        
        # Дополнительная проверка по work_position и названию
        work_position = user_info.get('work_position', '')
        name = user_info.get('name', '')
        
        # Wazzup обычно имеет work_position = "Чат-бот" и name = "Wazzup"
        if work_position == 'Чат-бот' and 'wazzup' in name.lower():
            return True
        
        return False
    
    def extract_wazzup_chat_ids_from_notifications(self) -> List[str]:
        """
        Извлекает ID чатов Wazzup из уведомлений
        
        Returns:
            Список ID чатов для получения реальных сообщений
        """
        print("Извлечение ID чатов Wazzup из уведомлений...")
        chat_ids = set()
        
        # Получаем все диалоги
        all_dialogs = self.get_all_dialogs(filter_messenger_only=False)
        
        for dialog in all_dialogs:
            dialog_id = dialog.get('id')
            
            # Получаем сообщения из диалога
            params = {'DIALOG_ID': dialog_id, 'LIMIT': 50}
            result = self.make_request('im.dialog.messages.get', params)
            
            if result and 'result' in result:
                messages = result['result'].get('messages', [])
                
                for msg in messages:
                    text = msg.get('text', '')
                    
                    # Ищем ссылки на Wazzup чаты в уведомлениях
                    if 'integrations.wazzup24.com/bitrix/chat/' in text:
                        import re
                        # Ищем ID в конце URL: /chat/hash/user_id/contact_id
                        pattern = r'integrations\.wazzup24\.com/bitrix/chat/[a-f0-9]+/\d+/(\d+)'
                        matches = re.findall(pattern, text)
                        for contact_id in matches:
                            chat_ids.add(contact_id)
                            print(f"Найден ID контакта: {contact_id}")
        
        print(f"Всего найдено уникальных ID контактов: {len(chat_ids)}")
        return list(chat_ids)
    
    def get_wazzup_dialog_messages(self, contact_id: str, limit: int = 100) -> List[Dict]:
        """
        Получение реальных сообщений из Wazzup диалога по ID контакта
        
        Args:
            contact_id: ID контакта из Wazzup
            limit: Лимит сообщений
        
        Returns:
            Список реальных сообщений пользователей
        """
        print(f"Получение сообщений для контакта {contact_id}...")
        
        # Попробуем разные варианты ID диалога для контакта
        possible_dialog_ids = [
            contact_id,  # Прямой ID
            f"chat{contact_id}",  # Chat + ID
            f"openline{contact_id}",  # Openline + ID
            f"ol{contact_id}",  # Openline короткий
        ]
        
        all_messages = []
        
        for dialog_id in possible_dialog_ids:
            params = {'DIALOG_ID': dialog_id, 'LIMIT': limit}
            result = self.make_request('im.dialog.messages.get', params)
            
            if result and 'result' in result:
                messages = result['result'].get('messages', [])
                if messages:
                    print(f"Найдены сообщения в диалоге {dialog_id}: {len(messages)}")
                    
                    # Показываем все сообщения для отладки
                    for i, msg in enumerate(messages, 1):
                        text = msg.get('text', '')
                        author_id = msg.get('author_id', 0)
                        print(f"  {i}. Автор {author_id}: {text[:100]}...")
                    
                    # Более мягкая фильтрация - включаем больше сообщений
                    user_messages = []
                    for msg in messages:
                        text = msg.get('text', '')
                        author_id = msg.get('author_id', 0)
                        
                        # Включаем все сообщения с текстом (исключаем только пустые)
                        if text.strip() and author_id != 0:
                            user_messages.append(msg)
                    
                    if user_messages:
                        print(f"Найдено {len(user_messages)} сообщений с содержимым")
                        all_messages.extend(user_messages)
                        break  # Нашли сообщения, не нужно проверять другие варианты
        
        return all_messages
    
    def get_dialog_messages(self, dialog_id: str, limit: int = 100, debug: bool = False) -> List[Dict]:
        """
        Получение всех сообщений из диалога
        
        Args:
            dialog_id: ID диалога
            limit: Количество сообщений за один запрос
            debug: Включить отладочную информацию
        
        Returns:
            Список сообщений
        """
        all_messages = []
        last_id = None
        
        while True:
            params = {
                'DIALOG_ID': dialog_id,
                'LIMIT': limit
            }
            
            if last_id:
                params['LAST_ID'] = last_id
            
            result = self.make_request('im.dialog.messages.get', params)
            
            if not result or 'result' not in result:
                break
            
            messages = result['result'].get('messages', [])
            
            if debug:
                print(f"Получено сообщений из API: {len(messages)}")
                if messages:
                    print("Первое сообщение (пример структуры):")
                    print(json.dumps(messages[0], indent=2, ensure_ascii=False))
            
            if not messages:
                break
            
            # Фильтруем сообщения: исключаем системные уведомления
            filtered_messages = []
            for msg in messages:
                text = msg.get('text', '')
                author_id = msg.get('author_id', 0)
                
                # Пропускаем сообщения от системы (author_id = 0)
                if author_id == 0:
                    if debug:
                        print(f"Пропускаю системное сообщение: {text[:100]}...")
                    continue
                
                # Пропускаем сообщения с URL-разметкой (технические уведомления)
                if '[URL=' in text and ']' in text:
                    if debug:
                        print(f"Пропускаю техническое уведомление: {text[:100]}...")
                    continue
                
                # Пропускаем сообщения со ссылками на CRM (могут быть автоматическими)
                if 'bitrix24.ru/crm/' in text:
                    if debug:
                        print(f"Пропускаю CRM уведомление: {text[:100]}...")
                    continue
                
                # Пропускаю сообщения с типовыми шаблонами уведомлений
                if any(phrase in text for phrase in [
                    'непрочитанных из', 
                    'Ответить в', 
                    'на канал',
                    'Сделка по обращению'
                ]):
                    if debug:
                        print(f"Пропускаю шаблонное уведомление: {text[:100]}...")
                    continue
                
                # Пропускаем пустые сообщения
                if not text.strip():
                    continue
                
                # Это выглядит как настоящее пользовательское сообщение
                if debug:
                    print(f"✅ Добавляю сообщение от пользователя {author_id}: {text[:50]}...")
                
                filtered_messages.append(msg)
            
            if debug:
                print(f"После фильтрации: {len(filtered_messages)} сообщений")
            
            all_messages.extend(filtered_messages)
            
            # Получаем ID последнего сообщения для следующего запроса
            if messages:
                last_id = min(msg['id'] for msg in messages)
            
            # Если получили меньше лимита, значит это все сообщения
            if len(messages) < limit:
                break
            
            time.sleep(0.3)  # Пауза между запросами
        
        return all_messages
    
    def export_all_dialogs(self, output_file: str = 'bitrix24_dialogs.json', 
                          include_messages: bool = True, max_messages_per_dialog: int = 1000,
                          messenger_only: bool = False):
        """
        Экспорт всех диалогов в файл
        
        Args:
            output_file: Имя файла для сохранения
            include_messages: Включать ли сообщения
            max_messages_per_dialog: Максимум сообщений на диалог
            messenger_only: Экспортировать только диалоги из мессенджеров (Wazzup)
        """
        # Получаем все диалоги
        dialogs = self.get_all_dialogs(filter_messenger_only=messenger_only)
        
        if not dialogs:
            print("Диалоги не найдены")
            return
        
        export_data = {
            'export_date': datetime.now().isoformat(),
            'total_dialogs': len(dialogs),
            'dialogs': []
        }
        
        for i, dialog in enumerate(dialogs, 1):
            print(f"\nОбрабатываю диалог {i}/{len(dialogs)}: {dialog.get('title', 'Без названия')}")
            
            dialog_data = {
                'id': dialog.get('id'),
                'type': dialog.get('type'),
                'title': dialog.get('title'),
                'avatar': dialog.get('avatar', {}).get('url'),
                'last_activity': dialog.get('date_last_activity'),
                'unread_count': dialog.get('counter'),
            }
            
            if include_messages:
                print(f"Загружаю сообщения для диалога: {dialog.get('id')}")
                messages = self.get_dialog_messages(dialog.get('id'), min(100, max_messages_per_dialog))
                dialog_data['messages'] = messages[:max_messages_per_dialog]
                dialog_data['messages_count'] = len(messages)
                print(f"Загружено сообщений: {len(messages)}")
            
            export_data['dialogs'].append(dialog_data)
        
        # Сохраняем в файл
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"\nЭкспорт завершен! Данные сохранены в: {output_file}")
        return export_data
    
    def export_to_csv(self, output_file: str = 'bitrix24_dialogs.csv', messenger_only: bool = False):
        """
        Экспорт диалогов в CSV (без сообщений)
        
        Args:
            output_file: Имя файла для сохранения
            messenger_only: Экспортировать только диалоги из мессенджеров (Wazzup)
        """
        dialogs = self.get_all_dialogs(filter_messenger_only=messenger_only)
        
        if not dialogs:
            print("Диалоги не найдены")
            return
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['id', 'type', 'title', 'last_activity', 'unread_count', 'avatar_url']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for dialog in dialogs:
                writer.writerow({
                    'id': dialog.get('id'),
                    'type': dialog.get('type'),
                    'title': dialog.get('title'),
                    'last_activity': dialog.get('date_last_activity'),
                    'unread_count': dialog.get('counter', 0),
                    'avatar_url': dialog.get('avatar', {}).get('url', '')
                })
        
        print(f"CSV экспорт завершен: {output_file}")

def debug_single_dialog():
    """Отладочная функция для анализа структуры сообщений"""
    WEBHOOK_URL = "https://b24-mwh5lj.bitrix24.ru/rest/1/vhbpg01ls83dn4rq/"
    
    print("=== Отладка структуры диалогов и сообщений ===\n")
    
    exporter = Bitrix24ChatExporter(WEBHOOK_URL, disable_proxy=True, verify_ssl=True)
    
    if not exporter.test_connection():
        print("❌ Не удалось подключиться к API")
        return
    
    # Получаем информацию о пользователях
    users_info = exporter.get_users_info()
    
    # НОВАЯ ЛОГИКА: Извлекаем ID чатов из уведомлений Wazzup
    print("\n=== Извлечение реальных чатов Wazzup ===")
    chat_ids = exporter.extract_wazzup_chat_ids_from_notifications()
    
    if not chat_ids:
        print("Не найдены ID чатов Wazzup")
        return
    
    print(f"Найдено ID чатов: {chat_ids}")
    
    # Получаем реальные сообщения для каждого чата
    all_real_messages = []
    chat_data = {}
    
    for chat_id in chat_ids:
        print(f"\n--- Проверяем чат {chat_id} ---")
        messages = exporter.get_wazzup_dialog_messages(chat_id, limit=50)
        
        if messages:
            all_real_messages.extend(messages)
            chat_data[chat_id] = {
                'total_messages': len(messages),
                'messages': messages
            }
            
            print(f"Примеры сообщений из чата {chat_id}:")
            for i, msg in enumerate(messages[:3], 1):
                text = msg.get('text', '')
                author_id = msg.get('author_id')
                print(f"  {i}. Автор {author_id}: {text[:80]}...")
                
                # Проверяем на 'тест' и 'тост'
                if 'тест' in text.lower() or 'тост' in text.lower():
                    print(f"  *** НАЙДЕНО 'тест/тост' в чате {chat_id}: {text}")
    
    print(f"\n=== ИТОГИ ===")
    print(f"Всего найдено реальных сообщений: {len(all_real_messages)}")
    print(f"Чатов с сообщениями: {len(chat_data)}")
    
    # Сохраняем результат в отладочный файл
    debug_data = {
        'total_chats': len(chat_ids),
        'chat_ids': chat_ids,
        'total_real_messages': len(all_real_messages),
        'chat_data': chat_data,
        'users_info': users_info
    }
    
    with open('bitrix24_dialogs_wazzup_debug.json', 'w', encoding='utf-8') as f:
        json.dump(debug_data, f, ensure_ascii=False, indent=2)
    
    print(f"Отладочные данные сохранены в: bitrix24_dialogs_wazzup_debug.json")

def find_messenger_messages():
    """Функция для поиска реальных сообщений из Telegram/WhatsApp"""
    WEBHOOK_URL = "https://b24-mwh5lj.bitrix24.ru/rest/1/vhbpg01ls83dn4rq/"
    
    print("=== Поиск сообщений из внешних мессенджеров ===\n")
    
    exporter = Bitrix24ChatExporter(WEBHOOK_URL, disable_proxy=True, verify_ssl=True)
    
    if not exporter.test_connection():
        print("❌ Не удалось подключиться к API")
        return
    
    # Получаем ВСЕ диалоги без фильтрации
    print("Получение всех диалогов...")
    all_dialogs = exporter.get_all_dialogs(filter_messenger_only=False)
    
    print(f"Найдено диалогов: {len(all_dialogs)}")
    
    # Детально изучаем каждый диалог
    messenger_messages = []
    
    for i, dialog in enumerate(all_dialogs, 1):
        dialog_id = dialog.get('id')
        dialog_title = dialog.get('title', 'Без названия')
        dialog_type = dialog.get('type')
        
        print(f"\n--- Диалог {i}: {dialog_title} (ID: {dialog_id}, тип: {dialog_type}) ---")
        
        # Показываем полную структуру диалога для понимания
        if 'user' in dialog:
            user_info = dialog['user']
            print(f"Пользователь: {user_info.get('name', 'N/A')}")
            print(f"Бот: {user_info.get('bot', False)}")
            if 'bot_data' in user_info and user_info['bot_data']:
                bot_data = user_info['bot_data']
                print(f"Bot App ID: {bot_data.get('app_id', 'N/A')}")
            elif user_info.get('bot', False):
                print("Bot App ID: N/A")
        
        # Получаем сообщения с полной отладкой
        messages = exporter.get_dialog_messages(dialog_id, limit=100, debug=True)
        
        if messages:
            print(f"Найдено сообщений после фильтрации: {len(messages)}")
            
            # Ищем сообщения, которые могут быть из внешних мессенджеров
            external_messages = []
            for msg in messages:
                text = msg.get('text', '')
                author_id = msg.get('author_id', 0)
                
                # Новая логика фильтрации для внешних сообщений
                if (text.strip() and 
                    author_id != 0 and  # Не системное
                    '[URL=' not in text and  # Не техническое уведомление
                    'bitrix24.ru' not in text and  # Не внутренняя ссылка
                    'Ответить в' not in text and  # Не шаблон
                    not text.startswith('Роль:') and  # Не внутренний промпт
                    'непрочитанных из' not in text):  # Не уведомление
                    
                    external_messages.append(msg)
                    print(f"  ✅ Внешнее сообщение от {author_id}: {text[:100]}...")
            
            if external_messages:
                messenger_messages.extend(external_messages)
                print(f"  Итого внешних сообщений в диалоге: {len(external_messages)}")
        else:
            print("  Сообщений не найдено")
    
    print(f"\n=== ФИНАЛЬНЫЕ ИТОГИ ===")
    print(f"Всего найдено внешних сообщений: {len(messenger_messages)}")
    
    # Группируем по авторам
    authors = {}
    for msg in messenger_messages:
        author_id = msg.get('author_id')
        if author_id not in authors:
            authors[author_id] = []
        authors[author_id].append(msg)
    
    print(f"Авторов: {len(authors)}")
    for author_id, msgs in authors.items():
        print(f"  Автор {author_id}: {len(msgs)} сообщений")
        for msg in msgs[:2]:  # Показываем первые 2 сообщения
            print(f"    - {msg.get('text', '')[:80]}...")
    
    # Сохраняем результат
    result_data = {
        'total_external_messages': len(messenger_messages),
        'authors_count': len(authors),
        'messages_by_author': authors,
        'all_messages': messenger_messages
    }
    
    with open('messenger_messages.json', 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nВнешние сообщения сохранены в: messenger_messages.json")

def extract_chat_links_and_try_access():
    """Извлекает ссылки на чаты Wazzup из уведомлений и пытается получить к ним доступ"""
    WEBHOOK_URL = "https://b24-mwh5lj.bitrix24.ru/rest/1/vhbpg01ls83dn4rq/"
    
    print("=== Извлечение ссылок на чаты Wazzup ===\n")
    
    exporter = Bitrix24ChatExporter(WEBHOOK_URL, disable_proxy=True, verify_ssl=True)
    
    if not exporter.test_connection():
        print("❌ Не удалось подключиться к API")
        return
    
    # Получаем все диалоги
    all_dialogs = exporter.get_all_dialogs(filter_messenger_only=False)
    
    chat_links = set()  # Для хранения уникальных ссылок
    contact_info = {}   # Информация о контактах
    
    print("Анализ уведомлений Wazzup...")
    
    for dialog in all_dialogs:
        dialog_id = dialog.get('id')
        
        # Получаем сообщения из диалога
        params = {'DIALOG_ID': dialog_id, 'LIMIT': 100}
        result = exporter.make_request('im.dialog.messages.get', params)
        
        if result and 'result' in result:
            messages = result['result'].get('messages', [])
            
            for msg in messages:
                text = msg.get('text', '')
                
                # Ищем ссылки на Wazzup чаты в уведомлениях
                if 'integrations.wazzup24.com/bitrix/chat/' in text:
                    import re
                    
                    # Извлекаем информацию о контакте
                    contact_pattern = r'\[URL=https://b24-mwh5lj\.bitrix24\.ru/crm/contact/details/(\d+)/\]([^[]+)\[/URL\]'
                    contact_matches = re.findall(contact_pattern, text)
                    
                    # Извлекаем информацию о платформе (Telegram/WhatsApp)
                    platform_pattern = r'Сделка по обращению в (Telegram|WhatsApp) \((\d+)\)'
                    platform_matches = re.findall(platform_pattern, text)
                    
                    # Извлекаем ссылку на чат
                    chat_pattern = r'Ответить в \[URL=(https://integrations\.wazzup24\.com/bitrix/chat/[^[]+)\]чате\[/URL\]'
                    chat_matches = re.findall(chat_pattern, text)
                    
                    if contact_matches and platform_matches and chat_matches:
                        contact_id, contact_name = contact_matches[0]
                        platform, user_id = platform_matches[0]
                        chat_url = chat_matches[0]
                        
                        chat_links.add(chat_url)
                        
                        if contact_id not in contact_info:
                            contact_info[contact_id] = {
                                'name': contact_name,
                                'platform': platform,
                                'user_id': user_id,
                                'chat_url': chat_url,
                                'message_count': 0
                            }
                        
                        # Извлекаем количество сообщений
                        count_pattern = r'(\d+) непрочитанн'
                        count_matches = re.findall(count_pattern, text)
                        if count_matches:
                            contact_info[contact_id]['message_count'] = int(count_matches[0])
                        
                        print(f"📱 {platform}: {contact_name} (ID: {contact_id})")
                        print(f"   User ID: {user_id}")
                        print(f"   Сообщений: {contact_info[contact_id]['message_count']}")
                        print(f"   Ссылка: {chat_url}")
                        print()
    
    print(f"\n=== РЕЗУЛЬТАТЫ ===")
    print(f"Найдено уникальных чатов: {len(chat_links)}")
    print(f"Контактов: {len(contact_info)}")
    
    # Группируем по платформам
    platforms = {}
    for contact_id, info in contact_info.items():
        platform = info['platform']
        if platform not in platforms:
            platforms[platform] = []
        platforms[platform].append(info)
    
    for platform, contacts in platforms.items():
        print(f"\n{platform}: {len(contacts)} контактов")
        total_messages = sum(c['message_count'] for c in contacts)
        print(f"Всего сообщений: {total_messages}")
    
    # Сохраняем данные
    export_data = {
        'total_chats': len(chat_links),
        'total_contacts': len(contact_info),
        'platforms': platforms,
        'contact_info': contact_info,
        'chat_links': list(chat_links)
    }
    
    with open('wazzup_chat_links.json', 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nДанные сохранены в: wazzup_chat_links.json")
    
    # Пытаемся получить доступ к чатам (это может не работать без авторизации)
    print(f"\n=== ПОПЫТКА ДОСТУПА К ЧАТАМ ===")
    print("⚠️  Внимание: доступ к чатам может требовать авторизации Wazzup")
    
    chat_content = {}
    
    for i, chat_url in enumerate(list(chat_links)[:3], 1):  # Проверяем первые 3
        print(f"\n{i}. Попытка доступа к: {chat_url}")
        try:
            import requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(chat_url, timeout=30, headers=headers)
            print(f"   Статус: {response.status_code}")
            
            if response.status_code == 200:
                content = response.text
                print(f"   Размер ответа: {len(content)} символов")
                
                # Сохраняем содержимое для анализа
                filename = f"chat_content_{i}.html"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"   Содержимое сохранено в: {filename}")
                
                # Анализируем содержимое
                content_lower = content.lower()
                
                # Ищем ключевые слова
                keywords = ['message', 'chat', 'telegram', 'whatsapp', 'сообщение', 'диалог']
                found_keywords = [kw for kw in keywords if kw in content_lower]
                print(f"   Найденные ключевые слова: {found_keywords}")
                
                # Ищем JavaScript API или данные
                if 'api' in content_lower and ('message' in content_lower or 'chat' in content_lower):
                    print("   ✅ Возможно, содержит API для чата")
                
                # Ищем фреймы или iframe
                if 'iframe' in content_lower:
                    print("   📱 Содержит iframe")
                
                # Ищем данные JSON
                import re
                json_patterns = re.findall(r'({[^{}]*"[^"]*"[^{}]*})', content)
                if json_patterns:
                    print(f"   📋 Найдено JSON объектов: {len(json_patterns)}")
                    
                    # Анализируем первые несколько JSON объектов
                    for j, json_str in enumerate(json_patterns[:3], 1):
                        if 'message' in json_str.lower() or 'text' in json_str.lower():
                            print(f"   🎯 JSON {j} может содержать сообщения: {json_str[:100]}...")
                
                chat_content[chat_url] = {
                    'size': len(content),
                    'keywords': found_keywords,
                    'has_json': len(json_patterns),
                    'content_sample': content[:500] + '...' if len(content) > 500 else content
                }
                
            else:
                print(f"   ❌ Доступ запрещен (код: {response.status_code})")
                
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    # Сохраняем анализ содержимого чатов
    if chat_content:
        with open('chat_content_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(chat_content, f, ensure_ascii=False, indent=2)
        print(f"\nАнализ содержимого чатов сохранен в: chat_content_analysis.json")
    
    return export_data

def get_messages_with_wazzup_api(wazzup_api_key: str):
    """Получение сообщений через Wazzup API с интеграцией с Bitrix24"""
    WEBHOOK_URL = "https://b24-mwh5lj.bitrix24.ru/rest/1/vhbpg01ls83dn4rq/"
    
    print("=== Получение сообщений через Wazzup API ===\n")
    
    # Инициализируем клиенты
    wazzup_client = WazzupAPIClient(wazzup_api_key)
    bitrix_exporter = Bitrix24ChatExporter(WEBHOOK_URL, disable_proxy=True, verify_ssl=True)
    
    # Тестируем соединения
    print("1. Тестирование соединений...")
    wazzup_ok = wazzup_client.test_connection()
    bitrix_ok = bitrix_exporter.test_connection()
    
    if not wazzup_ok:
        print("❌ Не удалось подключиться к Wazzup API")
        return
    
    if not bitrix_ok:
        print("❌ Не удалось подключиться к Bitrix24 API")
        return
    
    print("\n2. Получение данных из Wazzup API...")
    
    # Получаем каналы
    print("\n📡 Получение каналов...")
    channels = wazzup_client.get_channels()
    print(f"Найдено каналов: {len(channels) if isinstance(channels, list) else 'N/A'}")
    
    if channels:
        print("Каналы:")
        for i, channel in enumerate(channels[:3] if isinstance(channels, list) else [channels], 1):
            if isinstance(channel, dict):
                name = channel.get('name', channel.get('title', 'N/A'))
                channel_type = channel.get('type', channel.get('platform', 'N/A'))
                print(f"  {i}. {name} ({channel_type})")
    
    # Получаем контакты
    print("\n👥 Получение контактов...")
    contacts = wazzup_client.get_contacts(limit=50)
    print(f"Найдено контактов: {len(contacts) if isinstance(contacts, list) else 'N/A'}")
    
    if contacts:
        print("Первые 5 контактов:")
        for i, contact in enumerate(contacts[:5] if isinstance(contacts, list) else [contacts], 1):
            if isinstance(contact, dict):
                name = contact.get('name', contact.get('chatName', contact.get('phone', 'N/A')))
                platform = contact.get('transport', contact.get('channel', 'N/A'))
                contact_id = contact.get('chatId', contact.get('id', 'N/A'))
                print(f"  {i}. {name} | {platform} | ID: {contact_id}")
    
    # Получаем сделки
    print("\n💼 Получение сделок...")
    deals = wazzup_client.get_deals(limit=20)
    print(f"Найдено сделок: {len(deals) if isinstance(deals, list) else 'N/A'}")
    
    if deals:
        print("Первые 3 сделки:")
        for i, deal in enumerate(deals[:3] if isinstance(deals, list) else [deals], 1):
            if isinstance(deal, dict):
                name = deal.get('name', deal.get('title', 'N/A'))
                status = deal.get('status', deal.get('state', 'N/A'))
                contact_name = deal.get('contact', {}).get('name', 'N/A') if isinstance(deal.get('contact'), dict) else 'N/A'
                print(f"  {i}. {name} | Статус: {status} | Контакт: {contact_name}")
    
    print("\n3. Получение информации из Bitrix24 для сопоставления...")
    
    # Получаем информацию о контактах из уведомлений Bitrix24
    chat_links_data = extract_chat_links_and_try_access()
    bitrix_contacts = chat_links_data.get('contact_info', {}) if chat_links_data else {}
    
    print(f"\nНайдено контактов в Bitrix24 уведомлениях: {len(bitrix_contacts)}")
    
    # Пытаемся сопоставить контакты и получить сообщения
    print("\n4. Попытка получения сообщений...")
    
    all_messages = []
    successful_contacts = []
    
    if isinstance(contacts, list):
        for contact in contacts[:10]:  # Ограничиваем для тестирования
            if not isinstance(contact, dict):
                continue
                
            contact_id = contact.get('chatId', contact.get('id', contact.get('contactId')))
            contact_name = contact.get('name', contact.get('chatName', contact.get('phone', 'Unknown')))
            
            if contact_id:
                print(f"\n🔍 Пытаемся получить сообщения для: {contact_name} (ID: {contact_id})")
                messages = wazzup_client.get_messages_for_contact(str(contact_id))
                
                if messages:
                    print(f"✅ Найдено сообщений: {len(messages)}")
                    all_messages.extend(messages)
                    successful_contacts.append({
                        'id': contact_id,
                        'name': contact_name,
                        'messages_count': len(messages),
                        'contact_data': contact,
                        'messages': messages
                    })
                else:
                    print(f"❌ Сообщения не найдены")
    
    # Сохраняем результаты
    results = {
        'wazzup_data': {
            'channels': channels,
            'contacts': contacts,
            'deals': deals,
            'total_contacts': len(contacts) if isinstance(contacts, list) else 0,
            'total_channels': len(channels) if isinstance(channels, list) else 0,
            'total_deals': len(deals) if isinstance(deals, list) else 0
        },
        'bitrix_data': {
            'contact_info': bitrix_contacts,
            'total_bitrix_contacts': len(bitrix_contacts)
        },
        'messages': {
            'successful_contacts': successful_contacts,
            'total_messages': len(all_messages),
            'all_messages': all_messages
        },
        'summary': {
            'contacts_with_messages': len(successful_contacts),
            'total_messages_retrieved': len(all_messages),
            'export_timestamp': datetime.now().isoformat()
        }
    }
    
    # Сохраняем в файл
    output_file = 'wazzup_api_export.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== ИТОГОВЫЕ РЕЗУЛЬТАТЫ ===")
    print(f"📊 Каналов в Wazzup: {results['wazzup_data']['total_channels']}")
    print(f"👥 Контактов в Wazzup: {results['wazzup_data']['total_contacts']}")
    print(f"💼 Сделок в Wazzup: {results['wazzup_data']['total_deals']}")
    print(f"📱 Контактов в Bitrix24: {results['bitrix_data']['total_bitrix_contacts']}")
    print(f"✅ Контактов с сообщениями: {results['summary']['contacts_with_messages']}")
    print(f"💬 Всего получено сообщений: {results['summary']['total_messages_retrieved']}")
    print(f"\n📁 Результаты сохранены в: {output_file}")
    
    return results

def main():
    # Настройки
    WEBHOOK_URL = "https://b24-mwh5lj.bitrix24.ru/rest/1/vhbpg01ls83dn4rq/"
    
    print("=== Экспорт диалогов Битрикс24 ===\n")
    
    # Создаем экспортер с отключенным прокси
    exporter = Bitrix24ChatExporter(
        WEBHOOK_URL, 
        disable_proxy=True,    # Отключаем прокси
        verify_ssl=True        # Можно поставить False если проблемы с SSL
    )
    
    # Тестируем соединение
    if not exporter.test_connection():
        print("\n❌ Не удалось подключиться к API Битрикс24")
        print("\nВозможные причины:")
        print("1. Неверный URL вебхука")
        print("2. Веб-хук не активен или удален")
        print("3. Недостаточно прав доступа (нужны права 'im' и 'user')")
        print("4. Проблемы с интернет-соединением")
        print("5. Блокировка файрволом или антивирусом")
        print("\nПопробуйте:")
        print("- Проверить URL вебхука")
        print("- Пересоздать вебхук с правами 'im' и 'user'")
        print("- Отключить антивирус/файрвол временно")
        print("- Использовать verify_ssl=False если проблемы с сертификатами")
        return
    
    print("\n" + "="*50)
    
    # Экспорт в JSON с сообщениями (первые 100 сообщений каждого диалога)
    exporter.export_all_dialogs(
        output_file='bitrix24_dialogs_full.json',
        include_messages=True,
        max_messages_per_dialog=100,
        messenger_only=True  # Только мессенджеры
    )
    
    # Экспорт только списка диалогов в CSV
    exporter.export_to_csv('bitrix24_dialogs_list.csv', messenger_only=True)
    
    print("\n=== Экспорт завершен ===")


def test_connection_only():
    """Функция только для тестирования соединения"""
    WEBHOOK_URL = "https://b24-mwh5lj.bitrix24.ru/rest/1/vhbpg01ls83dn4rq/"
    
    print("=== Тест соединения с Битрикс24 ===\n")
    
    # Тест с прокси
    print("1. Тест с системными настройками прокси:")
    exporter1 = Bitrix24ChatExporter(WEBHOOK_URL, disable_proxy=False, verify_ssl=True)
    success1 = exporter1.test_connection()
    
    if not success1:
        print("\n2. Тест без прокси:")
        exporter2 = Bitrix24ChatExporter(WEBHOOK_URL, disable_proxy=True, verify_ssl=True)
        success2 = exporter2.test_connection()
        
        if not success2:
            print("\n3. Тест без прокси и без проверки SSL:")
            exporter3 = Bitrix24ChatExporter(WEBHOOK_URL, disable_proxy=True, verify_ssl=False)
            success3 = exporter3.test_connection()
            
            if success3:
                print("✅ Рекомендуется использовать: disable_proxy=True, verify_ssl=False")
            else:
                print("❌ Все варианты подключения не сработали")
        else:
            print("✅ Рекомендуется использовать: disable_proxy=True, verify_ssl=True")
    else:
        print("✅ Подключение работает с системными настройками")

if __name__ == "__main__":
    import sys
    
    # Если передан аргумент "test", запускаем только тестирование
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_connection_only()
    elif len(sys.argv) > 1 and sys.argv[1] == "debug":
        debug_single_dialog()
    elif len(sys.argv) > 1 and sys.argv[1] == "messenger":
        find_messenger_messages()
    elif len(sys.argv) > 1 and sys.argv[1] == "links":
        extract_chat_links_and_try_access()
    elif len(sys.argv) > 1 and sys.argv[1] == "wazzup":
        # Для работы с Wazzup API требуется передать API ключ
        if len(sys.argv) > 2:
            api_key = sys.argv[2]
            get_messages_with_wazzup_api(api_key)
        else:
            print("❌ Необходимо передать API ключ Wazzup:")
            print("   python3 get-dialogs.py wazzup YOUR_API_KEY")
            print("\nГде получить API ключ:")
            print("1. Войдите в ваш аккаунт Wazzup24")
            print("2. Перейдите в Настройки → API")
            print("3. Скопируйте ваш API ключ")
    else:
        main()