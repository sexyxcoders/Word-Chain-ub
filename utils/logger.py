import logging
from pathlib import Path
from datetime import datetime

class CustomLogger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup()
        return cls._instance
    
    def _setup(self):
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger("wordle_bot")
        self.logger.setLevel(logging.INFO)
        
        # File handler
        fh = logging.FileHandler(
            log_dir / f"bot_{datetime.now().strftime('%Y%m%d')}.log"
        )
        fh.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter('%(levelname)-8s | %(message)s'))
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
    
    def get_logger(self, name: str = "wordle_bot"):
        return self.logger.getChild(name)

# Singleton instance
logger = CustomLogger().get_logger()