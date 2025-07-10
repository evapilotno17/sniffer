import os
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from polymarket.clob_api.constants import Environment, POLYGON
load_dotenv()


class PolymarketClobClient(ClobClient):
    def __init__(self):
        self.private_key = os.getenv(Environment.POLYMARKET_PRIVATE_KEY)
        self.proxy_address = os.getenv(Environment.POLYMARKET_PROXY_ADDRESS)
        self.clob_host = os.getenv(Environment.POLYMARKET_CLOB_HOST)
        # ClobClient(host, key=prk, chain_id=chain_id, signature_type=1, funder=pbk)
        super().__init__(
            self.clob_host,
            key=self.private_key,
            chain_id=POLYGON,
            signature_type=1,
            funder=self.proxy_address,
        )
        self.set_api_creds(self.create_or_derive_api_creds())
