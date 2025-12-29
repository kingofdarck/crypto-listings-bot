import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from typing import List, Set
from exchange_monitor import ExchangeMonitor, Listing
from telegram_bot import TelegramNotifier
import config

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class CryptoListingBot:
    def __init__(self):
        self.notifier = TelegramNotifier(config.TELEGRAM_BOT_TOKEN)
        self.monitor = None
        self.known_symbols = set()  # Не используется для предстоящих листингов
        self.upcoming_listings = []
        self.active_alerts = {}  # symbol -> alert_count
        self.data_file = "listings_data.json"
        
    async def load_data(self):
        """Загрузка сохраненных данных"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.known_symbols = set(data.get('known_symbols', []))  # Оставляем для совместимости
                    
                    # Загружаем предстоящие листинги
                    upcoming_data = data.get('upcoming_listings', [])
                    self.upcoming_listings = []
                    for item in upcoming_data:
                        listing = Listing(
                            exchange=item['exchange'],
                            symbol=item['symbol'],
                            listing_time=datetime.fromisoformat(item['listing_time']),
                            announcement_url=item.get('announcement_url'),
                            status=item.get('status', 'upcoming')
                        )
                        self.upcoming_listings.append(listing)
                        
                    logging.info(f"Загружено {len(self.known_symbols)} известных символов и {len(self.upcoming_listings)} предстоящих листингов")
        except Exception as e:
            logging.error(f"Ошибка загрузки данных: {e}")
    
    async def save_data(self):
        """Сохранение данных"""
        try:
            data = {
                'known_symbols': list(self.known_symbols),
                'upcoming_listings': []
            }
            
            for listing in self.upcoming_listings:
                data['upcoming_listings'].append({
                    'exchange': listing.exchange,
                    'symbol': listing.symbol,
                    'listing_time': listing.listing_time.isoformat(),
                    'announcement_url': listing.announcement_url,
                    'status': listing.status
                })
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logging.error(f"Ошибка сохранения данных: {e}")
    
    async def check_listings(self):
        """Основная функция проверки предстоящих листингов"""
        try:
            async with ExchangeMonitor() as monitor:
                self.monitor = monitor
                
                # Получаем только предстоящие листинги
                all_listings = await monitor.get_all_listings()
                
                new_upcoming_listings = []
                
                for listing in all_listings:
                    # Обрабатываем только предстоящие листинги
                    if listing.status == 'upcoming' and listing.listing_time > datetime.now():
                        listing_key = f"{listing.exchange}:{listing.symbol}"
                        
                        # Проверяем, не знаем ли мы уже об этом листинге
                        existing = next((l for l in self.upcoming_listings 
                                       if l.symbol == listing.symbol and l.exchange == listing.exchange), None)
                        
                        if not existing:
                            new_upcoming_listings.append(listing)
                            logging.info(f"Обнаружен новый предстоящий листинг: {listing.symbol} на {listing.exchange} в {listing.listing_time}")
                
                # Добавляем новые предстоящие листинги
                self.upcoming_listings.extend(new_upcoming_listings)
                
                # Удаляем устаревшие листинги (которые уже прошли)
                current_time = datetime.now()
                expired_listings = []
                
                for listing in self.upcoming_listings[:]:
                    if listing.listing_time <= current_time:
                        expired_listings.append(listing)
                        self.upcoming_listings.remove(listing)
                        logging.info(f"Листинг {listing.symbol} на {listing.exchange} начался!")
                
                # Отправляем уведомления о начавшихся листингах
                for listing in expired_listings:
                    await self.send_listing_started_alerts(listing)
                
                # Проверяем предстоящие листинги на близость к времени листинга
                await self.check_upcoming_listings()
                
                # Сохраняем данные
                await self.save_data()
                
        except Exception as e:
            logging.error(f"Ошибка при проверке листингов: {e}")
    
    async def send_listing_started_alerts(self, listing: Listing):
        """Отправка уведомлений о начавшемся листинге (3 раза каждую минуту)"""
        for i in range(config.LISTING_ALERT_COUNT):
            await self.notifier.send_new_listing_alert(listing)
            logging.info(f"Отправлено уведомление о начале листинга {listing.symbol} ({i+1}/{config.LISTING_ALERT_COUNT})")
            
            if i < config.LISTING_ALERT_COUNT - 1:
                await asyncio.sleep(config.LISTING_ALERT_INTERVAL)
    
    async def check_upcoming_listings(self):
        """Проверка предстоящих листингов и отправка уведомлений"""
        now = datetime.now()
        
        for listing in self.upcoming_listings[:]:
            time_until_listing = (listing.listing_time - now).total_seconds()
            
            # Если листинг уже прошел
            if time_until_listing <= 0:
                await self.send_listing_started_alerts(listing)
                self.upcoming_listings.remove(listing)
                continue
            
            # Уведомления за час, 30 минут, 15 минут, 5 минут
            alert_times = [3600, 1800, 900, 300]  # в секундах
            
            for alert_time in alert_times:
                if abs(time_until_listing - alert_time) < 60:  # погрешность в 1 минуту
                    alert_key = f"{listing.exchange}:{listing.symbol}:{alert_time}"
                    if alert_key not in self.active_alerts:
                        await self.notifier.send_upcoming_listing_alert(listing)
                        self.active_alerts[alert_key] = True
                        logging.info(f"Отправлено предупреждение о листинге {listing.symbol} (осталось {alert_time//60} мин)")
    
    async def send_regular_report(self):
        """Отправка регулярного отчета о предстоящих листингах"""
        try:
            # Сортируем по времени и берем 5 ближайших
            upcoming_sorted = sorted(
                [l for l in self.upcoming_listings if l.listing_time > datetime.now()],
                key=lambda x: x.listing_time
            )[:5]
            
            await self.notifier.send_upcoming_listings_report(upcoming_sorted)
            logging.info(f"Отправлен регулярный отчет о {len(upcoming_sorted)} предстоящих листингах")
            
        except Exception as e:
            logging.error(f"Ошибка отправки регулярного отчета: {e}")
    
    async def run(self):
        """Основной цикл работы бота"""
        logging.info("Запуск бота мониторинга листингов...")
        
        # Загружаем сохраненные данные
        await self.load_data()
        
        # Отправляем сообщение о запуске
        await self.notifier.send_startup_message()
        
        last_report_time = datetime.now()
        
        while True:
            try:
                # Проверяем листинги
                await self.check_listings()
                
                # Отправляем регулярный отчет каждые 5 минут
                now = datetime.now()
                if (now - last_report_time).total_seconds() >= config.CHECK_INTERVAL:
                    await self.send_regular_report()
                    last_report_time = now
                
                # Ждем 30 секунд перед следующей проверкой
                await asyncio.sleep(30)
                
            except KeyboardInterrupt:
                logging.info("Получен сигнал остановки")
                break
            except Exception as e:
                logging.error(f"Ошибка в основном цикле: {e}")
                await asyncio.sleep(60)  # Ждем минуту при ошибке

async def main():
    bot = CryptoListingBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())