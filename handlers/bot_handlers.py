from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from config import Config
from userbot_manager import UserBotManager
from utils.logger import logger
import asyncio

manager = UserBotManager()

async def check_force_join(update: Update) -> bool:
    """Verify user is member of required channel"""
    if not Config.FORCE_JOIN_CHAT:
        return True
    
    user_id = update.effective_user.id
    try:
        chat_member = await update.get_bot().get_chat_member(Config.FORCE_JOIN_CHAT, user_id)
        if chat_member.status in ['member', 'administrator', 'creator']:
            return True
        
        # Not a member - show join prompt
        await update.message.reply_text(
            f"🔒 Please join {Config.FORCE_JOIN_CHAT} to use this bot",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Join Channel", url=f"https://t.me/{Config.FORCE_JOIN_CHAT.lstrip('@')}"),
                InlineKeyboardButton("✅ Verify", callback_data="verify_join")
            ]])
        )
        return False
    except Exception as e:
        logger.error(f"Force join check failed: {e}")
        return False

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_join(update):
        return
    
    welcome_text = (
        "🎮 Wordle Bot System\n\n"
        "✅ Multi-user game sessions\n"
        "✅ Manual play/stop control\n"
        "✅ Anti-ban pacing\n"
        "✅ Session persistence\n\n"
        "Commands:\n"
        "/connect <name> - Start new session\n"
        "/disconnect <name> - Stop session\n"
        "/sessions - List active sessions\n"
        "/play <name> - Start auto-playing\n"
        "/stop <name> - Pause session\n"
    )
    
    photo_path = Path(Config.ASSETS_DIR) / "start.jpg"
    if photo_path.exists():
        await update.message.reply_photo(
            photo=open(photo_path, 'rb'),
            caption=welcome_text
        )
    else:
        await update.message.reply_text(welcome_text)

async def connect_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_join(update):
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /connect <session_name>")
        return
    
    session_name = context.args[0].lower()
    user_id = update.effective_user.id
    
    # Security: sanitize session name
    if not session_name.isalnum():
        await update.message.reply_text("Session name must be alphanumeric")
        return
    
    try:
        session = await manager.get_or_create_session(user_id, session_name)
        await update.message.reply_text(
            f"✅ Session '{session_name}' connected!\n"
            f"Use /play {session_name} to start auto-playing"
        )
        logger.info(f"User {user_id} connected session {session_name}")
    except Exception as e:
        logger.error(f"Connect failed for {user_id}: {e}")
        await update.message.reply_text(f"❌ Connection failed: {str(e)}")

async def disconnect_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_join(update):
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /disconnect <session_name>")
        return
    
    session_name = context.args[0].lower()
    user_id = update.effective_user.id
    
    success = await manager.disconnect_session(user_id, session_name)
    if success:
        await update.message.reply_text(f"✅ Session '{session_name}' disconnected")
        logger.info(f"User {user_id} disconnected session {session_name}")
    else:
        await update.message.reply_text(f"⚠️ Session '{session_name}' not found or already disconnected")

async def sessions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_join(update):
        return
    
    user_id = update.effective_user.id
    sessions = manager.get_user_sessions(user_id)
    
    if not sessions:
        await update.message.reply_text("📭 No active sessions")
        return
    
    text = "📋 Active Sessions:\n\n"
    for sess in sessions:
        status = "▶️ Playing" if sess.active and sess.game_state and sess.game_state.is_active() else "⏸️ Paused"
        guesses = len(sess.game_state.guesses) if sess.game_state else 0
        text += f"• {sess.session_name} | {status} | {guesses}/6 guesses\n"
    
    await update.message.reply_text(text)

async def play_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_join(update):
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /play <session_name>")
        return
    
    session_name = context.args[0].lower()
    user_id = update.effective_user.id
    key = manager.get_session_key(user_id, session_name)
    
    if key not in manager.sessions:
        await update.message.reply_text(f"Session '{session_name}' not found. Use /connect first.")
        return
    
    session = manager.sessions[key]
    
    # Cancel existing task if running
    if session.task and not session.task.done():
        session.task.cancel()
    
    # Start new game task
    session.task = asyncio.create_task(
        auto_play_game(update, context, session, session_name)
    )
    
    await update.message.reply_text(
        f"▶️ Starting auto-play for '{session_name}'\n"
        f"I'll make intelligent guesses with human-like pacing"
    )

