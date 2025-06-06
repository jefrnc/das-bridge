"""Ejemplo de uso del sistema de notificaciones."""

import asyncio
import os
from dotenv import load_dotenv
from das_trader import DASTraderClient, OrderSide, OrderType
from das_trader.notifications import NotificationManager

# Cargar variables de entorno
load_dotenv()


async def main():
    """Ejemplo de trading con notificaciones."""
    
    # Configuración de notificaciones desde variables de entorno
    notification_config = {
        "ENABLE_NOTIFICATIONS": os.getenv("ENABLE_NOTIFICATIONS", "false").lower() == "true",
        "NOTIFICATION_TYPE": os.getenv("NOTIFICATION_TYPE", "email"),
        
        # Email
        "EMAIL_SMTP_HOST": os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com"),
        "EMAIL_SMTP_PORT": int(os.getenv("EMAIL_SMTP_PORT", "587")),
        "EMAIL_USERNAME": os.getenv("EMAIL_USERNAME"),
        "EMAIL_PASSWORD": os.getenv("EMAIL_PASSWORD"),
        "EMAIL_TO_ADDRESSES": os.getenv("EMAIL_TO_ADDRESSES", "").split(","),
        "EMAIL_USE_TLS": True,
        
        # Discord
        "DISCORD_WEBHOOK_URL": os.getenv("DISCORD_WEBHOOK_URL"),
        
        # Telegram
        "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
        "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID"),
        
        # Pushover
        "PUSHOVER_USER_KEY": os.getenv("PUSHOVER_USER_KEY"),
        "PUSHOVER_APP_TOKEN": os.getenv("PUSHOVER_APP_TOKEN"),
        
        # Slack
        "SLACK_WEBHOOK_URL": os.getenv("SLACK_WEBHOOK_URL"),
        
        # Webhook personalizado
        "CUSTOM_WEBHOOK_URL": os.getenv("CUSTOM_WEBHOOK_URL"),
        "WEBHOOK_HEADERS": {"Authorization": f"Bearer {os.getenv('WEBHOOK_AUTH_TOKEN')}"},
        
        # Desktop
        "ENABLE_DESKTOP_NOTIFICATIONS": True,
        "DESKTOP_NOTIFICATION_SOUND": True,
    }
    
    # Crear gestor de notificaciones
    notifications = NotificationManager(notification_config)
    
    # Crear cliente DAS Trader
    client = DASTraderClient()
    
    # Callbacks con notificaciones
    async def on_order_filled(order):
        """Notificar cuando se complete una orden."""
        await notifications.send_order_notification(order, "filled")
        print(f"Orden completada: {order.symbol} - Notificación enviada")
    
    async def on_order_rejected(order):
        """Notificar cuando se rechace una orden."""
        await notifications.send_order_notification(order, "rejected")
        print(f"Orden rechazada: {order.symbol} - Notificación enviada")
    
    async def on_position_update(position):
        """Notificar cambios importantes en posiciones."""
        # Notificar solo si hay ganancia/pérdida significativa
        if abs(position.pnl_percent) > 2.0:  # Mayor a 2%
            await notifications.send_position_notification(position, "updated")
            print(f"Posición {position.symbol}: {position.pnl_percent:.2f}% - Notificación enviada")
    
    try:
        # Conectar al API
        await client.connect(
            os.getenv("DAS_USERNAME"),
            os.getenv("DAS_PASSWORD"),
            os.getenv("DAS_ACCOUNT")
        )
        
        # Registrar callbacks
        client.orders.register_callback("order_filled", on_order_filled)
        client.orders.register_callback("order_rejected", on_order_rejected)
        client.positions.register_callback("position_updated", on_position_update)
        
        # Notificación de conexión exitosa
        await notifications.send_notification(
            "DAS Trader Conectado",
            "Bot de trading conectado exitosamente al API de DAS Trader",
            "success"
        )
        
        print("Conectado a DAS Trader con notificaciones habilitadas")
        print(f"Tipo de notificación: {notification_config['NOTIFICATION_TYPE']}")
        
        # Ejemplo: Enviar una orden de prueba
        if input("¿Enviar orden de prueba? (y/n): ").lower() == 'y':
            symbol = input("Símbolo (ej: AAPL): ").upper() or "AAPL"
            
            try:
                order_id = await client.send_order(
                    symbol=symbol,
                    side=OrderSide.BUY,
                    quantity=1,  # Solo 1 acción para prueba
                    order_type=OrderType.MARKET
                )
                
                print(f"Orden enviada: {order_id}")
                
                # Notificación de orden enviada
                await notifications.send_notification(
                    "Orden Enviada",
                    f"Orden de compra enviada para {symbol} - ID: {order_id}",
                    "info"
                )
                
            except Exception as e:
                await notifications.send_notification(
                    "Error en Orden",
                    f"Error al enviar orden para {symbol}: {str(e)}",
                    "error"
                )
        
        # Monitorear por 30 segundos
        print("\\nMonitoreando por 30 segundos...")
        await asyncio.sleep(30)
        
        # Ejemplo de alerta de precio
        quote = await client.get_quote("AAPL")
        if quote:
            await notifications.send_alert(
                "AAPL", 
                float(quote.last), 
                "alcanzó"
            )
        
    except Exception as e:
        # Notificación de error
        await notifications.send_notification(
            "Error de Conexión",
            f"Error conectando a DAS Trader: {str(e)}",
            "error"
        )
        print(f"Error: {e}")
    
    finally:
        # Notificación de desconexión
        await notifications.send_notification(
            "DAS Trader Desconectado",
            "Bot de trading desconectado del API de DAS Trader",
            "info"
        )
        await client.disconnect()


