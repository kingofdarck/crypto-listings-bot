import os

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = "8565304713:AAFpnuNkp4QR6Yk9H-5NoN8l3Z1pN2WigKQ"
CHAT_ID = None  # Будет установлен автоматически при первом сообщении

# Exchange APIs
EXCHANGE_APIS = {
    'binance': {
        'announcements': 'https://www.binance.com/bapi/composite/v1/public/cms/article/list/query',
        'new_listings': 'https://api.binance.com/api/v3/exchangeInfo'
    },
    'bybit': {
        'announcements': 'https://api.bybit.com/v5/announcements',
        'new_listings': 'https://api.bybit.com/v5/market/instruments-info'
    },
    'mexc': {
        'announcements': 'https://www.mexc.com/api/platform/spot/market/symbols',
        'new_listings': 'https://api.mexc.com/api/v3/exchangeInfo'
    },
    'kucoin': {
        'announcements': 'https://api.kucoin.com/api/v1/announcements',
        'new_listings': 'https://api.kucoin.com/api/v1/symbols'
    },
    'okx': {
        'announcements': 'https://www.okx.com/api/v5/public/announcements',
        'new_listings': 'https://www.okx.com/api/v5/public/instruments'
    }
}

# Timing Configuration
CHECK_INTERVAL = 300  # 5 минут в секундах
LISTING_ALERT_INTERVAL = 60  # 1 минута для дублирования уведомлений
LISTING_ALERT_COUNT = 3  # Количество дублирований

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "crypto_listings.log"