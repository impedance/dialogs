# Bitrix24 Deal Extractor v2.0

Улучшенный экстрактор сделок из Bitrix24 с поддержкой retry механизма, rate limiting и расширенными возможностями поиска.

## 🚀 Новые возможности

### ✅ Решенные проблемы:
- **503 ошибки**: Автоматические повторные попытки с экспоненциальной задержкой
- **Перегрузка API**: Rate limiting с настраиваемыми задержками  
- **Конкретные сделки**: Поиск по ID и номеру в тексте сообщений
- **Отладка**: Детальное логирование и статистика API

### 🔧 Технические улучшения:
- Retry механизм для 500, 502, 503, 504 ошибок
- Экспоненциальная задержка: 1s, 2s, 4s, 8s, 16s
- Rate limiting: настраиваемые задержки между запросами
- JSON export с метаданными
- Статистика производительности

## 📋 Режимы работы

### 1. Конкретная сделка по ID
```bash
python3 get_first_deal.py --deal-id 301721445
```

### 2. Поиск сделки по номеру в названии
```bash
python3 get_first_deal.py --find-number 301721445
```

### 3. Поиск всех номеров в сообщениях
```bash
python3 get_first_deal.py --find-all-numbers
```

### 4. Только первая сделка (быстрый режим)
```bash
python3 get_first_deal.py --first-only
```

### 5. Все сделки с диалогами (по умолчанию)
```bash
python3 get_first_deal.py
```

## 🛠️ Дополнительные параметры

### Отладка и логирование
```bash
# Включить детальное логирование
python3 get_first_deal.py --debug

# Сохранить результаты в JSON
python3 get_first_deal.py --output results.json

# И то и другое
python3 get_first_deal.py --deal-id 301721445 --debug --output deal_301721445.json
```

### Настройка производительности
```bash
# Увеличить количество повторов
python3 get_first_deal.py --max-retries 10

# Уменьшить задержку между запросами (осторожно!)
python3 get_first_deal.py --rate-limit 0.2

# Увеличить таймаут запросов
python3 get_first_deal.py --timeout 60
```

### Комбинированный пример
```bash
python3 get_first_deal.py \
  --deal-id 301721445 \
  --debug \
  --output deal_details.json \
  --max-retries 10 \
  --rate-limit 1.0 \
  --timeout 45
```

## 📊 Структура JSON вывода

```json
{
  "execution_info": {
    "timestamp": "2025-08-07T12:00:00+03:00",
    "duration_seconds": 45.2,
    "api_stats": {
      "total_requests": 15,
      "successful_requests": 13,
      "failed_requests": 2,
      "retry_attempts": 5
    },
    "config": {
      "rate_limit_delay": 0.5,
      "request_timeout": 30,
      "max_retries": 5
    }
  },
  "results": {
    "mode": "specific_deal_by_id",
    "total_deals": 1,
    "deals_with_dialogues": 1,
    "deals": [
      {
        "deal": {
          "ID": "301721445",
          "TITLE": "Сделка по обращению (301721445)",
          "STAGE_ID": "C19:NEW",
          "OPPORTUNITY": "10000",
          "DATE_CREATE": "2025-08-01T10:00:00+03:00"
        },
        "messages": [...],
        "message_count": 15
      }
    ]
  }
}
```

## 📝 Логирование

Создается файл `bitrix_extractor.log` с детальной информацией:

```
2025-08-07 12:00:01,234 - INFO - Starting Bitrix24 Deal Extractor v2.0
2025-08-07 12:00:01,456 - INFO - Processing specific deal ID: 301721445
2025-08-07 12:00:01,789 - INFO - Rate limiting delay: 0.50s before crm.deal.get
2025-08-07 12:00:02,123 - INFO - API Request #1: crm.deal.get (attempt 1/6)
2025-08-07 12:00:02,456 - INFO - API Request successful: crm.deal.get
2025-08-07 12:00:02,789 - INFO - Found deal: Сделка по обращению (301721445)
```

## 🔍 Поиск номеров в тексте

Поддерживаемые форматы:
- `сделка по обращению (301721445)`
- `обращению (301721445)`
- `дело №301721445`
- `(301721445)` - числа в скобках 6+ цифр
- `№301721445` - числа после № 6+ цифр

## 🚦 Статистика API

После выполнения показывается статистика:
```
=== API Statistics ===
Total requests: 15
Successful: 13
Failed: 2
Retry attempts: 5
Duration: 45.2 seconds
Success rate: 86.7%
```

## ⚡ Рекомендации по производительности

### Для избежания 503 ошибок:
1. **Используйте rate limiting**: `--rate-limit 1.0` (1 секунда между запросами)
2. **Увеличьте retry**: `--max-retries 10`
3. **Конкретные запросы**: используйте `--deal-id` вместо обработки всех сделок

### Для быстрой работы:
1. **Конкретная сделка**: `--deal-id 301721445`
2. **Первая сделка**: `--first-only` 
3. **Уменьшение задержек**: `--rate-limit 0.2` (осторожно!)

### Для отладки:
1. **Полное логирование**: `--debug`
2. **Сохранение данных**: `--output debug.json`
3. **Увеличенный таймаут**: `--timeout 60`

## 📞 Примеры для вашей задачи

Для получения сделки 301721445:
```bash
# Прямой поиск по ID
python3 get_first_deal.py --deal-id 301721445 --debug --output deal_301721445.json

# Поиск по номеру в названии/тексте
python3 get_first_deal.py --find-number 301721445 --debug --output found_deals.json

# Безопасный режим с увеличенными задержками
python3 get_first_deal.py --deal-id 301721445 --rate-limit 2.0 --max-retries 10 --timeout 60
```