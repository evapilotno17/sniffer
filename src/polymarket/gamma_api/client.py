import requests
import pandas as pd
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from polymarket.gamma_api.constants import BASE_URL, Endpoint
from polymarket.gamma_api.schemas import MarketRequest, EventRequest
from utils.runtime_utils import footprint

trading_keys = {
    # SLUG
    'slug': 'Market slug',

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


def format_datetime(date: datetime) -> str:
    return date.strftime('%Y-%m-%dT%H:%M:%SZ')

class PolymarketGammaClient:
    """
    Convenience wrapper around Polymarket's Gamma API.
    """
    @footprint()
    def __init__(
        self,
        *,
        session: Optional[requests.Session] = None,
        timeout: float = 10,
        user_agent: str = "polymarket-python/0.1",
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout
        self.headers: Dict[str, str] = {"User-Agent": user_agent}

    def _get(self, url: str, params: Dict[str, Any]) -> Any:
        """
        Fire a GET, raise for HTTP errors, and return the decoded JSON.
        """
        resp = self.session.get(
            url, params=params, headers=self.headers, timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json()

    def get_markets(
        self,
        request: MarketRequest | dict,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves a list of markets with various filtering and sorting options.
        """
        if isinstance(request, dict):
            request = MarketRequest(**request)
        
        params = request.model_dump(by_alias=True, exclude_none=True)
        return self._get(f"{BASE_URL}/{Endpoint.MARKETS}", params)

    def get_events(
        self,
        request: EventRequest | dict,
    ) -> List[Dict[str, Any]]:
        """
        Fetches a list of events with various filtering and sorting options.
        """
        if isinstance(request, dict):
            request = EventRequest(**request)
        
        params = request.model_dump(by_alias=True, exclude_none=True)
        return self._get(f"{BASE_URL}/{Endpoint.EVENTS}", params)

    # later move to nothing_ever_happens
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
        res = self.get_markets(MarketRequest(**request))

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
        
        return df

"""
Below is a concise, field-by-field cheat-sheet for a Polymarket “market” object as returned by the Gamma API, followed by a deeper look at the liquidity numbers.

────────────────────────────────────────────────────────

Top-level identification & labeling ──────────────────────────────────────────────────────── • id (string) - Internal numeric ID of the market.
• question (string) - Human-readable market question.
• slug (string) - URL-safe identifier used in Polymarket links.
• conditionId / questionID (hash) - On-chain identifiers used by the prediction-market smart contracts (conditionId on Polygon, questionID for UMA oracle).
• groupItemThreshold (string/number) - Min number of markets required before grouping logic displays this market; rarely important for traders.
──────────────────────────────────────────────────────── 2. Dates ──────────────────────────────────────────────────────── • startDate / startDateIso - First time the market can accept orders.
• endDate / endDateIso - Scheduled resolution/expiry time (ISO-8601).
• createdAt / updatedAt - API record timestamps.
• acceptingOrdersTimestamp - Exact instant the market switched to “acceptingOrders = true”.

──────────────────────────────────────────────────────── 3. Status flags (booleans) ──────────────────────────────────────────────────────── • active - The market is open for trading now (acceptingOrders && !closed && !archived).
• closed - Trading halted but not yet resolved.
• archived - Permanently hidden from UI.
• new - Recently listed; Polymarket uses this to badge markets.
• featured - Selected by admins for homepage prominence.
• approved - Passed internal compliance review.
• ready / funded - Internal pipeline states (liquidity seeded, bonds posted, etc.).
• restricted - Hidden from US IPs and other blocked regions.
• cyom - “Create-Your-Own-Market” flag (user-generated template).
• automaticallyActive / manualActivation / clearBookOnStart - Operational deployment controls.
• pendingDeployment / deploying - Market contract being created on-chain.
• rfqEnabled - Request-For-Quote module switched on.
• acceptingOrders - Orders are being matched (true once “active”).

──────────────────────────────────────────────────────── 4. Market mechanics & trading parameters ──────────────────────────────────────────────────────── • enableOrderBook (bool) - If false the market would have used the legacy AMM (rare now).
• orderPriceMinTickSize (float) - Smallest price increment (e.g., 0.01 ⇒ 1 ¢ tick).
• orderMinSize (float) - Minimum size (USDC) per order.
• spread (float) - BestAsk - BestBid (display-only helper).
• bestBid / bestAsk (float) - Current top of book prices for “Yes”.
• competitive (float) - Internal score ranking markets by trading activity/liquidity.
• negRisk / negRiskOther / negRiskRequestID - Admin fields dealing with “negative risk” protection (preventing free-money arbitrage situations).
• orderBook-related: clobTokenIds - 256-bit IDs that map outcome tokens in the on-chain CLOB (central-limit order book).

──────────────────────────────────────────────────────── 5. Liquidity & incentives ──────────────────────────────────────────────────────── • liquidity (string) - Human-display liquidity in USDC (as a string for historical reasons).
• liquidityNum (number) - Same amount but already parsed as a float.
• liquidityClob (number) - How much of that liquidity is specifically on the current on-chain CLOB (vs. still on legacy AMM pools).
• clobRewards (array) - Active liquidity-mining reward programs (each entry has rewardsDailyRate, startDate, endDate, etc.).
• rewardsMinSize / rewardsMaxSpread - Eligibility criteria for those rewards.
• umaBond / umaReward - UMA oracle bond amount and incentive paid by market creator.

──────────────────────────────────────────────────────── 6. Outcomes & pricing ──────────────────────────────────────────────────────── • outcomes (stringified list) - JSON-encoded array of outcome names.
• outcomePrices (stringified list) - JSON-encoded spot prices for each outcome.
• events (list) - One or more “event” wrappers (Polymarket can bundle markets into events; most single-market cases contain just one).

──────────────────────────────────────────────────────── 7. Misc & admin ──────────────────────────────────────────────────────── • resolutionSource (string) - Text description of where the final truth will be taken from (e.g., “Official CDC data”).
• marketMakerAddress (address) - If an AMM exists, its contract address.
• submitted_by / createdBy (address / user ID) - Market creator.
• resolvedBy - Address that ultimately posted the settlement when resolved.
• pagerDutyNotificationEnabled - Internal monitoring toggle.
• umaResolutionStatuses, negRiskAugmented, openInterest, commentCount, showAllOutcomes, showMarketImages, etc. - UI/ops helpers.

──────────────────────────────────────────────────────── Liquidity - exact meaning & interpretation ────────────────────────────────────────────────────────

Unit
• The value is denominated in USDC (Polymarket’s settlement/stablecoin), effectively equivalent to U.S. dollars.
How it’s computed
• For CLOB markets (current default):
“Liquidity” ≈ 2 × min(bestBidDepth, bestAskDepth) within a ±X % price band (internally X ≈ 2.5 %).
In other words, it measures the dollar value you can immediately trade on both sides before moving the mid-price by ~2-3 %.
• For legacy AMM markets:
It represented the constant-product invariant parameter: 2·√(k) where k = x·y pool reserves (also in USDC).
• liquidityClob isolates the CLOB portion when hybrid liquidity sources coexist during migration.
Practical reading
• Higher liquidity ⇒ tighter spreads and better price impact.
• You can treat the number as: “Roughly how many USDC I could buy & then immediately sell without moving the price more than a couple of ticks.”
──────────────────────────────────────────────────────── Quick “intuitive” summary of a few common fields ──────────────────────────────────────────────────────── • active / closed - Is the market trading right now?
• liquidity - Rough dollars available inside ±2-3 % of the mid-price.
• spread / bestBid / bestAsk - Current trading tightness.
• outcomePrices - What “Yes” and “No” are trading for (probabilities in decimal form: 0.20 = 20 %).
• orderPriceMinTickSize - Prices move in 1 ¢ steps.
• endDate - Deadline after which the market resolves.
• resolutionSource - Where truth will come from.
• umaBond - Skin-in-the-game the creator must lock to discourage ambiguities.


Example return object for get_markets:
{'id': '523354',
 'question': 'Will LDP hold the most seats in the House of Councillors following the 2025 Japan election?',
 'conditionId': '0x56d03f7bfd1a2c12e30dbeb6bb208041016e9dc68641e7fd1a879f928f0218d1',
 'slug': 'will-ldp-hold-the-most-seats-in-the-house-of-councillors-following-the-2025-japan-election',
 'resolutionSource': '',
 'endDate': '2025-07-27T12:00:00Z',
 'liquidity': '25094.61056',
 'startDate': '2025-06-10T23:22:20.927463Z',
 'image': 'https://polymarket-upload.s3.us-east-2.amazonaws.com/will-ldp-hold-the-most-seats-in-the-house-of-councillors-following-the-2025-japan-election-jgDhrrutlgMS.png',
 'icon': 'https://polymarket-upload.s3.us-east-2.amazonaws.com/will-ldp-hold-the-most-seats-in-the-house-of-councillors-following-the-2025-japan-election-jgDhrrutlgMS.png',
 'description': 'The 27th general election of the House of Councillors is scheduled to be held in Japan by July 27, 2025, to elect half of the 248 members of the House of Councillors, the upper house of the National Diet, for a term of six years.\n\nThis market will resolve to the political party that controls the most seats in Japan\'s House of Councillors as a result of the upcoming election, not any coalition of which it may be a part.\n\nIf voting in the next Japanese election for the House of Councillors does not occur by December 31, 2025, this market will resolve to "Other".\n\nIn the case of a tie between a party and any other for the most seats held, this market will resolve in favor of the party whose listed abbreviation comes first in alphabetical order. If no abbreviation is listed for a party, the name of that party will be used.\n\nThis market\'s resolution will be based solely on the number of seats won by the named party or coalition. \n\nThis market will resolve based solely on the certified results as reported by Japan\'s government, specifically the Central Election Management Council (https://www.e-stat.go.jp/stat-search/files?page=1&toukei=00200236). Certified results are typically published within 5 days of the election.',
 'outcomes': '["Yes", "No"]',
 'outcomePrices': '["0.977", "0.023"]',
 'volume': '137632.2291',
 'active': True,
 'closed': False,
 'marketMakerAddress': '',
 'createdAt': '2025-02-13T20:15:53.480819Z',
 'updatedAt': '2025-07-08T21:54:20.745023Z',
 'new': False,
 'featured': False,
 'submitted_by': '0x91430CaD2d3975766499717fA0D66A78D814E5c5',
 'archived': False,
 'resolvedBy': '0x2F5e3684cb1F318ec51b00Edba38d79Ac2c0aA9d',
 'restricted': True,
 'groupItemTitle': 'LDP (Liberal Democratic Party)',
 'groupItemThreshold': '0',
 'questionID': '0x0ec4a73b5730ed1f3ba73f01424b377dccb1f761935c0116f3de3597f0f7e200',
 'enableOrderBook': True,
 'orderPriceMinTickSize': 0.001,
 'orderMinSize': 5,
 'volumeNum': 137632.2291,
 'liquidityNum': 25094.61056,
 'endDateIso': '2025-07-27',
 'startDateIso': '2025-06-10',
 'hasReviewedDates': True,
 'volume24hr': 5243.695891000001,
 'volume1wk': 22254.469815,
 'volume1mo': 135767.812912,
 'volume1yr': 135767.812912,
 'clobTokenIds': '["69516851235597599035372774918947401580156756479320210283252592577684374017607", "57740901844812945942046290360877145704808318543679330418359752334050538850600"]',
 'umaBond': '500',
 'umaReward': '5',
 'volume24hrClob': 5243.695891000001,
 'volume1wkClob': 22254.469815,
 'volume1moClob': 135767.812912,
 'volume1yrClob': 135767.812912,
 'volumeClob': 137632.2291,
 'liquidityClob': 25094.61056,
 'acceptingOrders': True,
 'negRisk': True,
 'negRiskMarketID': '0x0ec4a73b5730ed1f3ba73f01424b377dccb1f761935c0116f3de3597f0f7e200',
 'negRiskRequestID': '0x04293fe41b8a6998ab94284d02b83085f86ed848eb56c3ea81ad6cb9fa00e63b',
 'events': [{'id': '18565',
   'ticker': 'japan-house-of-councillors-election',
   'slug': 'japan-house-of-councillors-election',
   'title': 'Japan House of Councillors Election',
   'description': 'The 27th general election of the House of Councillors is scheduled to be held in Japan by July 27, 2025, to elect half of the 248 members of the House of Councillors, the upper house of the National Diet, for a term of six years.\n\nThis market will resolve to the political party that controls the most seats in Japan\'s House of Councillors as a result of the upcoming election.\n\nIf voting in the next Japanese election for the House of Councillors does not occur by December 31, 2025, this market will resolve to "Other".\n\nIn the case of a tie between a party and any other for the most seats held, this market will resolve in favor of the party whose listed abbreviation comes first in alphabetical order. If no abbreviation is listed for a party, the name of that party will be used.\n\nThis market\'s resolution will be based solely on the number of seats won by the named party or coalition. \n\nThis market will resolve based on the result of the election as indicated by a consensus of credible reporting. If there is ambiguity, this market will resolve based solely on the official results as reported by Japan\'s government.',
   'resolutionSource': '',
   'startDate': '2025-06-10T23:24:23.011995Z',
   'creationDate': '2025-06-10T23:24:23.01199Z',
   'endDate': '2025-07-27T12:00:00Z',
   'image': 'https://polymarket-upload.s3.us-east-2.amazonaws.com/japan-parliamentary-election-2025-veeFjSprp7IX.jpg',
   'icon': 'https://polymarket-upload.s3.us-east-2.amazonaws.com/japan-parliamentary-election-2025-veeFjSprp7IX.jpg',
   'active': True,
   'closed': False,
   'archived': False,
   'new': False,
   'featured': False,
   'restricted': True,
   'liquidity': 145513.00145,
   'volume': 522650.121179,
   'openInterest': 0,
   'sortBy': 'price',
   'createdAt': '2025-02-13T20:15:50.662691Z',
   'updatedAt': '2025-07-08T21:52:29.38103Z',
   'competitive': 0.814961221088996,
   'volume24hr': 5446.424356000001,
   'volume1wk': 46736.668116,
   'volume1mo': 520778.466914,
   'volume1yr': 520778.466914,
   'enableOrderBook': True,
   'liquidityClob': 145513.00145,
   'negRisk': True,
   'negRiskMarketID': '0x0ec4a73b5730ed1f3ba73f01424b377dccb1f761935c0116f3de3597f0f7e200',
   'commentCount': 24,
   'cyom': False,
   'showAllOutcomes': True,
   'showMarketImages': True,
   'enableNegRisk': True,
   'automaticallyActive': True,
   'startTime': '2025-07-27T17:00:00Z',
   'gmpChartMode': 'default',
   'negRiskAugmented': True,
   'countryName': 'Japan',
   'electionType': ' House of Councillors',
   'pendingDeployment': False,
   'deploying': False,
   'deployingTimestamp': '2025-06-10T23:14:31.143735Z'}],
 'ready': False,
 'funded': False,
 'acceptingOrdersTimestamp': '2025-06-10T23:21:53Z',
 'cyom': False,
 'competitive': 0.8146447049316147,
 'pagerDutyNotificationEnabled': False,
 'approved': True,
 'clobRewards': [{'id': '26280',
   'conditionId': '0x56d03f7bfd1a2c12e30dbeb6bb208041016e9dc68641e7fd1a879f928f0218d1',
   'assetAddress': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
   'rewardsAmount': 0,
   'rewardsDailyRate': 10,
   'startDate': '2025-06-10',
   'endDate': '2500-12-31'}],
 'rewardsMinSize': 100,
 'rewardsMaxSpread': 3.5,
 'spread': 0.004,
 'oneDayPriceChange': -0.003,
 'oneWeekPriceChange': 0.0055,
 'lastTradePrice': 0.973,
 'bestBid': 0.975,
 'bestAsk': 0.979,
 'automaticallyActive': True,
 'clearBookOnStart': True,
 'seriesColor': '',
 'showGmpSeries': False,
 'showGmpOutcome': False,
 'manualActivation': False,
 'negRiskOther': False,
 'umaResolutionStatuses': '[]',
 'pendingDeployment': False,
 'deploying': False,
 'deployingTimestamp': '2025-06-10T23:15:00.479164Z',
 'rfqEnabled': False}


"""