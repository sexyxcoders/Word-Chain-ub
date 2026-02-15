import asyncio
import random
from typing import Tuple
from config import Config
from .logger import logger

class AntiBanDelay:
    """Human-like delay generator with anti-ban patterns"""
    
    @staticmethod
    async def between_actions(min_sec: float = None, max_sec: float = None) -> float:
        """Delay between game actions (guesses, clicks)"""
        min_sec = min_sec or Config.MIN_DELAY
        max_sec = max_sec or Config.MAX_DELAY
        
        # Add micro-variation for human-like behavior
        base_delay = random.uniform(min_sec, max_sec)
        variation = random.uniform(-0.3, 0.5)  # Small jitter
        total = max(0.5, base_delay + variation)
        
        logger.debug(f"Delaying {total:.2f}s before next action")
        await asyncio.sleep(total)
        return total
    
    @staticmethod
    async def between_games() -> float:
        """Cooldown between completed games"""
        delay = Config.COOLDOWN_BETWEEN_GAMES + random.uniform(10, 40)
        logger.info(f"Cooldown between games: {delay:.0f}s")
        await asyncio.sleep(delay)
        return delay
    
    @staticmethod
    async def on_error(retry_count: int) -> float:
        """Exponential backoff on errors"""
        delay = min(300, (2 ** retry_count) * random.uniform(1, 2))
        logger.warning(f"Error delay: {delay:.1f}s (retry #{retry_count})")
        await asyncio.sleep(delay)
        return delay
    
    @staticmethod
    async def human_typing(length: int) -> float:
        """Simulate human typing speed for inputs"""
        chars_per_sec = random.uniform(8, 15)  # Realistic typing speed
        delay = length / chars_per_sec
        await asyncio.sleep(delay)
        return delay