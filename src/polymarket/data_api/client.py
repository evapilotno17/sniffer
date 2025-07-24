import time
from polymarket.data_api.constants import (
    BASE_URL,
    Endpoint,
)
from typing import Any, Dict, List, Optional
import requests
from polymarket.data_api.schemas import (
    PositionRequest,
    ActivityRequest,
    HoldersRequest,
    HoldingsValueRequest,
    TradesRequest,
    Trade,
)

from utils.runtime_utils import footprint

class PolymarketDataClient:
    """
        Convenience wrapper around polymarket's data api
    """

    @footprint()
    def __init__(
        self,
        *,
        session: Optional[requests.Session] = None,
        timeout: float = 10,
        user_agent: str = "polymarket-python/0.1",
    ) -> None:
        self.session  = session or requests.Session()
        self.timeout  = timeout
        # You can tack on your own auth header(s) here if PM ever requires it.
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


    def positions(
        self,
        request: PositionRequest | dict,
    ) -> List[Dict[str, Any]]:
        """
        Fetch current positions for user.
        """
        if isinstance(request, dict):
            request = PositionRequest(**request)
        
        params = request.model_dump()
        return self._get(BASE_URL + '/' + Endpoint.POSITIONS, params)

    # /activity ---------------------------------------------------------- #
    def activity(
        self,
        request: ActivityRequest | dict,
    ) -> List[Dict[str, Any]]:
        """
            Fetch the users **on-chain activity / trade history**.
        """
        if isinstance(request, dict):
            request = ActivityRequest(**request)
        
        params = request.model_dump()
        return self._get(BASE_URL + '/' + Endpoint.ACTIVITY, params)

    # /holders ----------------------------------------------------------- #
    def holders(
        self,
        request: HoldersRequest | dict,
    ) -> List[Dict[str, Any]]:
        """
            get the TOP holders for a market
        """
        if isinstance(request, dict):
            request = HoldersRequest(**request)
        
        params = request.model_dump()
        return self._get(BASE_URL + '/' + Endpoint.HOLDERS, params) 

    # /value ------------------------------------------------------------- #
    def holdings_value(
        self,
        request: HoldingsValueRequest | dict,
    ) -> List[Dict[str, Any]]:
        """
            Fetch the users **total USD value** of their positions.
        """
        if isinstance(request, dict):
            request = HoldingsValueRequest(**request)
        
        params = request.model_dump()
        return self._get(BASE_URL + '/' + Endpoint.VALUE, params)


    def get_trades(
        self,
        request: TradesRequest | dict,
    ) -> List[Trade]:
        """
        Get trades from all markets and all users.
        """
        if isinstance(request, dict):
            request = TradesRequest(**request)

        params = request.model_dump(exclude_none=True)
        response = self._get(BASE_URL + '/' + Endpoint.TRADES, params)
        return [Trade(**trade) for trade in response]

