import concurrent.futures
import copy
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Union

import numpy as np
import pandas as pd

from py_clob_client.clob_types import MarketOrderArgs, OrderArgs, OrderType, BookParams  # FOK / GTK enums
from polymarket.clob_api.client import PolymarketClobClient
from polymarket.data_api.client import PolymarketDataClient, PositionRequest
from polymarket.gamma_api.client import PolymarketGammaClient, MarketRequest

from trading.datamodel.polymarket import (
    LimitOrder,
    MarketBuy,
    MarketSell,
    OrderResult,
    PolymarketPosition,
)
from trading.datamodel.strategy import StrategyState
from trading.db import polymarket as polymarket_models
from trading.db.polymarket import Portfolio, Position
from trading.strategies.base import BaseStrategy
from utils.log import logger
from utils.runtime_utils import footprint, format_datetime


# TODO: use self.state.whatever everywhere instead of self.whatever
class PolymarketStrategy(BaseStrategy):
    def __init__(self, state: Union[StrategyState, Dict], SessionFactory = None):
        # super().__init__(spec, SessionFactory)
        # not doing super.init deliberately

        if isinstance(state, dict):
            state = StrategyState(**state)
    
        logger.info("initializing polymarket api clients")
        self.data_client = PolymarketDataClient()
        self.gamma_client = PolymarketGammaClient()
        self.clob_client = PolymarketClobClient()

        self.state = state
        self.SessionFactory = SessionFactory

        if not self.state.portfolio_id:
            self.state.cash_usd = self.state.allocation_usd

        if not self.state.portfolio_id and SessionFactory:
            # create a db record for an empty portfolio
            with SessionFactory() as session:
                logger.info("creating a db record for an empty portfolio for strategy {self.state.strategy_path}: {self.state.name}")
                portfolio = Portfolio(
                    allocation_usd=self.state.allocation_usd,
                    cash_usd=self.state.allocation_usd,
                    paper=self.state.paper,
                    is_active=False,
                )
                session.add(portfolio)
                session.commit()
                self.state.portfolio_id = portfolio.id

        self.positions = dict()
        if SessionFactory:
            # load portfolio from db
            with self.SessionFactory() as session:
                logger.info("loading portfolio from db for strategy {self.state.strategy_path}: {self.state.name}")
                portfolio = session.query(Portfolio).filter_by(id=self.state.portfolio_id).first()
                if portfolio:
                    self.state.allocation_usd = portfolio.allocation_usd
                    self.state.cash_usd = portfolio.cash_usd
                    self.state.paper = portfolio.paper
                    self.state.last_rebalance_at = portfolio.last_rebalance_at

                    # load positions from db.
                    self.positions = {
                        pos.asset_id: PolymarketPosition(
                            token_id=pos.asset_id,
                            event_id=pos.event_id,
                            condition_id=pos.condition_id,
                            slug=pos.slug,
                            end_date=pos.end_date,
                            amount=pos.amount,
                            avg_price=pos.avg_price
                        )
                        for pos in session.query(Position).filter_by(portfolio_id=self.state.portfolio_id).all()
                    }

    ################## core functions ##########################
   
    
    def rebalance(self, positions: Dict[str, Dict[str, Any]]) -> List[Union[LimitOrder, MarketBuy, MarketSell]]:
        """
            should return a list of orders to place
        """
        raise NotImplementedError

    @staticmethod
    def get_virtual_order_result(order: Union[MarketBuy, MarketSell, LimitOrder]) -> OrderResult:
        """
            should return the result of an order if it were to be executed WITHOUT SLIPPAGE
        """
        if isinstance(order, MarketBuy):
            making_amount = order.amount_usd 
            taking_amount = order.amount_usd / order.expected_price
        elif isinstance(order, MarketSell):
            making_amount = order.amount_shares
            taking_amount = order.amount_shares * order.expected_price
        else:
            raise ValueError("you can't make a limit paper order T_T")
        
       
        return OrderResult(
                order=order,
                success=True,
                status='FILLED',
                makingAmount=str(making_amount),
                takingAmount=str(taking_amount)
            )
        


    def execute(self, orders_to_place: List[Union[MarketBuy, MarketSell, LimitOrder]]) -> List[OrderResult]:
        """
            Executes orders and returns the results. For paper trades, it simulates
            perfect execution with zero slippage.

            Note:
                "making amount" and "taking amount" mean DIFFERENT things for buy and sell orders.
                the "maker" is YOU. who is MAKING the trade. the taker is the guy who placed a limit order and is getting matched against your trade.
                
                for a buy order, making amount is the amount of USD you are giving up. taking amount is the amount of shares you are getting.
                for a sell order, making amount is the amount of shares you are giving up. taking amount is the amount of USD you are getting.
        """
        if not len(orders_to_place):
            logger.info("no orders to place")
            return []

        if self.state.paper:
            logger.info("paper mode, simulating execution")
            paper_results = []
            for order in orders_to_place:
                paper_results.append(self.get_virtual_order_result(order))
            return paper_results

        return self.execute_orders_in_parallel(orders_to_place)

    def update_state(self, execution_report: List[OrderResult]):
        """
            exc report is a list of "OrderResult" items. an OrderResult item is a pydantic object that looks like this in dict form:
                {'order': {'token_id': '82479753119294635275390000077165452043164711919562713911857288253230026838902',
                    'amount_usd': 3.3333333333333335,
                    'expected_price': 0.8985,
                    'event_id': 'bitcoin-price-on-july-25',
                    'condition_id': '0x7f1b31f81ebc01d946909eab08326762ee853fe48d03482ad316537b4b2638d8',
                    'slug': 'will-the-price-of-bitcoin-be-less-than-114k-on-july-25',
                    'end_date': '2025-07-25T16:00:00Z',
                    'virtual': False},
                
                'errorMsg': None,
                'orderID': None,
                'takingAmount': '3.7098868484511227',
                'makingAmount': '3.3333333333333335',
                'status': 'FILLED',
                'transactionsHashes': None,
                'success': True
                }
        """
        # 1. Update internal state (cash and positions)
        prev_asset_ids = set(self.positions.keys())
        prev_positons = copy.deepcopy(self.positions)

        for res in execution_report:
            if res.success:
                order_data = res.order
                token_id = order_data.token_id

                if isinstance(order_data, MarketBuy):
                    self.state.cash_usd -= float(res.makingAmount)
                    if token_id not in self.positions:
                        self.positions[token_id] = PolymarketPosition(
                            token_id=token_id,
                            event_id=order_data.event_id,
                            condition_id=order_data.condition_id,
                            slug=order_data.slug,
                            end_date=order_data.end_date,
                            amount=0,
                            avg_price=0,
                            cur_price=self.clob_client.get_price(token_id=token_id, side="BUY")['price']
                        )
                    
                    position = self.positions[token_id]
                    prev_total_price = position.amount * position.avg_price
                    position.amount += float(res.takingAmount)
                    position.avg_price = (prev_total_price + float(res.makingAmount)) / position.amount

                elif isinstance(order_data, MarketSell):
                    self.state.cash_usd += float(res.takingAmount)
                    assert token_id in self.positions
                    position = self.positions[token_id]
                    assert position.amount >= float(res.makingAmount)

                    if abs(position.amount - float(res.makingAmount)) < 1e-9:
                        del self.positions[token_id]
                    else:
                        prev_total_price = position.amount * position.avg_price
                        position.amount -= float(res.makingAmount)
                        position.avg_price = (prev_total_price - float(res.takingAmount)) / position.amount
                    position.cur_price = self.clob_client.get_price(token_id=token_id, side="BUY")['price']

        # 2. Update Database
        if not self.SessionFactory:
            logger.warning("SessionFactory not set, skipping DB update")
            return

        all_asset_ids = set(self.positions.keys()) | prev_asset_ids


        with self.SessionFactory() as session:

            logger.info(f"updating db for strategy {self.state.strategy_path}: {self.state.name} at time {format_datetime(datetime.now())}")

            for asset_id in all_asset_ids:
                runtime_pos = self.positions.get(asset_id) if asset_id in self.positions else prev_positions.get(asset_id)
                if not session.query(polymarket_models.Asset).filter_by(asset_id=asset_id).first():
                    session.add(
                        polymarket_models.Asset(
                            asset_id=asset_id,
                            event_id=runtime_pos.event_id,
                            condition_id=runtime_pos.condition_id,
                            slug=runtime_pos.slug,
                            last_price=runtime_pos.cur_price,
                        )
                    )
                
                pos = session.query(polymarket_models.Position).filter_by(portfolio_id=self.state.portfolio_id, asset_id=asset_id).first()
                if asset_id in self.positions and asset_id in prev_asset_ids:
                    pos.amount_shares = self.positions[asset_id].amount
                    pos.avg_price = self.positions[asset_id].avg_price
                elif asset_id in self.positions:
                    session.add(
                        # i keep forgetting that i don't store event_id, slug, etc in the positions table -> this is stored in the "assets table"
                        polymarket_models.Position(
                            portfolio_id=self.state.portfolio_id,
                            asset_id=asset_id,
                            amount_shares=self.positions[asset_id].amount,
                            avg_price=self.positions[asset_id].avg_price,
                            paper=self.state.paper
                        )
                    )
                elif asset_id in prev_asset_ids:
                    session.delete(pos)

                
            portfolio = session.query(polymarket_models.Portfolio).filter_by(id=self.state.portfolio_id).first()
            if not portfolio:
                logger.error(f"Portfolio '{self.state.portfolio}' not found.")
                return

            portfolio.cash_usd = self.state.cash_usd
            portfolio.paper = self.state.paper
            cur_value = self.state.cash_usd
            for asset_id, position in self.positions.items():
                cur_value += position.amount * (position.cur_price if position.cur_price else position.avg_price)
            portfolio.holdings_value_usd = cur_value
            portfolio.total_value_usd = self.state.cash_usd + cur_value
            portfolio.pnl = (self.state.cash_usd + cur_value) - self.state.allocation_usd
            
            portfolio.max_pnl = max(portfolio.max_pnl, portfolio.pnl)
            portfolio.min_pnl = min(portfolio.min_pnl, portfolio.pnl)
            portfolio.last_rebalance_at = datetime.now()
            
            session.commit()
            logger.info("DB updated successfully")

        
        logger.info("syncing portfolio...")
        self.sync_and_refresh()


    ############ db utils ############

    def sync_and_refresh(self):
        with self.SessionFactory() as session:
            portfolio = session.query(polymarket_models.Portfolio).filter_by(id=self.state.portfolio_id).first()
            if not portfolio:
                logger.error(f"Portfolio '{self.state.portfolio}' not found.")
                return

            logger.info(f"portfolio_id: {self.state.portfolio_id}, cash_usd: {self.state.cash_usd}, holdings_value_usd: {self.state.holdings_value_usd}, total_value_usd: {self.state.total_value_usd}, pnl: {self.state.pnl}")
            
            snapshot = polymarket_models.PortfolioSnapshot(
                portfolio_id=self.state.portfolio_id,
                cash_usd=self.state.cash_usd,
                holdings_value_usd=portfolio.holdings_value_usd,
                total_value_usd=portfolio.total_value_usd,
                pnl=portfolio.pnl,
                )
            session.add(snapshot)
            session.commit()
            logger.info("Portfolio snapshot taken successfully")

    ############################################################


    def place_market_buy(self, market_buy: MarketBuy) -> OrderResult:
        try:
            signed_order = self.clob_client.create_market_order(
                MarketOrderArgs(
                    token_id=market_buy.token_id,
                    amount=market_buy.amount_usd,
                    side='BUY'
                )
            )
            res = self.clob_client.post_order(signed_order, orderType="FOK")
            return OrderResult(order=market_buy, **res)
        except Exception as e:
            logger.error(f"failed to place market buy order: {e}")
            return OrderResult(order=market_buy, errorMsg=str(e))

    def place_market_sell(self, market_sell: MarketSell) -> OrderResult:
        # qwax
        if market_sell.virtual:
            return 
        try:
            signed_order = self.clob_client.create_market_order(
                MarketOrderArgs(
                    token_id=market_sell.token_id,
                    amount=market_sell.amount_shares,
                    side='SELL'
                )
            )
            res = self.clob_client.post_order(signed_order, orderType="FOK")
            return OrderResult(order=market_sell, **res)
        except Exception as e:
            logger.error(f"failed to place market sell order: {e}")
            return OrderResult(order=market_sell, errorMsg=str(e))

    def place_limit_order(self, limit_order: LimitOrder) -> OrderResult:
        try:
            order = self.clob_client.create_order(
                OrderArgs(
                    token_id=limit_order.token_id,
                    size=limit_order.size,
                    price=limit_order.price,
                    side=limit_order.side
                )
            )
            res = self.clob_client.post_order(order, orderType=OrderType.GTK.value)
            return OrderResult(order=limit_order, **res)
        except Exception as e:
            logger.error(f"failed to place limit order: {e}")
            return OrderResult(order=limit_order, errorMsg=str(e))

    def execute_orders_in_parallel(self, orders: List[Union[MarketBuy, MarketSell, LimitOrder]]) -> List[OrderResult]:
        """ 
        Executes a list of orders in parallel using a thread pool.
        Each order in the list should be an instance of one of the above defined order types
        """
        execution_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_order = {}
            for order in orders:
                future = None
                if isinstance(order, LimitOrder):
                    future = executor.submit(self.place_limit_order, order)
                elif isinstance(order, MarketBuy):
                    future = executor.submit(self.place_market_buy, order)
                elif isinstance(order, MarketSell):
                    if not order.virtual:
                        future = executor.submit(self.place_market_sell, order)
                    else:
                        future = executor.submit(self.get_virtual_order_result, order)
                else:
                    raise ValueError(f"Invalid order type: {order}")

                if future:
                    future_to_order[future] = order

            for future in concurrent.futures.as_completed(future_to_order):
                original_order = future_to_order[future]
                try:
                    result = future.result()
                    execution_results.append(result)
                except Exception as exc:
                    logger.error(f"Order {original_order} generated an exception: {exc}")
                    execution_results.append(OrderResult(order=original_order, errorMsg=str(exc)))
        
        return execution_results


    # util functions -> these should be PURE STATELESS FUNCTIONS

    @staticmethod
    def check_delta(p1: Dict[str, Dict[str, Any]], p2: Dict[str, Dict[str, Any]]) -> bool:
        for k, v in p1.items():
            if k not in p2:
                return True
            if abs(v["amount"] - p2[k]["amount"]) > 1e-9:
                return True
            if abs(v["avg_price"] - p2[k]["avg_price"]) > 1e-9:
                return True
        return False


    @staticmethod
    def apply(df, conditions):
        mask = np.full(df.shape[0], True)
        for k, v in conditions.items():
            mask &= np.vectorize(v)(df[k])
        return df[mask].reset_index()


    @footprint(time_limit_seconds=0.01, memory_limit_mb=10)
    def get_user_positions(self, user: str = None):
        if not user:
            user = os.getenv('POLYMARKET_PROXY_ADDRESS')
        pos = self.data_client.positions(
            PositionRequest(user=user)
        )
        return pd.DataFrame(pos)

    @footprint()
    def get_user_positions_dict(self, user: str = None):
        return self.get_user_positions(user).to_dict('records')

    @footprint(time_limit_seconds=0.01, memory_limit_mb=10)
    def get_recent_markets(self, look_back_days: int = 6 * 30, minimum_volume: float = 100000, minimum_liquidity: float = 1000, limit: int = 500, days_to_end: int = None):
        """
        Fetches a dataframe of markets created in the last look_back_months months.
        """ 
        request = {
            'limit': limit,
            'start_date_min': format_datetime(datetime.now() - timedelta(days=look_back_days)),
            'end_date_min': format_datetime(datetime.now()),
            'volume_num_min': minimum_volume,
            'liquidity_num_min': minimum_liquidity,
            'closed': False
        }
        if days_to_end is not None:
            request['end_date_max'] = format_datetime(datetime.now() + timedelta(days=days_to_end))
        res = self.gamma_client.get_markets(MarketRequest(**request))

        # this is just some cleaning on the data recieved from polymarket
    
        for market in res:
            json_fields = ['outcomes', 'outcomePrices', 'clobTokenIds', 'umaResolutionStatuses']
            for field in json_fields:
                if field in market and isinstance(market[field], str):
                    try:
                        market[field] = json.loads(market[field])
                    except (json.JSONDecodeError, TypeError):
                        pass
            
            float_fields = [
                'liquidity', 'volume', 'volumeNum', 'liquidityNum', 
                'volume24hr', 'volume1wk', 'volume1mo', 'volume1yr',
                'umaBond', 'umaReward', 'volume24hrClob', 'volume1wkClob', 
                'volume1moClob', 'volume1yrClob', 'volumeClob', 'liquidityClob',
                'orderPriceMinTickSize', 'orderMinSize', 'rewardsMinSize', 
                'rewardsMaxSpread', 'spread', 'oneDayPriceChange', 
                'oneWeekPriceChange', 'lastTradePrice', 'bestBid', 'bestAsk'
            ]
            for field in float_fields:
                if field in market and isinstance(market[field], str):
                    try:
                        market[field] = float(market[field])
                    except (ValueError, TypeError):
                        pass
            
            bool_fields = [
                'active', 'closed', 'new', 'featured', 'archived', 'restricted',
                'enableOrderBook', 'hasReviewedDates', 'acceptingOrders', 'negRisk',
                'ready', 'funded', 'cyom', 'pagerDutyNotificationEnabled', 'approved',
                'automaticallyActive', 'clearBookOnStart', 'showGmpSeries', 
                'showGmpOutcome', 'manualActivation', 'negRiskOther', 'pendingDeployment',
                'deploying', 'rfqEnabled'
            ]
            for field in bool_fields:
                if field in market and isinstance(market[field], str):
                    if market[field].lower() == 'true':
                        market[field] = True
                    elif market[field].lower() == 'false':
                        market[field] = False
            
            int_fields = ['id', 'commentCount']
            for field in int_fields:
                if field in market and isinstance(market[field], str):
                    try:
                        market[field] = int(market[field])
                    except (ValueError, TypeError):
                        pass
            
            if 'outcomePrices' in market and isinstance(market['outcomePrices'], list):
                try:
                    market['outcomePrices'] = [float(price) for price in market['outcomePrices']]
                except (ValueError, TypeError):
                    pass
            
            if 'events' in market and isinstance(market['events'], list):
                for event in market['events']:
                    for field in ['liquidity', 'volume', 'openInterest', 'competitive',
                                 'volume24hr', 'volume1wk', 'volume1mo', 'volume1yr']:
                        if field in event and isinstance(event[field], str):
                            try:
                                event[field] = float(event[field])
                            except (ValueError, TypeError):
                                pass
                    
                    for field in ['active', 'closed', 'archived', 'new', 'featured', 
                                 'restricted', 'enableOrderBook', 'negRisk', 'cyom',
                                 'showAllOutcomes', 'showMarketImages', 'enableNegRisk',
                                 'automaticallyActive', 'negRiskAugmented', 'pendingDeployment',
                                 'deploying']:
                        if field in event and isinstance(event[field], str):
                            if event[field].lower() == 'true':
                                event[field] = True
                            elif event[field].lower() == 'false':
                                event[field] = False
            
            if 'clobRewards' in market and isinstance(market['clobRewards'], list):
                for reward in market['clobRewards']:
                    for field in ['rewardsAmount', 'rewardsDailyRate']:
                        if field in reward and isinstance(reward[field], str):
                            try:
                                reward[field] = float(reward[field])
                            except (ValueError, TypeError):
                                pass

        df = pd.DataFrame(res)[trading_keys.keys()]
        
        list_fields = [
            'clobTokenIds',
            'outcomes',
            'outcomePrices',
        ]
        for k in list_fields:
            tdf = pd.DataFrame(df[k].tolist(), index=df.index)
            df[[k+str(i+1) for i in tdf.columns]] = tdf

        df.rename(columns={'conditionId': 'condition_id', 'endDate': 'end_date'}, inplace=True)
        df['event_id'] = df['events'].apply(lambda i: i[0]['ticker'])
        return df



