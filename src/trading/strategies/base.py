import abc
from typing import Dict, Any, List
from utils import logger
from pydantic import BaseModel
import copy
import time

"""
    -> every strategy has a rebalance method which runs every self.update_time seconds
    -> a strategy can update its own "update time" within its rebalance method
    -> a "portfolio" object represents a set of positions. i will simply maintain it as a dict within every strategy.
    -> a strategy can be initialized with an existing portfolio object or a portfolio id (to load from db)


    how do we rebalance our strategy? how is a rebalance even defined?
        a rebalance acts on a portfolio - or rather a set of positions -> which is essentially a dict of asset_id -> amount. we simply do some transform on this vector to get to a new vector in position-space.


    Now programmatically, there's three processes:
        1. modification of the internal positions dict
        2. modification of the on-chain/in-bank dict (through some api) 
        3. modification of OUR sqlite db of positions

    These three processes should be handled separately.
        1. REBALANCE: the subclass should import the rebalance method from the base class and implement it -> it takes in a dict and returns a dict.
        2. EXECUTE: the subclass should import the execute method from the base class and implement it. it takes in the previous dict, the modified dict and executes the trades with some api
        3. UPDATE_DB: the subclass should import the update_db method from the base class and implement it. it takes in the modified dict and updates whatever db

    Our run function looks like this:
        def run(self):
            while True:
                self.rebalance()
                self.execute()
                self.update_db()
                time.sleep(self.spec.rebalance_interval_seconds)
  
        
"""



class BaseStrategy(abc.ABC):
    """
    * execute (…) must NOW return an “execution report”.
    * update_db (…) receives that report so it can persist whatever happened.
    """
    def __init__(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def rebalance(self, positions: Dict[str, Any]) -> List[Any]:
        pass

    @abc.abstractmethod
    def execute(self, prev_positions: Dict[str, Any], orders_to_place: List[Any]) -> List[Any]:
        pass

    @abc.abstractmethod
    def update_state(self, execution_report: List[Any]):
        """
            updates the strategy's state with the execution report. an execution report is a list of executed orders
        """
        pass

    def run_once(self):
        """Runs a single rebalance-execute-update cycle. If a strategy wants more granular control over its loop, it can modify this method."""
        prev_positions = copy.deepcopy(self.positions)
        
        orders_to_place = self.rebalance(prev_positions)

        if orders_to_place:
            execution_report = self.execute(
                orders_to_place=orders_to_place
            )
            self.update_state(execution_report)

        logger.info(f"rebalance cycle for {self.state.name} complete.")


    def run(self):
        while True:
            self.run_once()
            logger.info(f"sleeping for {self.state.rebalance_interval_seconds} seconds...")
            time.sleep(self.state.rebalance_interval_seconds)