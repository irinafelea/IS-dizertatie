import time


class Progress:
    """
    Tracks and prints periodic LNS progress updates
    """
    def __init__(self, name: str, every: int = 10):
        """
        Initializes a progress tracker

        Args:
            name: Printed progress label
            every: Logging interval in iterations

        Returns:
            None
        """
        self.name = name
        self.every = every
        self.t0 = time.perf_counter()
        self.last = self.t0
        self.i = 0
        self.best = None

    def tick(self, *, best_score: int, cur_score: int, accepted: bool, removed_k: int):
        """
        Updates and prints the progress state when the interval is reached

        Args:
            best_score: Best score seen so far
            cur_score: Current score
            accepted: Whether the last move was accepted
            removed_k: Number of removed tasks

        Returns:
            None
        """
        self.i += 1
        if self.best is None or best_score < self.best:
            self.best = best_score

        if self.i % self.every != 0:
            return

        now = time.perf_counter()
        dt = now - self.last
        total = now - self.t0
        it_s = self.every / max(dt, 1e-9)
        self.last = now

        print(
            f"[{self.name}] it={self.i}  it/s={it_s:.2f}  "
            f"best={best_score}  cur={cur_score}  "
            f"acc={'Y' if accepted else 'n'}  removed={removed_k}  t={total:.1f}s"
        )
