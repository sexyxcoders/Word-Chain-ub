import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
    FORCE_JOIN_CHAT = os.getenv("FORCE_JOIN_CHAT", "")  # @channel username
    
    # Paths
    SESSIONS_DIR = "sessions"
    DATA_DIR = "data"
    ASSETS_DIR = "assets"
    
    # Anti-ban settings
    MIN_DELAY = float(os.getenv("MIN_DELAY", "1.5"))      # seconds between actions
    MAX_DELAY = float(os.getenv("MAX_DELAY", "3.5"))
    COOLDOWN_BETWEEN_GAMES = int(os.getenv("COOLDOWN_BETWEEN_GAMES", "120"))  # seconds
    
    # Game settings
    MAX_GUESSES = 6
    WORD_LENGTH = 5
    
    # Safety
    MAX_SESSIONS_PER_USER = 3
    SESSION_TIMEOUT = 3600  # seconds
    
    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable required")
        os.makedirs(cls.SESSIONS_DIR, exist_ok=True)
        os.makedirs(cls.DATA_DIR, exist_ok=True)