async def stop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_force_join(update):
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /stop <session_name>")
        return
    
    session_name = context.args[0].lower()
    user_id = update.effective_user.id
    key = manager.get_session_key(user_id, session_name)
    
    if key not in manager.sessions:
        await update.message.reply_text(f"Session '{session_name}' not found")
        return
    
    session = manager.sessions[key]
    if session.task and not session.task.done():
        session.task.cancel()
        await update.message.reply_text(f"⏸️ Auto-play stopped for '{session_name}'")
    else:
        await update.message.reply_text(f"⚠️ No active game in '{session_name}'")

async def auto_play_game(update: Update, context: ContextTypes.DEFAULT_TYPE, session: UserSession, session_name: str):
    """Main game loop with anti-ban pacing"""
    from core.parser import GameResponseParser
    from utils.delays import AntiBanDelay
    
    try:
        # Start new game
        game_id = f"{session.user_id}_{session_name}_{int(time.time())}"
        session.start_new_game(game_id)
        
        for turn in range(1, Config.MAX_GUESSES + 1):
            # Get next guess from solver
            guess = session.solver.get_next_guess(session.game_state)
            logger.info(f"Session {session_name}: Turn {turn} - Guessing '{guess}'")
            
            # Simulate human typing delay
            await AntiBanDelay.human_typing(len(guess))
            
            # TODO: INTEGRATION POINT - Send guess to game UI
            # Example placeholder:
            # await game_ui.send_guess(guess)
            
            await update.message.reply_text(
                f"🔤 [{session_name}] Turn {turn}: `{guess}`",
                parse_mode="Markdown"
            )
            
            # Wait for game feedback (simulated here)
            await AntiBanDelay.between_actions()
            
            # TODO: INTEGRATION POINT - Get game feedback
            # Example placeholder:
            # feedback = await game_ui.get_feedback()
            feedback = simulate_feedback(guess, turn)  # REMOVE IN PRODUCTION
            
            # Parse feedback
            result = GameResponseParser.parse_emoji_grid(feedback, guess, turn)
            if not result:
                logger.error(f"Failed to parse feedback for '{guess}'")
                await update.message.reply_text(f"⚠️ Couldn't parse game feedback for '{guess}'")
                break
            
            # Update game state
            session.update_game(result)
            
            # Show progress
            progress = "".join([
                "🟩" if s == LetterState.CORRECT else
                "🟨" if s == LetterState.PRESENT else "⬛"
                for s in result.states
            ])
            await update.message.reply_text(
                f"📊 [{session_name}] {progress} ({guess})"
            )
            
            # Check win/loss
            if result.is_win():
                session.finish_game(guess)
                await update.message.reply_text(
                    f"🎉 [{session_name}] Solved in {turn} turns!\n"
                    f"Target: {guess.upper()}"
                )
                await AntiBanDelay.between_games()
                return
            
            if turn == Config.MAX_GUESSES:
                # Extract target word if available
                target = GameResponseParser.extract_target_word(feedback) or "unknown"
                session.finish_game(target)
                await update.message.reply_text(
                    f"❌ [{session_name}] Failed to solve\n"
                    f"Target: {target.upper()}"
                )
                await AntiBanDelay.between_games()
                return
            
            # Anti-ban delay between guesses
            await AntiBanDelay.between_actions()
    
    except asyncio.CancelledError:
        logger.info(f"Game task cancelled for session {session_name}")
        session.active = False
        await update.message.reply_text(f"⏹️ [{session_name}] Game paused")
        raise
    except Exception as e:
        logger.error(f"Game error in session {session_name}: {e}", exc_info=True)
        await update.message.reply_text(f"❌ [{session_name}] Error: {str(e)}")
        session.active = False

# Simulated feedback for demo (REMOVE IN PRODUCTION)
def simulate_feedback(guess: str, turn: int) -> str:
    """Simulate game feedback - REPLACE with actual game integration"""
    target = "crane"  # Demo target word
    states = []
    
    for i, char in enumerate(guess):
        if char == target[i]:
            states.append('🟩')
        elif char in target:
            states.append('🟨')
        else:
            states.append('⬛')
    
    return "".join(states)

# Handler registration
def register_bot_handlers(application):
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("connect", connect_handler))
    application.add_handler(CommandHandler("disconnect", disconnect_handler))
    application.add_handler(CommandHandler("sessions", sessions_handler))
    application.add_handler(CommandHandler("play", play_handler))
    application.add_handler(CommandHandler("stop", stop_handler))