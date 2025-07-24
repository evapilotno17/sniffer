# Sniffer Impl plan

## End user
- me

## Purpose
- allow me to visualize polymarket stats/markets/positions/users/strategies
- allow me to trade polymarket assets programmatically: deploy, manage and edit strategies

## Endpoints I need:
- /strategies crud
- /assets crud




## design for a strategy:
- what state should a strategy store in-memory?
- every run_once iteration:
    - for ALL the positions that THIS strategy has access to, update their price data and such from polymarket (prepare for rebalance)
    - rebalance - get a set of orders to execute
    - execute orders
    - update state