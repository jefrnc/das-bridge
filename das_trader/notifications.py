"""Notification system for DAS Trader API."""

import asyncio
import logging
import json
import smtplib
from typing import Dict, Any, Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import platform

logger = logging.getLogger(__name__)


class NotificationManager:
    """Multi-platform notification manager."""
    # TODO: Add rate limiting to avoid spam
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("ENABLE_NOTIFICATIONS", False)
        self.notification_type = config.get("NOTIFICATION_TYPE", "email")
        
        self._notifiers = {
            "email": EmailNotifier(config),
            "discord": DiscordNotifier(config),
            "telegram": TelegramNotifier(config),
            # "pushover": PushoverNotifier(config),  # Coming soon
            # "slack": SlackNotifier(config),  # Not implemented yet
            "webhook": WebhookNotifier(config),
            "desktop": DesktopNotifier(config),
        }
    
    async def send_notification(
        self,
        title: str,
        message: str,
        level: str = "info",
        data: Optional[Dict[str, Any]] = None
    ):
        if not self.enabled:
            return
        
        try:
            notifier = self._notifiers.get(self.notification_type)
            if notifier:
                await notifier.send(title, message, level, data)
            else:
                logger.warning(f"Unsupported notifier: {self.notification_type}")
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    async def send_order_notification(self, order, event_type: str):
        title = f"Order {event_type.upper()}"
        message = (f"Symbol: {order.symbol}\n"
                  f"Side: {order.side.value}\n"
                  f"Quantity: {order.quantity}\n"
                  f"Type: {order.order_type.value}\n"
                  f"Status: {order.status.value}")
        
        if order.price:
            message += f"\nPrice: ${order.price}"
        
        level = "warning" if event_type == "rejected" else "info"
        await self.send_notification(title, message, level, {"order": order.to_dict()})
    
    async def send_position_notification(self, position, event_type: str):
        title = f"Position {event_type.upper()}"
        message = (f"Symbol: {position.symbol}\n"
                  f"Quantity: {position.quantity}\n"
                  f"P&L: ${position.unrealized_pnl:.2f}\n"
                  f"P&L %: {position.pnl_percent:.2f}%")
        
        level = "success" if position.unrealized_pnl > 0 else "warning"
        await self.send_notification(title, message, level, {"position": position.to_dict()})
    
    async def send_alert(self, symbol: str, price: float, condition: str):
        title = f"Price Alert - {symbol}"
        message = f"Price of {symbol} has {condition} ${price:.2f}"
        
        await self.send_notification(title, message, "warning", {
            "symbol": symbol,
            "price": price,
            "condition": condition
        })


class BaseNotifier:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    async def send(self, title: str, message: str, level: str, data: Optional[Dict] = None):
        raise NotImplementedError


class EmailNotifier(BaseNotifier):
    
    async def send(self, title: str, message: str, level: str, data: Optional[Dict] = None):
        try:
            smtp_host = self.config.get("EMAIL_SMTP_HOST", "smtp.gmail.com")
            smtp_port = self.config.get("EMAIL_SMTP_PORT", 587)
            username = self.config.get("EMAIL_USERNAME")
            password = self.config.get("EMAIL_PASSWORD")
            to_addresses = self.config.get("EMAIL_TO_ADDRESSES", [])
            use_tls = self.config.get("EMAIL_USE_TLS", True)
            
            if not username or not password or not to_addresses:
                logger.warning("Incomplete email configuration")
                return
            
            msg = MIMEMultipart()
            msg['From'] = username
            msg['To'] = ", ".join(to_addresses)
            msg['Subject'] = f"[DAS Trader] {title}"
            
            body = f"{message}\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            if data:
                body += f"\n\nAdditional data:\n{json.dumps(data, indent=2)}"
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_host, smtp_port)
            if use_tls:
                server.starttls()
            server.login(username, password)
            
            text = msg.as_string()
            server.sendmail(username, to_addresses, text)
            server.quit()
            
            logger.info(f"Email sent: {title}")
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")


