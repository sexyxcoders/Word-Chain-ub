from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum
import json
import time

class LetterState(Enum):
    CORRECT = "correct"      # Green
    PRESENT = "present"      # Yellow
    ABSENT = "absent"        # Gray
    UNKNOWN = "unknown"

@dataclass
class GuessResult:
    word: str
    states: List[LetterState]
    turn: int
    
    def is_win(self) -> bool:
        return all(s == LetterState.CORRECT for s in self.states)

@dataclass
class GameState:
    game_id: str
    started_at: float = field(default_factory=time.time)
    guesses: List[GuessResult] = field(default_factory=list)
    solved: bool = False
    failed: bool = False
    target_word: Optional[str] = None  # Only populated after win/loss
    
    def add_guess(self, result: GuessResult):
        self.guesses.append(result)
        if result.is_win():
            self.solved = True
        elif len(self.guesses) >= 6:
            self.failed = True
    
    def is_active(self) -> bool:
        return not (self.solved or self.failed)
    
    def to_dict(self) -> Dict:
        return {
            "game_id": self.game_id,
            "started_at": self.started_at,
            "guesses": [
                {
                    "word": g.word,
                    "states": [s.value for s in g.states],
                    "turn": g.turn
                } for g in self.guesses
            ],
            "solved": self.solved,
            "failed": self.failed,
            "target_word": self.target_word
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GameState':
        state = cls(game_id=data["game_id"], started_at=data["started_at"])
        state.guesses = [
            GuessResult(
                word=g["word"],
                states=[LetterState(s) for s in g["states"]],
                turn=g["turn"]
            ) for g in data["guesses"]
        ]
        state.solved = data["solved"]
        state.failed = data["failed"]
        state.target_word = data.get("target_word")
        return state