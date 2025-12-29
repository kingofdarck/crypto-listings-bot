import asyncio
import aiohttp
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional
from bs4 import BeautifulSoup
from exchange_monitor import Listing

class EnhancedExchangeMonitor:
    """Расширенный мониторинг для MEXC и OKX с веб-скрапингом"""
    
    def __init__(self):
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_mexc_listings_enhanced(self) -> List[Listing]:
        """Расширенный мониторинг MEXC"""
        listings = []
        
        # Источники для MEXC
        sources = [
            {
                'url': 'https://support.mexc.com/hc/en-us/sections/360000258333-New-Listings',
                'type': 'support_page'
            },
            {
                'url': 'https://www.mexc.com/support/articles/360035513073',
                'type': 'announcements'
            },
            {
                'url': 'https://blog.mexc.com/category/listing/',
                'type': 'blog'
            }
        ]
        
        for source in sources:
            try:
                listings.extend(await self._scrape_mexc_source(source))
            except Exception as e:
                logging.error(f"Ошибка скрапинга MEXC {source['type']}: {e}")
        
        return listings
    
    async def _scrape_mexc_source(self, source: dict) -> List[Listing]:
        """Скрапинг конкретного источника MEXC"""
        listings = []
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        try:
            async with self.session.get(source['url'], headers=headers) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    if source['type'] == 'support_page':
                        listings.extend(self._parse_mexc_support_page(soup, source['url']))
                    elif source['type'] == 'blog':
                        listings.extend(self._parse_mexc_blog(soup, source['url']))
                    elif source['type'] == 'announcements':
                        listings.extend(self._parse_mexc_announcements(soup, source['url']))
                        
        except Exception as e:
            logging.error(f"Ошибка получения данных MEXC: {e}")
            
        return listings
    
    def _parse_mexc_support_page(self, soup: BeautifulSoup, base_url: str) -> List[Listing]:
        """Парсинг страницы поддержки MEXC"""
        listings = []
        
        # Ищем статьи о листингах
        articles = soup.find_all(['a', 'div'], class_=['article-list-link', 'article-title', 'support-article'])
        
        for article in articles:
            title_elem = article.find(['h3', 'h4', 'span', 'div']) or article
            title = title_elem.get_text().strip() if title_elem else ""
            
            if self._is_listing_announcement(title):
                symbol = self._extract_symbol(title)
                if symbol:
                    listing_time = self._extract_time_from_mexc_title(title)
                    link = article.get('href', '') if article.name == 'a' else ''
                    
                    if listing_time and listing_time > datetime.now():
                        listings.append(Listing(
                            exchange='MEXC',
                            symbol=symbol,
                            listing_time=listing_time,
                            announcement_url=self._build_full_url(link, base_url),
                            status='upcoming'
                        ))
        
        return listings
    
    def _parse_mexc_blog(self, soup: BeautifulSoup, base_url: str) -> List[Listing]:
        """Парсинг блога MEXC"""
        listings = []
        
        # Ищем посты в блоге
        posts = soup.find_all(['article', 'div'], class_=['post', 'blog-post', 'entry'])
        
        for post in posts:
            title_elem = post.find(['h1', 'h2', 'h3', 'a'])
            title = title_elem.get_text().strip() if title_elem else ""
            
            if self._is_listing_announcement(title):
                symbol = self._extract_symbol(title)
                if symbol:
                    listing_time = self._extract_time_from_mexc_title(title)
                    link = title_elem.get('href', '') if title_elem and title_elem.name == 'a' else ''
                    
                    if listing_time and listing_time > datetime.now():
                        listings.append(Listing(
                            exchange='MEXC',
                            symbol=symbol,
                            listing_time=listing_time,
                            announcement_url=self._build_full_url(link, base_url),
                            status='upcoming'
                        ))
        
        return listings
    
    async def get_okx_listings_enhanced(self) -> List[Listing]:
        """Расширенный мониторинг OKX"""
        listings = []
        
        # Источники для OKX
        sources = [
            {
                'url': 'https://www.okx.com/support/hc/en-us/sections/115000275131-New-Crypto-Listings',
                'type': 'support_page'
            },
            {
                'url': 'https://www.okx.com/academy/en/category/announcements',
                'type': 'academy'
            },
            {
                'url': 'https://www.okx.com/help/new-listings',
                'type': 'help_page'
            }
        ]
        
        for source in sources:
            try:
                listings.extend(await self._scrape_okx_source(source))
            except Exception as e:
                logging.error(f"Ошибка скрапинга OKX {source['type']}: {e}")
        
        # Также проверяем API инструментов
        try:
            api_listings = await self._get_okx_api_listings()
            listings.extend(api_listings)
        except Exception as e:
            logging.error(f"Ошибка OKX API: {e}")
        
        return listings
    
    async def _scrape_okx_source(self, source: dict) -> List[Listing]:
        """Скрапинг конкретного источника OKX"""
        listings = []
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.okx.com/',
        }
        
        try:
            async with self.session.get(source['url'], headers=headers) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    if source['type'] == 'support_page':
                        listings.extend(self._parse_okx_support_page(soup, source['url']))
                    elif source['type'] == 'academy':
                        listings.extend(self._parse_okx_academy(soup, source['url']))
                    elif source['type'] == 'help_page':
                        listings.extend(self._parse_okx_help_page(soup, source['url']))
                        
        except Exception as e:
            logging.error(f"Ошибка получения данных OKX: {e}")
            
        return listings
    
    def _parse_okx_support_page(self, soup: BeautifulSoup, base_url: str) -> List[Listing]:
        """Парсинг страницы поддержки OKX"""
        listings = []
        
        # Ищем статьи о листингах
        articles = soup.find_all(['a', 'div'], href=True) + soup.find_all(['div', 'article'], class_=['article', 'support-article'])
        
        for article in articles:
            title_elem = article.find(['h1', 'h2', 'h3', 'h4', 'span']) or article
            title = title_elem.get_text().strip() if title_elem else ""
            
            if self._is_listing_announcement(title):
                symbol = self._extract_symbol(title)
                if symbol:
                    listing_time = self._extract_time_from_okx_title(title)
                    link = article.get('href', '') if article.name == 'a' else ''
                    
                    if listing_time and listing_time > datetime.now():
                        listings.append(Listing(
                            exchange='OKX',
                            symbol=symbol,
                            listing_time=listing_time,
                            announcement_url=self._build_full_url(link, base_url),
                            status='upcoming'
                        ))
        
        return listings
    
    def _parse_okx_academy(self, soup: BeautifulSoup, base_url: str) -> List[Listing]:
        """Парсинг академии OKX"""
        listings = []
        
        # Ищем статьи в академии
        articles = soup.find_all(['article', 'div'], class_=['article', 'post', 'academy-post'])
        
        for article in articles:
            title_elem = article.find(['h1', 'h2', 'h3', 'a'])
            title = title_elem.get_text().strip() if title_elem else ""
            
            if self._is_listing_announcement(title):
                symbol = self._extract_symbol(title)
                if symbol:
                    listing_time = self._extract_time_from_okx_title(title)
                    link = title_elem.get('href', '') if title_elem and title_elem.name == 'a' else ''
                    
                    if listing_time and listing_time > datetime.now():
                        listings.append(Listing(
                            exchange='OKX',
                            symbol=symbol,
                            listing_time=listing_time,
                            announcement_url=self._build_full_url(link, base_url),
                            status='upcoming'
                        ))
        
        return listings
    
    async def _get_okx_api_listings(self) -> List[Listing]:
        """Получение листингов через OKX API"""
        listings = []
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Получаем список инструментов
            async with self.session.get("https://www.okx.com/api/v5/public/instruments?instType=SPOT", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    instruments = data.get('data', [])
                    
                    # Сортируем по времени листинга (новые первыми)
                    instruments_with_time = []
                    for inst in instruments:
                        if inst.get('listTime'):
                            list_time = int(inst.get('listTime')) / 1000
                            instruments_with_time.append((inst, list_time))
                    
                    instruments_with_time.sort(key=lambda x: x[1], reverse=True)
                    
                    # Проверяем последние 20 инструментов
                    for inst, list_timestamp in instruments_with_time[:20]:
                        list_datetime = datetime.fromtimestamp(list_timestamp)
                        
                        # Если листинг был в последние 48 часов или в будущем
                        time_diff = datetime.now() - list_datetime
                        if time_diff < timedelta(hours=48) or list_datetime > datetime.now():
                            inst_id = inst.get('instId', '')
                            symbol = inst_id.split('-')[0] if '-' in inst_id else inst_id
                            
                            status = 'upcoming' if list_datetime > datetime.now() else 'active'
                            
                            listings.append(Listing(
                                exchange='OKX',
                                symbol=symbol,
                                listing_time=list_datetime,
                                announcement_url=f"https://www.okx.com/trade-spot/{inst_id.lower()}",
                                status=status
                            ))
                            
        except Exception as e:
            logging.error(f"Ошибка OKX API инструментов: {e}")
            
        return listings
    
    def _is_listing_announcement(self, title: str) -> bool:
        """Проверка, является ли заголовок анонсом листинга"""
        title_lower = title.lower()
        keywords = [
            'listing', 'will list', 'new token', 'new coin',
            'trading launch', 'spot trading', 'trading starts',
            'now available', 'added to', 'launch'
        ]
        return any(keyword in title_lower for keyword in keywords)
    
    def _extract_symbol(self, title: str) -> Optional[str]:
        """Извлечение символа токена из заголовка"""
        # Ищем символы в скобках или заглавными буквами
        patterns = [
            r'\(([A-Z]{2,10})\)',  # В скобках (BTC)
            r'\b([A-Z]{2,10})\b',  # Отдельно стоящие заглавные буквы
            r'([A-Z]{2,10})\s+(?:token|coin)',  # Перед словом token/coin
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                symbol = match.group(1)
                # Исключаем общие слова
                if symbol not in ['USD', 'BTC', 'ETH', 'USDT', 'THE', 'NEW', 'AND', 'FOR', 'YOU', 'ALL']:
                    return symbol
        
        return None
    
    def _extract_time_from_mexc_title(self, title: str) -> Optional[datetime]:
        """Извлечение времени из заголовка MEXC"""
        # MEXC часто использует форматы типа "December 15, 2024"
        patterns = [
            r'(\w+\s+\d{1,2},\s+\d{4})',  # December 15, 2024
            r'(\d{1,2}/\d{1,2}/\d{4})',   # 12/15/2024
            r'(\d{4}-\d{2}-\d{2})',       # 2024-12-15
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                try:
                    from dateutil import parser
                    parsed_time = parser.parse(match.group(1))
                    # Если только дата, добавляем время (обычно 10:00 UTC)
                    if parsed_time.hour == 0 and parsed_time.minute == 0:
                        parsed_time = parsed_time.replace(hour=10)
                    return parsed_time
                except:
                    continue
        
        # Если точное время не найдено, возвращаем завтра в 10:00
        return datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    def _extract_time_from_okx_title(self, title: str) -> Optional[datetime]:
        """Извлечение времени из заголовка OKX"""
        # OKX использует различные форматы
        patterns = [
            r'(\w+\s+\d{1,2},\s+\d{4}\s+at\s+\d{1,2}:\d{2})',  # January 15, 2024 at 10:00
            r'(\d{1,2}:\d{2}\s+UTC\s+on\s+\w+\s+\d{1,2})',     # 10:00 UTC on January 15
            r'(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2})',            # 2024-01-15 10:00
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                try:
                    from dateutil import parser
                    return parser.parse(match.group(1))
                except:
                    continue
        
        # Если точное время не найдено, возвращаем завтра в 12:00
        return datetime.now().replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    def _build_full_url(self, link: str, base_url: str) -> str:
        """Построение полного URL"""
        if not link:
            return base_url
        if link.startswith('http'):
            return link
        if link.startswith('/'):
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            return f"{parsed.scheme}://{parsed.netloc}{link}"
        return f"{base_url.rstrip('/')}/{link.lstrip('/')}"