from enum import Enum

BASE_URL = "https://gamma-api.polymarket.com"

class Endpoint(str, Enum):
    def __str__(self) -> str: 
        return self.value

    def __repr__(self) -> str:
        return self.value

    MARKETS = "markets"
    EVENTS  = "events"

class SortDir(str, Enum):
    ASC  = "asc"
    DESC = "desc"
