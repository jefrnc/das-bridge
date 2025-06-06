"""Demostración completa de todas las funcionalidades implementadas."""

import asyncio
import os
from dotenv import load_dotenv
from das_trader import DASTraderClient, OrderSide, OrderType, MarketDataLevel

# Cargar variables de entorno
load_dotenv()


async def demo_notifications(client):
    """Demostrar sistema de notificaciones."""
    print("=== DEMO NOTIFICACIONES ===")
    
    # Configurar notificaciones
    notification_config = {
        "ENABLE_NOTIFICATIONS": True,
        "NOTIFICATION_TYPE": "email",  # Cambiar según preferencia
        "EMAIL_SMTP_HOST": "smtp.gmail.com",
        "EMAIL_USERNAME": os.getenv("EMAIL_USERNAME"),
        "EMAIL_PASSWORD": os.getenv("EMAIL_PASSWORD"),
        "EMAIL_TO_ADDRESSES": [os.getenv("EMAIL_USERNAME")],
    }
    
    if notification_config["EMAIL_USERNAME"]:
        client.configure_notifications(notification_config)
        
        # Enviar notificación de prueba
        await client.send_notification(
            "Sistema Activado",
            "Sistema de notificaciones DAS Trader activado correctamente",
            "success"
        )
        print("✅ Notificación de prueba enviada")
    else:
        print("⚠️ Configuración de email no encontrada, omitiendo demo de notificaciones")


async def demo_orders(client):
    """Demostrar gestión avanzada de órdenes."""
    print("\\n=== DEMO ÓRDENES AVANZADAS ===")
    
    symbol = "AAPL"
    
    try:
        # Orden Market
        print(f"📊 Enviando orden MARKET para {symbol}...")
        market_order = await client.send_order(
            symbol=symbol,
            side=OrderSide.BUY,
            quantity=1,
            order_type=OrderType.MARKET
        )
        print(f"✅ Orden Market enviada: {market_order}")
        
        # Orden Limit
        print(f"📊 Enviando orden LIMIT para {symbol}...")
        limit_order = await client.send_order(
            symbol=symbol,
            side=OrderSide.BUY,
            quantity=1,
            order_type=OrderType.LIMIT,
            price=150.00
        )
        print(f"✅ Orden Limit enviada: {limit_order}")
        
        # Orden Stop Loss
        print(f"📊 Enviando orden STOP para {symbol}...")
        stop_order = await client.send_order(
            symbol=symbol,
            side=OrderSide.SELL,
            quantity=1,
            order_type=OrderType.STOP,
            stop_price=145.00
        )
        print(f"✅ Orden Stop enviada: {stop_order}")
        
        # Ver órdenes activas
        active_orders = client.get_active_orders()
        print(f"📋 Órdenes activas: {len(active_orders)}")
        
        # Cancelar todas las órdenes
        print("🚫 Cancelando todas las órdenes...")
        cancelled = await client.cancel_all_orders()
        print(f"✅ {cancelled} órdenes canceladas")
        
    except Exception as e:
        print(f"❌ Error en demo de órdenes: {e}")


async def demo_positions(client):
    """Demostrar gestión de posiciones."""
    print("\\n=== DEMO POSICIONES ===")
    
    try:
        # Refrescar posiciones
        await client.refresh_positions()
        
        # Obtener todas las posiciones
        positions = client.get_positions()
        print(f"📊 Total de posiciones: {len(positions)}")
        
        # Mostrar posiciones abiertas
        open_positions = [p for p in positions if not p.is_flat()]
        if open_positions:
            print("🔓 Posiciones abiertas:")
            for pos in open_positions:
                print(f"   {pos.symbol}: {pos.quantity} shares, "
                      f"P&L: ${pos.unrealized_pnl:.2f} ({pos.pnl_percent:.2f}%)")
        else:
            print("💰 No hay posiciones abiertas")
        
        # P&L total
        total_pnl = client.get_total_pnl()
        print(f"💹 P&L Total: ${total_pnl['total_pnl']:.2f}")
        
        # Buying Power
        bp = await client.get_buying_power()
        print(f"💵 Buying Power: ${bp['buying_power']:,.2f}")
        
    except Exception as e:
        print(f"❌ Error en demo de posiciones: {e}")


async def demo_market_data(client):
    """Demostrar market data streaming."""
    print("\\n=== DEMO MARKET DATA ===")
    
    symbols = ["AAPL", "TSLA", "MSFT"]
    
    try:
        # Suscribirse a Level 1 quotes
        for symbol in symbols:
            await client.subscribe_quote(symbol, MarketDataLevel.LEVEL1)
            print(f"📈 Suscrito a quotes de {symbol}")
        
        # Obtener quotes actuales
        for symbol in symbols:
            quote = await client.get_quote(symbol)
            if quote:
                print(f"💲 {symbol}: ${quote.last:.2f} "
                      f"(Bid: ${quote.bid:.2f}, Ask: ${quote.ask:.2f})")
        
        # Callback para quotes en tiempo real
        quote_count = [0]
        
        def on_quote_received(quote):
            quote_count[0] += 1
            if quote_count[0] <= 5:  # Solo mostrar primeras 5
                print(f"🔄 Quote update: {quote.symbol} = ${quote.last:.2f}")
        
        client.on_quote_update(on_quote_received)
        
        print("⏱️ Monitoreando quotes por 10 segundos...")
        await asyncio.sleep(10)
        
        print(f"📊 Recibidas {quote_count[0]} actualizaciones de quotes")
        
    except Exception as e:
        print(f"❌ Error en demo de market data: {e}")


