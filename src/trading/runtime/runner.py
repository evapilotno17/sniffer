import threading, time
from utils.log import logger

class StrategyRunner(threading.Thread):
    """Encapsulates a single strategy running in its own thread."""
    def __init__(self, strategy, interval_s: int):
        super().__init__(daemon=True)
        self.strategy = strategy
        self.interval = interval_s
        self._running = threading.Event()
        self._running.set()               # start as running
        self._shutdown = threading.Event()

    # ----- public control methods -----
    def pause(self):    self._running.clear()
    def resume(self):   self._running.set()
    def stop(self):     self._shutdown.set()

    def run(self):
        logger.info(f"STARTED STRATEGY {self.strategy.state.name}")
        while not self._shutdown.is_set():
            if self._running.is_set():
                self.strategy.run_once()
            # block in smaller chunks to allow responsive pause/stop
            for _ in range(int(self.interval*10)):
                if self._shutdown.is_set(): break
                time.sleep(0.1)
        logger.info(f"STOPPED STRATEGY {self.strategy.state.name}")
