import json
import random
from pathlib import Path
from typing import List, Set, Tuple
from config import Config
from .state import GameState, LetterState
from .logger import logger

class WordleSolver:
    def __init__(self):
        self.words = self._load_wordlist()
        self.reset()
    
    def _load_wordlist(self) -> List[str]:
        path = Path(Config.DATA_DIR) / "allWords.json"
        if not path.exists():
            # Fallback to minimal wordlist
            return ["crane", "slate", "audio", "stare", "roate", "teary"]
        with open(path) as f:
            data = json.load(f)
            return [w.lower() for w in data.get("words", []) if len(w) == Config.WORD_LENGTH]
    
    def reset(self):
        self.possible_words = set(self.words)
        self.correct_positions = [None] * Config.WORD_LENGTH
        self.present_letters = set()
        self.absent_letters = set()
        self.known_letter_counts = {}  # letter -> min count
    
    def update_with_result(self, word: str, states: List[LetterState]):
        """Update constraints based on guess result"""
        # Track letter frequencies in this guess
        word_counts = {}
        for c in word:
            word_counts[c] = word_counts.get(c, 0) + 1
        
        # First pass: handle CORRECT letters (gives exact position + count info)
        for i, (char, state) in enumerate(zip(word, states)):
            if state == LetterState.CORRECT:
                self.correct_positions[i] = char
                self.present_letters.add(char)
                # This confirms at least this many occurrences
                self.known_letter_counts[char] = max(
                    self.known_letter_counts.get(char, 0),
                    word_counts[char]
                )
        
        # Second pass: handle PRESENT letters (wrong position but exists)
        for i, (char, state) in enumerate(zip(word, states)):
            if state == LetterState.PRESENT:
                self.present_letters.add(char)
                # If not already counted as correct, this adds to minimum count
                if self.correct_positions[i] != char:
                    self.known_letter_counts[char] = max(
                        self.known_letter_counts.get(char, 0),
                        word_counts[char]
                    )
        
        # Third pass: handle ABSENT letters (only absent if not elsewhere present/correct)
        for char, state in zip(word, states):
            if state == LetterState.ABSENT:
                # Only mark absent if we don't know it exists elsewhere
                if char not in self.present_letters and char not in self.correct_positions:
                    self.absent_letters.add(char)
    
    def filter_possible_words(self):
        """Filter word list based on current constraints"""
        new_possible = set()
        
        for word in self.possible_words:
            if not self._word_meets_constraints(word):
                continue
            new_possible.add(word)
        
        if not new_possible:
            logger.warning("No words match constraints! Resetting solver...")
            self.reset()
            return
        
        self.possible_words = new_possible
        logger.debug(f"Possible words after filter: {len(self.possible_words)}")
    
    def _word_meets_constraints(self, word: str) -> bool:
        # Check correct positions
        for i, required_char in enumerate(self.correct_positions):
            if required_char and word[i] != required_char:
                return False
        
        # Check absent letters
        for absent in self.absent_letters:
            if absent in word:
                return False
        
        # Check present letters exist somewhere
        for present in self.present_letters:
            if present not in word:
                return False
        
        # Check letter counts
        from collections import Counter
        word_counter = Counter(word)
        for letter, min_count in self.known_letter_counts.items():
            if word_counter.get(letter, 0) < min_count:
                return False
        
        return True
    
    def get_next_guess(self, game_state: GameState) -> str:
        """Get optimal next guess based on strategy"""
        if not game_state.guesses:
            # First guess: use statistically optimal starter
            starters = ["crane", "slate", "roate", "audio"]
            return random.choice([w for w in starters if w in self.possible_words] or list(self.possible_words))
        
        # Update constraints with latest result
        last_guess = game_state.guesses[-1]
        self.update_with_result(last_guess.word, last_guess.states)
        self.filter_possible_words()
        
        if not self.possible_words:
            logger.error("No possible words! Using random fallback")
            return random.choice(self.words)
        
        # Strategy: minimize max remaining words (entropy)
        return self._select_optimal_guess()
    
    def _select_optimal_guess(self) -> str:
        """Simple heuristic: pick word that maximizes letter diversity"""
        if len(self.possible_words) <= 2:
            return next(iter(self.possible_words))
        
        # Score words by unique letter coverage
        def score_word(w: str) -> int:
            unique = len(set(w))
            # Bonus for letters not yet tried
            novelty = sum(1 for c in set(w) if c not in self.present_letters and c not in self.absent_letters)
            return unique * 10 + novelty
        
        candidates = list(self.possible_words)
        candidates.sort(key=score_word, reverse=True)
        
        # Add randomness to avoid predictability (anti-ban)
        top_n = min(5, len(candidates))
        return random.choice(candidates[:top_n])