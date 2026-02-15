import re
from typing import List, Optional
from .state import LetterState, GuessResult
from .logger import logger

class GameResponseParser:
    """
    Parses game feedback from various Wordle-like UIs.
    Handles emoji patterns (🟩🟨⬛) and color-based feedback.
    """
    
    # Emoji mappings
    EMOJI_MAP = {
        '🟩': LetterState.CORRECT,
        '🟨': LetterState.PRESENT,
        '⬛': LetterState.ABSENT,
        '⬜': LetterState.ABSENT,
        '🟦': LetterState.ABSENT,  # Some variants
    }
    
    @classmethod
    def parse_emoji_grid(cls, text: str, guess_word: str, turn: int) -> Optional[GuessResult]:
        """
        Parse emoji grid feedback (e.g., "🟩🟨⬛⬛🟨")
        Returns GuessResult or None if parsing fails
        """
        # Find lines with exactly 5 emoji squares
        lines = text.split('\n')
        for line in lines:
            # Clean and extract emoji sequence
            cleaned = re.sub(r'[^\U0001F7E5-\U0001F7FF]', '', line)  # Keep only colored squares
            if len(cleaned) == 5:
                states = []
                for emoji in cleaned:
                    state = cls.EMOJI_MAP.get(emoji, None)
                    if state is None:
                        logger.warning(f"Unknown emoji '{emoji}' in feedback")
                        return None
                    states.append(state)
                
                # Validate guess length matches
                if len(guess_word) != 5:
                    logger.warning(f"Guess '{guess_word}' length mismatch")
                    return None
                
                return GuessResult(word=guess_word.lower(), states=states, turn=turn)
        
        logger.debug("No valid emoji grid found in response")
        return None
    
    @classmethod
    def detect_game_over(cls, text: str) -> bool:
        """Detect win/loss messages"""
        win_patterns = [
            r'you\s+win', r'correct', r'genius', r'master', r'victory',
            r'🎉', r'✅', r'⭐', r'you\s+solved'
        ]
        loss_patterns = [
            r'you\s+lose', r'game\s+over', r'hard\s+luck', r'the\s+word\s+was',
            r'❌', r'💣'
        ]
        
        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in win_patterns + loss_patterns)
    
    @classmethod
    def extract_target_word(cls, text: str) -> Optional[str]:
        """Try to extract the solution word from loss message"""
        # Common patterns: "The word was WORD", "Answer: WORD"
        patterns = [
            r'the\s+word\s+was\s+([a-z]{5})',
            r'answer[:\s]+([a-z]{5})',
            r'today\'s\s+word[:\s]+([a-z]{5})',
            r'it\s+was\s+([a-z]{5})'
        ]
        
        text_lower = text.lower()
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(1)
        return None