class DiscordNotifier(BaseNotifier):
    """Discord webhook notifier."""
    
    async def send(self, title: str, message: str, level: str, data: Optional[Dict] = None):
        try:
            import aiohttp
            
            webhook_url = self.config.get("DISCORD_WEBHOOK_URL")
            if not webhook_url:
                logger.warning("Discord webhook URL not configured")
                return
            
            colors = {
                "info": 0x3498db,
                "success": 0x2ecc71,
                "warning": 0xf39c12,
                "error": 0xe74c3c
            }
            
            embed = {
                "title": title,
                "description": message,
                "color": colors.get(level, 0x3498db),
                "timestamp": datetime.now().isoformat(),
                "footer": {"text": "DAS Trader Bot"}
            }
            
            if data:
                embed["fields"] = [
                    {"name": "Additional data", "value": f"```json\n{json.dumps(data, indent=2)[:1000]}```"}
                ]
            
            payload = {"embeds": [embed]}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 204:
                        logger.info(f"Discord message sent: {title}")
                    else:
                        logger.error(f"Discord error: {response.status}")
                        
        except ImportError:
            logger.error("aiohttp not installed. Install with: pip install aiohttp")
        except Exception as e:
            logger.error(f"Error sending to Discord: {e}")
            # FIXME: Better error handling needed here


class TelegramNotifier(BaseNotifier):
    
    async def send(self, title: str, message: str, level: str, data: Optional[Dict] = None):
        try:
            import aiohttp
            
            bot_token = self.config.get("TELEGRAM_BOT_TOKEN")
            chat_id = self.config.get("TELEGRAM_CHAT_ID")
            
            if not bot_token or not chat_id:
                logger.warning("Incomplete Telegram configuration")
                return
            
            emojis = {
                "info": "ℹ️",
                "success": "✅",
                "warning": "⚠️",
                "error": "❌"
            }
            
            text = f"{emojis.get(level, 'ℹ️')} *{title}*\n\n{message}"
            
            if data:
                text += f"\n\n```json\n{json.dumps(data, indent=2)[:500]}\n```"
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Telegram message sent: {title}")
                    else:
                        logger.error(f"Telegram error: {response.status}")
                        
        except ImportError:
            logger.error("aiohttp not installed. Install with: pip install aiohttp")
        except Exception as e:
            logger.error(f"Error sending to Telegram: {e}")


class PushoverNotifier(BaseNotifier):
    """Pushover mobile push notification notifier."""
    
    async def send(self, title: str, message: str, level: str, data: Optional[Dict] = None):
        raise NotImplementedError("Pushover support coming in v2")
        # TODO: Implement Pushover notifications


class SlackNotifier(BaseNotifier):
    """Slack notifier."""
    
    async def send(self, title: str, message: str, level: str, data: Optional[Dict] = None):
        # Not implemented yet
        raise NotImplementedError("Slack notifications not ready")


class WebhookNotifier(BaseNotifier):
    """Generic webhook notifier."""
    
    async def send(self, title: str, message: str, level: str, data: Optional[Dict] = None):
        try:
            import aiohttp
            
            webhook_url = self.config.get("CUSTOM_WEBHOOK_URL")
            headers = self.config.get("WEBHOOK_HEADERS", {})
            
            if not webhook_url:
                logger.warning("Webhook URL not configured")
                return
            
            payload = {
                "title": title,
                "message": message,
                "level": level,
                "timestamp": datetime.now().isoformat(),
                "data": data or {}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload, headers=headers) as response:
                    if response.status in [200, 201, 204]:
                        logger.info(f"Webhook sent: {title}")
                    else:
                        logger.error(f"Webhook error: {response.status}")
                        
        except ImportError:
            logger.error("aiohttp not installed. Install with: pip install aiohttp")
        except Exception as e:
            logger.error(f"Error sending webhook: {e}")


class DesktopNotifier(BaseNotifier):
    """Desktop notifier (Windows/macOS/Linux)."""
    
    async def send(self, title: str, message: str, level: str, data: Optional[Dict] = None):
        if not self.config.get("ENABLE_DESKTOP_NOTIFICATIONS", True):
            return
        
        try:
            system = platform.system().lower()
            
            if system == "windows":
                await self._windows_notification(title, message)
            elif system == "darwin":
                await self._macos_notification(title, message)
            elif system == "linux":
                await self._linux_notification(title, message)
            else:
                logger.warning(f"Unsupported system for desktop notifications: {system}")
                
        except Exception as e:
            logger.error(f"Error sending desktop notification: {e}")
    
    async def _windows_notification(self, title: str, message: str):
        try:
            import win10toast
            toaster = win10toast.ToastNotifier()
            toaster.show_toast(title, message, duration=5)
        except ImportError:
            logger.error("win10toast not installed. Install with: pip install win10toast")
    
    async def _macos_notification(self, title: str, message: str):
        import subprocess
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(["osascript", "-e", script])
    
    async def _linux_notification(self, title: str, message: str):
        import subprocess
        subprocess.run(["notify-send", title, message])
