import uuid
from runtime.runner import StrategyRunner

class StrategyManager:
    def __init__(self):
        self._runners: dict[str, StrategyRunner] = {}

    # ---------- CRUD ----------
    def create(self, strategy_cls, state, session_factory):
        strategy = strategy_cls(state=state, SessionFactory=session_factory)
        runner = StrategyRunner(strategy, interval_s=state.rebalance_interval_seconds)
        runner_id = str(uuid.uuid4())
        self._runners[runner_id] = runner
        runner.start()
        return runner_id

    def list(self):
        return {rid: {"name": r.strategy.state.name,
                      "alive": r.is_alive(),
                      "paused": not r._running.is_set()}
                for rid, r in self._runners.items()}

    def _get(self, rid):          # helper
        if rid not in self._runners:
            raise KeyError(f"No strategy {rid}")
        return self._runners[rid]

    def pause(self, rid):   self._get(rid).pause()
    def resume(self, rid):  self._get(rid).resume()
    def stop(self, rid):    self._get(rid).stop()
