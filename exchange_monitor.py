import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import re

@dataclass
class Listing:
    exchange: str
    symbol: str
    listing_time: datetime
    announcement_url: Optional[str] = None
    status: str = "upcoming"  # upcoming, active, completed

class ExchangeMonitor:
    def __init__(self):
        self.session = None
        self.known_listings = {}  # exchange -> set of symbols
        self.upcoming_listings = []
        self.active_listings = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_binance_listings(self) -> List[Listing]:
        """Получение предстоящих листингов с Binance"""
        listings = []
        try:
            # Проверяем только анонсы о предстоящих листингах
            announcements_payload = {
                "type": 1,
                "catalogId": 48,
                "pageNo": 1,
                "pageSize": 20
            }
            
            async with self.session.post(
                "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query",
                json=announcements_payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = data.get('data', {}).get('articles', [])
                    
                    for article in articles:
                        title = article.get('title', '')
                        content = article.get('content', '')
                        
                        # Ищем анонсы о предстоящих листингах
                        if any(keyword in title.lower() for keyword in ['will list', 'listing', 'launches']):
                            # Извлекаем символ токена
                            symbol_match = re.search(r'\b([A-Z]{2,10})\b', title)
                            if symbol_match:
                                symbol = symbol_match.group(1)
                                
                                # Извлекаем время листинга из контента
                                listing_time = self._extract_listing_time(content + ' ' + title)
                                
                                # Добавляем только если листинг в будущем
                                if listing_time and listing_time > datetime.now():
                                    listings.append(Listing(
                                        exchange='Binance',
                                        symbol=symbol,
                                        listing_time=listing_time,
                                        announcement_url=f"https://www.binance.com/en/support/announcement/{article.get('code', '')}",
                                        status='upcoming'
                                    ))
                            
        except Exception as e:
            logging.error(f"Ошибка при получении данных Binance: {e}")
            
        return listings
    
    async def fetch_bybit_listings(self) -> List[Listing]:
        """Получение предстоящих листингов с Bybit"""
        listings = []
        try:
            # Проверяем только анонсы о предстоящих листингах
            async with self.session.get("https://api.bybit.com/v5/announcements?category=new_crypto&limit=20") as response:
                if response.status == 200:
                    data = await response.json()
                    announcements = data.get('result', {}).get('list', [])
                    
                    for announcement in announcements:
                        title = announcement.get('title', '')
                        content = announcement.get('content', '')
                        
                        # Ищем анонсы о предстоящих листингах
                        if any(keyword in title.lower() for keyword in ['listing', 'launch', 'will list', 'coming soon']):
                            symbol_match = re.search(r'\b([A-Z]{2,10})\b', title)
                            if symbol_match:
                                symbol = symbol_match.group(1)
                                
                                # Извлекаем время листинга
                                listing_time = self._extract_listing_time(content + ' ' + title)
                                if not listing_time:
                                    listing_time = self._parse_timestamp(announcement.get('publishTime'))
                                
                                # Добавляем только если листинг в будущем
                                if listing_time and listing_time > datetime.now():
                                    listings.append(Listing(
                                        exchange='Bybit',
                                        symbol=symbol,
                                        listing_time=listing_time,
                                        announcement_url=announcement.get('url', ''),
                                        status='upcoming'
                                    ))
                            
        except Exception as e:
            logging.error(f"Ошибка при получении данных Bybit: {e}")
            
        return listings
    
    async def fetch_mexc_listings(self) -> List[Listing]:
        """Получение предстоящих листингов с MEXC"""
        listings = []
        try:
            # MEXC обычно анонсирует листинги в Twitter и на сайте
            # Пока что возвращаем пустой список, так как у них нет публичного API для анонсов
            # В будущем можно добавить парсинг их сайта или Twitter API
            pass
                            
        except Exception as e:
            logging.error(f"Ошибка при получении данных MEXC: {e}")
            
        return listings
    
    async def fetch_kucoin_listings(self) -> List[Listing]:
        """Получение предстоящих листингов с KuCoin"""
        listings = []
        try:
            # Проверяем только анонсы о предстоящих листингах
            async with self.session.get("https://api.kucoin.com/api/v1/announcements?currentPage=1&pageSize=20") as response:
                if response.status == 200:
                    data = await response.json()
                    announcements = data.get('data', {}).get('items', [])
                    
                    for announcement in announcements:
                        title = announcement.get('title', '')
                        content = announcement.get('content', '')
                        
                        # Ищем анонсы о предстоящих листингах
                        if any(keyword in title.lower() for keyword in ['listing', 'launch', 'will list', 'coming soon']):
                            symbol_match = re.search(r'\b([A-Z]{2,10})\b', title)
                            if symbol_match:
                                symbol = symbol_match.group(1)
                                
                                # Извлекаем время листинга
                                listing_time = self._extract_listing_time(content + ' ' + title)
                                if not listing_time:
                                    listing_time = self._parse_timestamp(announcement.get('publishTime'))
                                
                                # Добавляем только если листинг в будущем
                                if listing_time and listing_time > datetime.now():
                                    listings.append(Listing(
                                        exchange='KuCoin',
                                        symbol=symbol,
                                        listing_time=listing_time,
                                        announcement_url=announcement.get('url', ''),
                                        status='upcoming'
                                    ))
                            
        except Exception as e:
            logging.error(f"Ошибка при получении данных KuCoin: {e}")
            
        return listings
    
    async def fetch_okx_listings(self) -> List[Listing]:
        """Получение предстоящих листингов с OKX"""
        listings = []
        try:
            # OKX обычно анонсирует листинги в своих анонсах
            # Пока что возвращаем пустой список, так как их API анонсов требует авторизацию
            # В будущем можно добавить парсинг их сайта
            pass
                            
        except Exception as e:
            logging.error(f"Ошибка при получении данных OKX: {e}")
            
        return listings
    
    async def get_all_listings(self) -> List[Listing]:
        """Получение всех листингов со всех бирж"""
        all_listings = []
        
        tasks = [
            self.fetch_binance_listings(),
            self.fetch_bybit_listings(),
            self.fetch_mexc_listings(),
            self.fetch_kucoin_listings(),
            self.fetch_okx_listings()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_listings.extend(result)
            elif isinstance(result, Exception):
                logging.error(f"Ошибка при получении листингов: {result}")
        
        return all_listings
    
    def _extract_listing_time(self, content: str) -> Optional[datetime]:
        """Извлечение времени листинга из текста"""
        import re
        from dateutil import parser
        
        # Паттерны для поиска времени
        time_patterns = [
            # 2024-01-15 14:00 UTC
            r'(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2})\s*(?:UTC|GMT)',
            # January 15, 2024 at 14:00 UTC
            r'(\w+\s+\d{1,2},\s+\d{4}\s+at\s+\d{1,2}:\d{2})\s*(?:UTC|GMT)',
            # 15 Jan 2024, 14:00 UTC
            r'(\d{1,2}\s+\w+\s+\d{4},\s+\d{1,2}:\d{2})\s*(?:UTC|GMT)',
            # 14:00 UTC on January 15
            r'(\d{1,2}:\d{2})\s*(?:UTC|GMT)\s+on\s+(\w+\s+\d{1,2})',
            # Trading will start at 14:00 UTC
            r'(?:start|begin|commence)\s+at\s+(\d{1,2}:\d{2})\s*(?:UTC|GMT)',
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    if isinstance(match, tuple):
                        time_str = ' '.join(match)
                    else:
                        time_str = match
                    
                    # Пытаемся парсить дату
                    parsed_time = parser.parse(time_str, fuzzy=True)
                    
                    # Если год не указан, используем текущий или следующий
                    if parsed_time.year == 1900:  # dateutil default
                        current_year = datetime.now().year
                        parsed_time = parsed_time.replace(year=current_year)
                        
                        # Если дата в прошлом, используем следующий год
                        if parsed_time < datetime.now():
                            parsed_time = parsed_time.replace(year=current_year + 1)
                    
                    # Проверяем, что дата в будущем
                    if parsed_time > datetime.now():
                        return parsed_time
                        
                except Exception as e:
                    continue
        
        # Ищем относительные времена (через X часов/дней)
        relative_patterns = [
            r'in\s+(\d+)\s+hours?',
            r'in\s+(\d+)\s+days?',
            r'after\s+(\d+)\s+hours?',
        ]
        
        for pattern in relative_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    amount = int(match.group(1))
                    if 'hour' in pattern:
                        return datetime.now() + timedelta(hours=amount)
                    elif 'day' in pattern:
                        return datetime.now() + timedelta(days=amount)
                except:
                    continue
        
        return None
    
    def _parse_timestamp(self, timestamp) -> Optional[datetime]:
        """Парсинг timestamp"""
        try:
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp / 1000)
            return None
        except:
            return None
    
    def update_known_listings(self, listings: List[Listing]):
        """Обновление списка известных листингов"""
        for listing in listings:
            exchange_key = listing.exchange.lower()
            if exchange_key not in self.known_listings:
                self.known_listings[exchange_key] = set()
            self.known_listings[exchange_key].add(listing.symbol)