def test_notifications():
    """Probar diferentes tipos de notificaciones."""
    print("\\n=== CONFIGURACIÓN DE NOTIFICACIONES ===")
    print("Tipos disponibles:")
    print("1. email - Notificaciones por correo electrónico")
    print("2. discord - Mensajes a canal de Discord")
    print("3. telegram - Mensajes de Telegram Bot")
    print("4. pushover - Notificaciones push móviles")
    print("5. slack - Mensajes a Slack")
    print("6. webhook - Webhook personalizado")
    print("7. desktop - Notificaciones de escritorio")
    
    print("\\nPara configurar:")
    print("1. Copia .env.example a .env")
    print("2. Completa las variables según el tipo de notificación que quieras")
    print("3. Ejecuta este ejemplo")
    
    print("\\nEjemplos de configuración:")
    print("\\n--- DISCORD ---")
    print("1. Ve a tu servidor Discord > Configuración > Webhooks")
    print("2. Crea un nuevo webhook y copia la URL")
    print("3. Añade a .env: DISCORD_WEBHOOK_URL=tu_webhook_url")
    
    print("\\n--- TELEGRAM ---")
    print("1. Habla con @BotFather en Telegram")
    print("2. Crea un bot con /newbot y guarda el token")
    print("3. Inicia chat con tu bot y envía /start")
    print("4. Ve a https://api.telegram.org/botTU_TOKEN/getUpdates")
    print("5. Copia el chat_id de la respuesta")
    
    print("\\n--- PUSHOVER ---")
    print("1. Registrate en https://pushover.net")
    print("2. Crea una app y copia el token")
    print("3. Copia tu user key del dashboard")
    
    print("\\n--- EMAIL ---")
    print("1. Usa tu email favorito (Gmail, Outlook, etc.)")
    print("2. Para Gmail: habilita 2FA y crea una App Password")
    print("3. Configura SMTP_HOST, PORT, USERNAME, PASSWORD")


if __name__ == "__main__":
    # Si no hay variables de entorno, mostrar ayuda
    if not os.getenv("DAS_USERNAME"):
        test_notifications()
    else:
        asyncio.run(main())