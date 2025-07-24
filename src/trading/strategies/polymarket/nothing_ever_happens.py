import os
from typing import Any, Dict, List, Union

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel

from utils.log import logger
from utils.runtime_utils import footprint

from trading.strategies.polymarket.base import (
    MarketBuy,
    MarketSell,
    PolymarketStrategy,
    StrategyState,
)
from py_clob_client.clob_types import BookParams


load_dotenv()
"""
    'but what if-?'
    'it won't happen'


    nothing ever happens. 
    so why not buy all "NO"s on polymarket? what could go wrong?

    i don't feel like writing down a pydantic model for the position object. So i'm gonna use a dct instead. the dict will be structured like this:
    
    self.positions = {
        'asset_id': {
            'event_id': ...,
            'amount': ...,
            'avg_price': ...,
        }
    }

    NOTE: when the strategy cashes out a position, it will NOT make any actual sell request.
    cash out == we have won this position AND it'll be redeemed by ME separately.
"""


# TODO: have a config for every strategy which provides the option to use and manage global portfolio exposure
class SpecConfig(BaseModel):
    look_back_days: int = 6 * 30
    minimum_volume: float = 100000
    minimum_liquidity: float = 1000
    limit: int = 500
    days_to_end: int = None
    maximum_spread: float = 0.1
    price_lower_bound: float = 0.1
    price_upper_bound: float = 0.9
    target_price: float = None
    minimum_position_size: float = 100
    panic_exit_price: float = 0.45
    cash_out_price: float = 0.99
    sell_on_cash_out: bool = False
    consider_global_exposure: bool = True # do we look at JUST this srategies exposure or my total exposure wrt an event?


# TODO: calculate corelation between events and make connected components before entering -> else we end up entering 5 positions which all depend on the epstein files NOT being released
class NothingEverHappens(PolymarketStrategy):

    @footprint()
    def __init__(self, state: StrategyState, SessionFactory = None):
        super().__init__(state, SessionFactory)

    @footprint()
    def get_candidate_markets(self):
        logger.info("retrieving candidate markets..")
        cands = self.get_recent_markets(
            look_back_days=self.state.spec['look_back_days'],
            minimum_volume=self.state.spec['minimum_volume'],
            minimum_liquidity=self.state.spec['minimum_liquidity'],
            limit=self.state.spec['limit'],
            days_to_end=self.state.spec['days_to_end']
        )
        logger.info("cleaning market data..")

        # clean and filter candidate markets
        msk = (cands['outcomePrices1'] < cands['outcomePrices2'])
        cands['expensivePrice'] = np.maximum(cands['outcomePrices1'], cands['outcomePrices2'])
        cands['expensiveToken'] = cands['clobTokenIds1']
        cands.loc[msk, 'expensiveToken'] = cands['clobTokenIds2'][msk]
        cands['expensiveBet'] = cands['outcomes1']
        cands.loc[msk, 'expensiveBet'] = cands['outcomes2'][msk]
        cands['eventCount'] = cands['events'].apply(lambda i: len(i))
        cands = cands[cands['eventCount'] == 1]
        cands = cands[cands['spread'] <= self.state.spec['maximum_spread']].reset_index()

        target_price = self.state.spec.get('target_price') or (self.state.spec['price_lower_bound'] + self.state.spec['price_upper_bound']) / 2

        def select_row(grp):
            msk = (
                (grp['expensiveBet'] == 'No') &
                (~pd.isnull(grp['expensivePrice'])) &
                (grp['expensivePrice'] <= self.state.spec['price_upper_bound']) &
                (grp['expensivePrice'] >= self.state.spec['price_lower_bound'])
            )
            if not msk.any():
                return pd.DataFrame()

            _cands = grp[msk]
            row = _cands.loc[[_cands['expensivePrice'].sub(target_price).abs().idxmin()]]

            # add the group key manually (we can get it from the group index)
            row['event_id'] = grp.name
            return row


        final_cands = (
            cands.groupby('event_id', group_keys=False)
                .apply(select_row, include_groups=False)
                .reset_index(drop=True)
        )

        return final_cands

    @footprint()
    def rebalance(self, positions: Dict[str, Dict[str, Any]]) -> List[Union[MarketBuy, MarketSell]]:
        logger.info("rebalancing portfolio...")
        logger.info("retrieving candidate markets..")
        
        final_cands = self.get_candidate_markets()

        if final_cands.shape[0] == 0:
            return []

        logger.info(f"no. of candidates: {final_cands.shape[0]}")
        logger.info("retrieving user positions..")

        # these are NOT the positions of THIS portfolio -> they are TOTAL positions on polymarket
        global_positions = self.get_user_positions().to_dict('records')

        cur_prices = self.clob_client.get_prices(
            [
                BookParams(token_id = i.token_id, side="BUY")
                for i in positions.values()
            ] 
        ) if len(positions) else {}

        # the clob client returns get_prices as a dict: {token_id: {side: price}}
        # i now update our in-memory positions
        for k, v in cur_prices.items():
            positions[k].cur_price = float(v['BUY'])

        
        global_event_exposure = set(i["eventSlug"] for i in global_positions)
        local_event_exposure = set(pos.event_id for pos in positions.values())

        orders_to_place = []
        cash_balance = self.state.cash_usd


        # positions which we'll cash out (already resolved/close to resolution)
        for pos in positions.values():
            if pos.cur_price > self.state.spec['cash_out_price']:
                orders_to_place.append(
                    MarketSell(token_id=pos.token_id, amount_shares=pos.amount, expected_price=pos.cur_price, event_id=pos.event_id, virtual=True)
                    # here, virtual=True tells the downstream executor - do NOT send an actual sell order. 
                )

            if pos.cur_price < self.state.spec['panic_exit_price']:
                orders_to_place.append(
                    MarketSell(token_id=pos.token_id, amount_shares=pos.amount, expected_price=pos.cur_price, event_id=pos.event_id)
                )


        existing_exposure = (global_event_exposure | local_event_exposure) if self.state.spec['consider_global_exposure'] else local_event_exposure

        logger.info(f"local_event_exposure: {local_event_exposure}")
        logger.info(f"global_event_exposure: {global_event_exposure}")

        # we don't wanna buy into events we already have exposure to
        entry_cands = final_cands[~final_cands['event_id'].isin(existing_exposure)]
        logger.info(f"no. of entry candidates: {entry_cands.shape[0]}")

        # split cash between all entry candidates
        if not entry_cands.empty:
            cash_per_cand = max(cash_balance / entry_cands.shape[0], self.state.spec['minimum_position_size'])
            for _, row in entry_cands.iterrows():
                orders_to_place.append(MarketBuy(
                    token_id=row['expensiveToken'], 
                    amount_usd=cash_per_cand, 
                    expected_price=row['expensivePrice'], 
                    event_id=row['event_id'],
                    condition_id=row['condition_id'],
                    slug=row['slug'],
                    end_date=row['end_date']
                ))

        return orders_to_place
