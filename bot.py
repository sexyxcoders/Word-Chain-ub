import asyncio
import signal
import sys
from pathlib import Path
from telegram.ext import Application
from config import Config
from utils.logger import logger
from handlers.bot_handlers import register_bot_handlers
from userbot_manager import UserBotManager

async def graceful_shutdown(signal, loop, application):
    """Gracefully shutdown bot and sessions"""
    logger.info(f"Received exit signal {signal.name}...")
    
    # Disconnect all sessions gracefully
    manager = UserBotManager()
    tasks = []
    for key in list(manager.sessions.keys()):
        user_id, session_name = key.split('_')
        tasks.append(manager.disconnect_session(int(user_id), session_name))
    
    if tasks:
        logger.info(f"Disconnecting {len(tasks)} active sessions...")
        await asyncio.gather(*tasks, return_exceptions=True)
    
    # Stop bot
    await application.stop()
    await application.shutdown()
    
    logger.info("Shutdown complete")
    sys.exit(0)

def main():
    # Validate config
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Setup graceful shutdown
    loop = asyncio.get_event_loop()
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig,
            lambda s=sig: asyncio.create_task(graceful_shutdown(s, loop, application))
        )
    
    # Register handlers
    register_bot_handlers(application)
    
    # Start background cleanup task
    manager = UserBotManager()
    loop.create_task(manager.cleanup_stale_sessions())
    
    # Start bot
    logger.info("🚀 Wordle Bot starting...")
    logger.info(f"Bot: @{application.bot.username}")
    logger.info(f"Force join: {Config.FORCE_JOIN_CHAT or 'disabled'}")
    logger.info(f"Anti-ban delay: {Config.MIN_DELAY}-{Config.MAX_DELAY}s")
    
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()