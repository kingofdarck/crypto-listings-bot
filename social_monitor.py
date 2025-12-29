import asyncio
import aiohttp
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from exchange_monitor import Listing

@dataclass
class SocialSource:
    name: str
    url: str
    source_type: str  # twitter, telegram, website, rss
    keywords: List[str]
    enabled: bool = True

class SocialMediaMonitor:
    def __init__(self):
        self.session = None
        self.sources = self._init_sources()
        
    def _init_sources(self) -> List[SocialSource]:
        """Инициализация источников для мониторинга"""
        return [
            # Twitter аккаунты бирж
            SocialSource(
                name="Binance Twitter",
                url="https://api.twitter.com/2/users/by/username/binance/tweets",
                source_type="twitter",
                keywords=["listing", "will list", "new token", "trading starts"]
            ),
            SocialSource(
                name="Bybit Twitter", 
                url="https://api.twitter.com/2/users/by/username/Bybit_Official/tweets",
                source_type="twitter",
                keywords=["listing", "spot trading", "new coin", "launch"]
            ),
            SocialSource(
                name="KuCoin Twitter",
                url="https://api.twitter.com/2/users/by/username/kucoincom/tweets", 
                source_type="twitter",
                keywords=["listing", "new trading", "spot market"]
            ),
            
            # Telegram каналы
            SocialSource(
                name="Binance Announcements",
                url="https://t.me/s/binance_announcements",
                source_type="telegram",
                keywords=["listing", "will list", "trading will start"]
            ),
            SocialSource(
                name="Bybit Announcements",
                url="https://t.me/s/Bybit_Announcements", 
                source_type="telegram",
                keywords=["listing", "spot trading", "new token"]
            ),
            
            # Агрегаторы и календари
            SocialSource(
                name="CoinLaunch",
                url="https://coinlaunch.space/api/listings",
                source_type="api",
                keywords=["binance", "bybit", "kucoin", "mexc", "okx"]
            ),
            SocialSource(
                name="ICO Drops",
                url="https://icodrops.com/calendar/",
                source_type="website", 
                keywords=["exchange listing", "trading starts"]
            ),
            SocialSource(
                name="CoinMarketCal",
                url="https://coinmarketcal.com/api/v1/events",
                source_type="api",
                keywords=["listing", "exchange"]
            ),
            
            # DEX агрегаторы
            SocialSource(
                name="Dune Analytics",
                url="https://dune.com/api/v1/query/recent_listings",
                source_type="api", 
                keywords=["new token", "first trade", "liquidity added"]
            ),
            
            # Новостные сайты
            SocialSource(
                name="CoinDesk RSS",
                url="https://www.coindesk.com/arc/outboundfeeds/rss/",
                source_type="rss",
                keywords=["listing", "exchange", "trading launch"]
            ),
            SocialSource(
                name="Cointelegraph RSS", 
                url="https://cointelegraph.com/rss",
                source_type="rss",
                keywords=["listing announcement", "new exchange", "trading begins"]
            )
        ]
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def monitor_twitter_accounts(self) -> List[Listing]:
        """Мониторинг Twitter аккаунтов бирж"""
        listings = []
        
        twitter_sources = [s for s in self.sources if s.source_type == "twitter" and s.enabled]
        
        for source in twitter_sources:
            try:
                # Используем альтернативный метод без Twitter API (nitter или scraping)
                listings.extend(await self._scrape_twitter_alternative(source))
            except Exception as e:
                logging.error(f"Ошибка мониторинга Twitter {source.name}: {e}")
        
        return listings
    
    async def _scrape_twitter_alternative(self, source: SocialSource) -> List[Listing]:
        """Альтернативный способ получения твитов через nitter"""
        listings = []
        
        try:
            # Используем nitter.net как альтернативу Twitter API
            username = source.url.split('/')[-2]  # Извлекаем username из URL
            nitter_url = f"https://nitter.net/{username}/rss"
            
            async with self.session.get(nitter_url) as response:
                if response.status == 200:
                    content = await response.text()
                    listings.extend(self._parse_twitter_rss(content, source))
                    
        except Exception as e:
            logging.error(f"Ошибка scraping Twitter через nitter: {e}")
            
        return listings
    
    def _parse_twitter_rss(self, rss_content: str, source: SocialSource) -> List[Listing]:
        """Парсинг RSS фида Twitter через nitter"""
        listings = []
        
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(rss_content)
            
            for item in root.findall('.//item')[:10]:  # Последние 10 твитов
                title = item.find('title').text if item.find('title') is not None else ""
                description = item.find('description').text if item.find('description') is not None else ""
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                
                full_text = f"{title} {description}".lower()
                
                # Проверяем наличие ключевых слов
                if any(keyword in full_text for keyword in source.keywords):
                    # Извлекаем информацию о листинге
                    symbol_match = re.search(r'\b([A-Z]{2,10})\b', title + description)
                    if symbol_match:
                        symbol = symbol_match.group(1)
                        
                        # Определяем биржу из источника
                        exchange = self._extract_exchange_from_source(source.name)
                        
                        # Пытаемся извлечь время
                        listing_time = self._extract_time_from_social_post(full_text, pub_date)
                        
                        if listing_time and listing_time > datetime.now():
                            listings.append(Listing(
                                exchange=exchange,
                                symbol=symbol,
                                listing_time=listing_time,
                                announcement_url=f"https://twitter.com/{source.url.split('/')[-2]}",
                                status='upcoming'
                            ))
                            
        except Exception as e:
            logging.error(f"Ошибка парсинга Twitter RSS: {e}")
            
        return listings
    
    async def monitor_telegram_channels(self) -> List[Listing]:
        """Мониторинг Telegram каналов"""
        listings = []
        
        telegram_sources = [s for s in self.sources if s.source_type == "telegram" and s.enabled]
        
        for source in telegram_sources:
            try:
                listings.extend(await self._scrape_telegram_channel(source))
            except Exception as e:
                logging.error(f"Ошибка мониторинга Telegram {source.name}: {e}")
        
        return listings
    
    async def _scrape_telegram_channel(self, source: SocialSource) -> List[Listing]:
        """Скрапинг Telegram канала через веб-версию"""
        listings = []
        
        try:
            # Используем публичную веб-версию Telegram
            async with self.session.get(source.url) as response:
                if response.status == 200:
                    content = await response.text()
                    listings.extend(self._parse_telegram_messages(content, source))
                    
        except Exception as e:
            logging.error(f"Ошибка scraping Telegram: {e}")
            
        return listings
    
    def _parse_telegram_messages(self, html_content: str, source: SocialSource) -> List[Listing]:
        """Парсинг сообщений Telegram канала"""
        listings = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Ищем сообщения в канале
            messages = soup.find_all('div', class_='tgme_widget_message_text')
            
            for message in messages[:20]:  # Последние 20 сообщений
                text = message.get_text().lower()
                
                # Проверяем ключевые слова
                if any(keyword in text for keyword in source.keywords):
                    # Извлекаем символ токена
                    symbol_match = re.search(r'\b([A-Z]{2,10})\b', message.get_text())
                    if symbol_match:
                        symbol = symbol_match.group(1)
                        
                        # Определяем биржу
                        exchange = self._extract_exchange_from_source(source.name)
                        
                        # Извлекаем время
                        listing_time = self._extract_time_from_social_post(text, "")
                        
                        if listing_time and listing_time > datetime.now():
                            listings.append(Listing(
                                exchange=exchange,
                                symbol=symbol,
                                listing_time=listing_time,
                                announcement_url=source.url,
                                status='upcoming'
                            ))
                            
        except Exception as e:
            logging.error(f"Ошибка парсинга Telegram сообщений: {e}")
            
        return listings
    
    async def monitor_aggregator_apis(self) -> List[Listing]:
        """Мониторинг API агрегаторов листингов"""
        listings = []
        
        api_sources = [s for s in self.sources if s.source_type == "api" and s.enabled]
        
        for source in api_sources:
            try:
                listings.extend(await self._fetch_from_aggregator(source))
            except Exception as e:
                logging.error(f"Ошибка мониторинга API {source.name}: {e}")
        
        return listings
    
    async def _fetch_from_aggregator(self, source: SocialSource) -> List[Listing]:
        """Получение данных от агрегаторов"""
        listings = []
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with self.session.get(source.url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    listings.extend(self._parse_aggregator_data(data, source))
                    
        except Exception as e:
            logging.error(f"Ошибка получения данных от {source.name}: {e}")
            
        return listings
    
    def _parse_aggregator_data(self, data: dict, source: SocialSource) -> List[Listing]:
        """Парсинг данных от агрегаторов"""
        listings = []
        
        try:
            if source.name == "CoinLaunch":
                # Парсинг данных CoinLaunch
                for item in data.get('listings', []):
                    if item.get('exchange') in ['binance', 'bybit', 'kucoin', 'mexc', 'okx']:
                        listing_time = datetime.fromisoformat(item.get('listing_date', ''))
                        if listing_time > datetime.now():
                            listings.append(Listing(
                                exchange=item.get('exchange').title(),
                                symbol=item.get('symbol'),
                                listing_time=listing_time,
                                announcement_url=item.get('announcement_url', ''),
                                status='upcoming'
                            ))
            
            elif source.name == "CoinMarketCal":
                # Парсинг CoinMarketCal
                for event in data.get('events', []):
                    if 'listing' in event.get('title', '').lower():
                        event_date = datetime.fromisoformat(event.get('date_event', ''))
                        if event_date > datetime.now():
                            # Извлекаем символ и биржу из описания
                            symbol_match = re.search(r'\b([A-Z]{2,10})\b', event.get('title', ''))
                            exchange_match = re.search(r'(binance|bybit|kucoin|mexc|okx)', 
                                                     event.get('description', '').lower())
                            
                            if symbol_match and exchange_match:
                                listings.append(Listing(
                                    exchange=exchange_match.group(1).title(),
                                    symbol=symbol_match.group(1),
                                    listing_time=event_date,
                                    announcement_url=event.get('source', ''),
                                    status='upcoming'
                                ))
                                
        except Exception as e:
            logging.error(f"Ошибка парсинга данных агрегатора: {e}")
            
        return listings
    
    async def monitor_rss_feeds(self) -> List[Listing]:
        """Мониторинг RSS фидов новостных сайтов"""
        listings = []
        
        rss_sources = [s for s in self.sources if s.source_type == "rss" and s.enabled]
        
        for source in rss_sources:
            try:
                listings.extend(await self._parse_rss_feed(source))
            except Exception as e:
                logging.error(f"Ошибка мониторинга RSS {source.name}: {e}")
        
        return listings
    
    async def _parse_rss_feed(self, source: SocialSource) -> List[Listing]:
        """Парсинг RSS фидов"""
        listings = []
        
        try:
            async with self.session.get(source.url) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(content)
                    
                    for item in root.findall('.//item')[:20]:
                        title = item.find('title').text if item.find('title') is not None else ""
                        description = item.find('description').text if item.find('description') is not None else ""
                        pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                        
                        full_text = f"{title} {description}".lower()
                        
                        # Проверяем ключевые слова
                        if any(keyword in full_text for keyword in source.keywords):
                            # Извлекаем информацию о листинге
                            symbol_match = re.search(r'\b([A-Z]{2,10})\b', title + description)
                            exchange_match = re.search(r'(binance|bybit|kucoin|mexc|okx)', full_text)
                            
                            if symbol_match and exchange_match:
                                listing_time = self._extract_time_from_social_post(full_text, pub_date)
                                
                                if listing_time and listing_time > datetime.now():
                                    listings.append(Listing(
                                        exchange=exchange_match.group(1).title(),
                                        symbol=symbol_match.group(1),
                                        listing_time=listing_time,
                                        announcement_url=item.find('link').text if item.find('link') is not None else "",
                                        status='upcoming'
                                    ))
                                    
        except Exception as e:
            logging.error(f"Ошибка парсинга RSS: {e}")
            
        return listings
    
    def _extract_exchange_from_source(self, source_name: str) -> str:
        """Извлечение названия биржи из источника"""
        source_lower = source_name.lower()
        if 'binance' in source_lower:
            return 'Binance'
        elif 'bybit' in source_lower:
            return 'Bybit'
        elif 'kucoin' in source_lower:
            return 'KuCoin'
        elif 'mexc' in source_lower:
            return 'MEXC'
        elif 'okx' in source_lower:
            return 'OKX'
        else:
            return 'Unknown'
    
    def _extract_time_from_social_post(self, text: str, pub_date: str) -> Optional[datetime]:
        """Извлечение времени из социального поста"""
        try:
            # Паттерны для социальных сетей
            patterns = [
                r'(\d{1,2}:\d{2}\s*utc)',
                r'(tomorrow\s+at\s+\d{1,2}:\d{2})',
                r'(in\s+\d+\s+hours?)',
                r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2})',
                r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}.*?\d{1,2}:\d{2}'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    time_str = match.group(1)
                    
                    # Простая обработка относительного времени
                    if 'tomorrow' in time_str:
                        return datetime.now() + timedelta(days=1)
                    elif 'in' in time_str and 'hour' in time_str:
                        hours_match = re.search(r'(\d+)', time_str)
                        if hours_match:
                            hours = int(hours_match.group(1))
                            return datetime.now() + timedelta(hours=hours)
                    else:
                        # Пытаемся парсить как обычную дату
                        try:
                            from dateutil import parser
                            return parser.parse(time_str, fuzzy=True)
                        except:
                            continue
            
            # Если не нашли время в тексте, используем время публикации + 1 день
            if pub_date:
                try:
                    from dateutil import parser
                    pub_datetime = parser.parse(pub_date)
                    return pub_datetime + timedelta(days=1)
                except:
                    pass
                    
        except Exception as e:
            logging.error(f"Ошибка извлечения времени из поста: {e}")
            
        return None
    
    async def get_all_social_listings(self) -> List[Listing]:
        """Получение всех листингов из социальных источников"""
        all_listings = []
        
        # Запускаем все мониторы параллельно
        tasks = [
            self.monitor_twitter_accounts(),
            self.monitor_telegram_channels(), 
            self.monitor_aggregator_apis(),
            self.monitor_rss_feeds()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_listings.extend(result)
            elif isinstance(result, Exception):
                logging.error(f"Ошибка в социальном мониторе: {result}")
        
        # Дедупликация
        unique_listings = []
        seen = set()
        
        for listing in all_listings:
            key = f"{listing.exchange}:{listing.symbol}:{listing.listing_time}"
            if key not in seen:
                seen.add(key)
                unique_listings.append(listing)
        
        return unique_listings