trading_keys = {
    # SLUG
    'slug': 'Market slug',

    # EVENTS
    'events': 'Market events',

    # IDENTIFIERS
    'id': 'Unique market identifier',
    'conditionId': 'Blockchain condition identifier for the market',
    'clobTokenIds': 'CLOB token IDs for the market',
    'questionID': 'Question identifier for resolution',
    'outcomes': 'Possible resolution outcomes',
    
    # PRICING DATA
    'outcomePrices': 'Current prices for ["Yes", "No"] outcomes',
    'lastTradePrice': 'Price of the most recent trade',
    'bestBid': 'Highest price someone is willing to buy at',
    'bestAsk': 'Lowest price someone is willing to sell at',
    'spread': 'Difference between best bid and best ask',
    
    # LIQUIDITY & VOLUME
    'liquidity': 'Total liquidity available in the market',
    'liquidityNum': 'Total liquidity available in the market',
    'volumeNum': 'Total trading volume since market creation',
    'volume24hr': '24-hour trading volume',
    'volume1wk': '1-week trading volume',
    'volume1mo': '1-month trading volume',
    'volume': 'Total trading volume since market creation',
    
    # PRICE TRENDS
    'oneDayPriceChange': 'Price change over last 24 hours',
    'oneWeekPriceChange': 'Price change over last week',
    
    # MARKET STATUS
    'active': 'Whether market is currently active for trading',
    'closed': 'Whether market is closed',
    'acceptingOrders': 'Whether new orders can be placed',
    'endDate': 'When the market closes/resolves',
    
    # TRADING MECHANICS
    'orderMinSize': 'Minimum order size allowed',
    'orderPriceMinTickSize': 'Minimum price increment for orders',
    'enableOrderBook': 'Whether order book trading is enabled'
}



"""
This is how a return value from an order execution looks like:

{'errorMsg': '',
 'orderID': '0x7fa18fbd8ae6f68a30257d72710df62fb24c4704d84e742f4c60b017bc17ee04',
 'takingAmount': '2.136751',
 'makingAmount': '1.999998',
 'status': 'matched',
 'transactionsHashes': ['0x3abd31f20135449ebc49b4a1f02c3ae36753c5b3786aeacb0d5f0b029b238aad'],
 'success': True}

"""