async def demo_short_features(client):
    """Demostrar funcionalidades de short selling."""
    print("\\n=== DEMO SHORT FEATURES ===")
    
    symbol = "AAPL"
    
    try:
        # Información de short
        short_info = await client.get_short_info(symbol)
        print(f"🩳 {symbol} - Shortable: {short_info['shortable']}, "
              f"Rate: {short_info['rate']:.4f}%")
        
        if short_info['shortable']:
            # Inquirir precio de locate
            print(f"🔍 Consultando precio de locate para {symbol}...")
            locate_price = await client.inquire_locate_price(symbol, 100)
            print(f"📍 Locate disponible: {locate_price['available']}, "
                  f"Rate: {locate_price['rate']:.4f}%")
            
            if locate_price['available']:
                # Solicitar locate
                print(f"📝 Solicitando locate para {symbol}...")
                locate_order = await client.locate_stock(symbol, 100)
                print(f"✅ Locate order: {locate_order}")
                
                # Si el locate fue exitoso, podríamos aceptar o cancelar
                if locate_order.get('locate_id'):
                    print(f"🚫 Cancelando locate order...")
                    cancelled = await client.cancel_locate_order(locate_order['locate_id'])
                    print(f"✅ Locate cancelado: {cancelled}")
        
    except Exception as e:
        print(f"❌ Error en demo de short features: {e}")


async def demo_scripts(client):
    """Demostrar ejecución de scripts."""
    print("\\n=== DEMO SCRIPTS ===")
    
    try:
        # Cambiar símbolo en montage
        print("🖥️ Cambiando símbolo en montage...")
        result = await client.change_montage_symbol("Montage1", "TSLA")
        print(f"✅ Montage actualizado: {result}")
        
        # Ejecutar script personalizado
        print("⚙️ Ejecutando script personalizado...")
        result = await client.execute_script("Chart1", "SYMBOL MSFT")
        print(f"✅ Script ejecutado: {result}")
        
        # Script global (si tienes desktop layouts configurados)
        print("🌐 Ejecutando script global...")
        result = await client.switch_desktop("default")
        print(f"✅ Desktop cambiado: {result}")
        
    except Exception as e:
        print(f"❌ Error en demo de scripts: {e}")


async def demo_alerts(client):
    """Demostrar sistema de alertas."""
    print("\\n=== DEMO ALERTAS ===")
    
    try:
        # Obtener precio actual
        quote = await client.get_quote("AAPL")
        if quote:
            current_price = float(quote.last)
            
            # Enviar alerta personalizada
            await client.send_alert(
                "AAPL",
                current_price,
                f"alcanzó ${current_price:.2f}"
            )
            print(f"🚨 Alerta enviada para AAPL a ${current_price:.2f}")
            
            # Notificación personalizada
            await client.send_notification(
                "Precio Monitoreado",
                f"AAPL está cotizando a ${current_price:.2f}\\n"
                f"Spread: ${quote.ask - quote.bid:.2f}",
                "info"
            )
            print("📱 Notificación personalizada enviada")
        
    except Exception as e:
        print(f"❌ Error en demo de alertas: {e}")


async def main():
    """Función principal para ejecutar todas las demos."""
    print("🚀 DEMO COMPLETO - TODAS LAS FUNCIONALIDADES DAS TRADER")
    print("=" * 60)
    
    # Configurar notificaciones
    notification_config = {
        "ENABLE_NOTIFICATIONS": True,
        "NOTIFICATION_TYPE": "desktop",  # Usar desktop por defecto
        "ENABLE_DESKTOP_NOTIFICATIONS": True,
    }
    
    # Crear cliente con notificaciones
    client = DASTraderClient(
        host="localhost",
        port=9910,
        notification_config=notification_config
    )
    
    try:
        # Conectar
        print("🔌 Conectando a DAS Trader...")
        await client.connect(
            os.getenv("DAS_USERNAME", "demo_user"),
            os.getenv("DAS_PASSWORD", "demo_pass"),
            os.getenv("DAS_ACCOUNT", "demo_account")
        )
        print("✅ Conectado exitosamente!")
        
        # Ejecutar todas las demos
        await demo_notifications(client)
        await demo_positions(client)
        await demo_market_data(client)
        await demo_orders(client)
        await demo_short_features(client)
        await demo_scripts(client)
        await demo_alerts(client)
        
        print("\\n🎉 ¡Demo completo finalizado!")
        print("\\n📋 RESUMEN DE FUNCIONALIDADES DEMOSTRADAS:")
        print("   ✅ Sistema de notificaciones multi-plataforma")
        print("   ✅ Gestión completa de órdenes")
        print("   ✅ Seguimiento de posiciones y P&L")
        print("   ✅ Market data streaming en tiempo real")
        print("   ✅ Funcionalidades de short selling y locate")
        print("   ✅ Ejecución de scripts DAS")
        print("   ✅ Sistema de alertas personalizadas")
        
    except Exception as e:
        print(f"❌ Error en demo principal: {e}")
        print("\\n💡 Nota: Algunas funciones requieren DAS Trader conectado")
        print("   y configuración adecuada de credenciales en .env")
    
    finally:
        await client.disconnect()
        print("\\n👋 Desconectado de DAS Trader")


if __name__ == "__main__":
    print("🔧 Para configurar el demo:")
    print("1. Copia .env.example a .env")
    print("2. Completa las credenciales de DAS Trader")
    print("3. Opcional: configura notificaciones (email, discord, etc.)")
    print("4. Asegúrate de que DAS Trader esté ejecutándose")
    print("\\n⏳ Iniciando demo en 3 segundos...")
    
    import time
    time.sleep(3)
    
    asyncio.run(main())