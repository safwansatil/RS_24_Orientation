"""Match state and validation for both board and keyboard play."""
from dataclasses import dataclass, field


ROUND_LIMIT = 7


@dataclass
class Match:
    names: tuple[str, str]
    scores: list[int] = field(default_factory=lambda: [0, 0])
    number: int = 0
    token: int = 0
    phase: str = "release"
    outcome: str = ""
    player: int = 0
    elapsed: int = 0
    rounds: list[int] = field(default_factory=list)

    @property
    def winner(self):
        left, right = self.scores
        return 1 if left > right else 2 if right > left else 0

    def arm(self, token):
        self.number += 1
        self.token = token
        self.phase = "release"
        self.outcome = ""
        self.player = self.elapsed = 0

    def receive(self, message):
        """Apply one message for the current round. Return whether it changed."""
        parts = message.split(",")
        if len(parts) < 2 or parts[1] != str(self.token):
            return False

        allowed = {"release": ("WAIT", "wait"), "wait": ("GO", "go")}
        if len(parts) == 2 and self.phase in allowed:
            expected, next_phase = allowed[self.phase]
            if parts[0] == expected:
                self.phase = next_phase
                return True

        if len(parts) != 5 or parts[0] != "RESULT":
            return False
        _, _, outcome, player, elapsed = parts
        if not elapsed.isascii() or not elapsed.isdecimal():
            return False
        if outcome == "WIN":
            valid = self.phase == "go" and player in {"1", "2"} and int(elapsed) <= 3000
        elif outcome == "EARLY":
            valid = self.phase in {"wait", "go"} and player in {"0", "1", "2"}
        elif outcome in {"TIE", "MISS"}:
            valid = self.phase == "go" and player == "0"
        else:
            return False
        if not valid:
            return False

        self.outcome, self.player, self.elapsed = outcome, int(player), int(elapsed)
        if outcome == "WIN":
            self.scores[self.player - 1] += 1
        self.rounds.append(self.player if outcome == "WIN" else 0)
        self.phase = "finished" if len(self.rounds) == ROUND_LIMIT else "result"
        return True
