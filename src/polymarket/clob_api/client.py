import os
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from polymarket.clob_api.constants import Environment, POLYGON
load_dotenv()

from utils.runtime_utils import footprint


class PolymarketClobClient(ClobClient):
    @footprint()
    def __init__(self, private_key: str = None, proxy_address: str = None, clob_host: str = None):
        self.private_key = private_key or os.getenv(Environment.POLYMARKET_PRIVATE_KEY)
        self.proxy_address = proxy_address or os.getenv(Environment.POLYMARKET_PROXY_ADDRESS)
        self.clob_host = clob_host or os.getenv(Environment.POLYMARKET_CLOB_HOST)
        # ClobClient(host, key=prk, chain_id=chain_id, signature_type=1, funder=pbk)
        super().__init__(
            self.clob_host,
            key=self.private_key,
            chain_id=POLYGON,
            signature_type=1,
            funder=self.proxy_address,
        )
        self.set_api_creds(self.create_or_derive_api_creds())
