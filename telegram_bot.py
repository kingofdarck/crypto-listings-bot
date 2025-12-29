import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
from telegram import Bot
from telegram.error import TelegramError
from exchange_monitor import Listing
import config

class TelegramNotifier:
    def __init__(self, bot_token: str):
        self.bot = Bot(token=bot_token)
        self.chat_id = config.CHAT_ID
        
    async def send_message(self, message: str, parse_mode='HTML'):
        """Отправка сообщения в Telegram"""
        try:
            if not self.chat_id:
                # Если chat_id не установлен, пытаемся получить его
                updates = await self.bot.get_updates()
                if updates:
                    self.chat_id = updates[-1].effective_chat.id
                    config.CHAT_ID = self.chat_id
                else:
                    logging.error("Не удалось получить chat_id. Отправьте любое сообщение боту.")
                    return False
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            return True
            
        except TelegramError as e:
            logging.error(f"Ошибка отправки сообщения в Telegram: {e}")
            return False
    
    def format_upcoming_listings_message(self, listings: List[Listing]) -> str:
        """Форматирование сообщения о предстоящих листингах"""
        if not listings:
            return "📊 <b>Предстоящие листинги</b>\n\nНет запланированных листингов в ближайшее время."
        
        message = "📊 <b>5 ближайших листингов</b>\n\n"
        
        # Сортируем по времени листинга
        sorted_listings = sorted(listings, key=lambda x: x.listing_time)[:5]
        
        for i, listing in enumerate(sorted_listings, 1):
            time_str = listing.listing_time.strftime("%d.%m.%Y %H:%M UTC")
            time_left = self._get_time_left(listing.listing_time)
            
            message += f"<b>{i}. {listing.symbol}</b>\n"
            message += f"🏢 Биржа: {listing.exchange}\n"
            message += f"⏰ Время: {time_str}\n"
            message += f"⏳ Осталось: {time_left}\n"
            
            if listing.announcement_url:
                message += f"🔗 <a href='{listing.announcement_url}'>Анонс</a>\n"
            
            message += "\n"
        
        return message
    
    def format_new_listing_alert(self, listing: Listing) -> str:
        """Форматирование уведомления о начавшемся листинге"""
        message = "🚨 <b>ЛИСТИНГ НАЧАЛСЯ!</b> 🚨\n\n"
        message += f"💰 <b>Токен:</b> {listing.symbol}\n"
        message += f"🏢 <b>Биржа:</b> {listing.exchange}\n"
        message += f"⏰ <b>Время начала:</b> {listing.listing_time.strftime('%d.%m.%Y %H:%M UTC')}\n"
        
        if listing.announcement_url:
            message += f"🔗 <a href='{listing.announcement_url}'>Подробности</a>\n"
        
        message += "\n💡 <i>Торговля началась! Успевайте!</i>"
        
        return message
    
    def format_upcoming_listing_alert(self, listing: Listing) -> str:
        """Форматирование уведомления о предстоящем листинге"""
        time_left = self._get_time_left(listing.listing_time)
        
        message = "⏰ <b>СКОРО ЛИСТИНГ!</b> ⏰\n\n"
        message += f"💰 <b>Токен:</b> {listing.symbol}\n"
        message += f"🏢 <b>Биржа:</b> {listing.exchange}\n"
        message += f"⏰ <b>Время листинга:</b> {listing.listing_time.strftime('%d.%m.%Y %H:%M UTC')}\n"
        message += f"⏳ <b>Осталось:</b> {time_left}\n"
        
        if listing.announcement_url:
            message += f"🔗 <a href='{listing.announcement_url}'>Анонс</a>\n"
        
        return message
    
    def _get_time_left(self, listing_time: datetime) -> str:
        """Вычисление оставшегося времени до листинга"""
        now = datetime.now()
        if listing_time <= now:
            return "Уже началось"
        
        time_diff = listing_time - now
        
        if time_diff.days > 0:
            return f"{time_diff.days} дн. {time_diff.seconds // 3600} ч."
        elif time_diff.seconds >= 3600:
            hours = time_diff.seconds // 3600
            minutes = (time_diff.seconds % 3600) // 60
            return f"{hours} ч. {minutes} мин."
        else:
            minutes = time_diff.seconds // 60
            return f"{minutes} мин."
    
    async def send_upcoming_listings_report(self, listings: List[Listing]):
        """Отправка отчета о предстоящих листингах"""
        message = self.format_upcoming_listings_message(listings)
        await self.send_message(message)
    
    async def send_new_listing_alert(self, listing: Listing):
        """Отправка уведомления о новом листинге"""
        message = self.format_new_listing_alert(listing)
        await self.send_message(message)
    
    async def send_upcoming_listing_alert(self, listing: Listing):
        """Отправка уведомления о предстоящем листинге"""
        message = self.format_upcoming_listing_alert(listing)
        await self.send_message(message)
    
    async def send_startup_message(self):
        """Отправка сообщения о запуске бота"""
        message = "🤖 <b>Расширенный бот мониторинга листингов запущен!</b>\n\n"
        message += "📊 <b>Официальные источники:</b>\n"
        message += "• Binance API (анонсы)\n• Bybit API (анонсы)\n• KuCoin API (анонсы)\n\n"
        message += "🌐 <b>Социальные сети и агрегаторы:</b>\n"
        message += "• Twitter аккаунты бирж\n• Telegram каналы\n• CoinLaunch, ICO Drops\n• CoinMarketCal\n• RSS новостных сайтов\n\n"
        message += "⏰ Отчеты каждые 5 минут о ближайших листингах\n"
        message += "🚨 Предупреждения за час, 30, 15 и 5 минут до листинга\n"
        message += "💥 Уведомления в момент начала листинга (3 раза)\n\n"
        message += "🎯 <i>Максимальное покрытие всех источников информации!</i>"
        
        await self.send_message(message)