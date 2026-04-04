"""股票持倉模組 — 自動抓取即時股價並計算投資組合價值"""

from dataclasses import dataclass, field
import requests


@dataclass
class StockHolding:
    symbol: str         # 股票代號 (例: "2330.TW", "AAPL")
    shares: float       # 持有股數
    cost_per_share: float = 0.0  # 買入均價 (選填，用於損益計算)


@dataclass
class StockQuote:
    symbol: str
    name: str
    price: float        # 即時價格
    currency: str       # 幣別 (TWD, USD)
    change_pct: float   # 漲跌幅 %


@dataclass
class StockPosition:
    symbol: str
    name: str
    shares: float
    price: float
    market_value: float     # 現值 = shares * price
    cost_basis: float       # 成本 = shares * cost_per_share
    profit_loss: float      # 損益 = market_value - cost_basis
    profit_loss_pct: float  # 損益率 %
    currency: str
    change_pct: float       # 今日漲跌幅


class StockEngine:
    """股票持倉引擎：管理持股清單並抓取即時股價"""

    YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"

    def __init__(self, holdings: list[StockHolding] | None = None):
        self.holdings = holdings or []
        self._price_cache: dict[str, StockQuote] = {}

    def add_holding(self, symbol: str, shares: float, cost_per_share: float = 0.0):
        """新增持股"""
        self.holdings.append(StockHolding(symbol=symbol.upper(), shares=shares, cost_per_share=cost_per_share))

    def remove_holding(self, symbol: str):
        """移除持股"""
        self.holdings = [h for h in self.holdings if h.symbol.upper() != symbol.upper()]

    def fetch_quotes(self, symbols: list[str] | None = None) -> dict[str, StockQuote]:
        """從 Yahoo Finance 抓取即時報價

        Args:
            symbols: 要查詢的股票代號列表，None 則查全部持股

        Returns:
            dict: symbol -> StockQuote
        """
        if symbols is None:
            symbols = [h.symbol for h in self.holdings]

        if not symbols:
            return {}

        try:
            params = {
                "symbols": ",".join(symbols),
                "fields": "shortName,regularMarketPrice,currency,regularMarketChangePercent",
            }
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(self.YAHOO_QUOTE_URL, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            quotes = {}
            for result in data.get("quoteResponse", {}).get("result", []):
                symbol = result.get("symbol", "")
                quotes[symbol] = StockQuote(
                    symbol=symbol,
                    name=result.get("shortName", symbol),
                    price=result.get("regularMarketPrice", 0.0),
                    currency=result.get("currency", "TWD"),
                    change_pct=result.get("regularMarketChangePercent", 0.0),
                )

            self._price_cache.update(quotes)
            return quotes

        except (requests.RequestException, KeyError, ValueError):
            return self._price_cache

    def get_positions(self) -> list[StockPosition]:
        """計算所有持股的即時部位資訊 (使用快取價格)"""
        positions = []
        for h in self.holdings:
            quote = self._price_cache.get(h.symbol)
            if quote is None:
                continue

            market_value = h.shares * quote.price
            cost_basis = h.shares * h.cost_per_share
            profit_loss = market_value - cost_basis
            profit_loss_pct = (profit_loss / cost_basis * 100) if cost_basis > 0 else 0.0

            positions.append(StockPosition(
                symbol=h.symbol,
                name=quote.name,
                shares=h.shares,
                price=quote.price,
                market_value=round(market_value),
                cost_basis=round(cost_basis),
                profit_loss=round(profit_loss),
                profit_loss_pct=round(profit_loss_pct, 2),
                currency=quote.currency,
                change_pct=round(quote.change_pct, 2),
            ))
        return positions

    def total_market_value(self) -> int:
        """持倉總市值"""
        return sum(p.market_value for p in self.get_positions())

    def total_profit_loss(self) -> int:
        """持倉總損益"""
        return sum(p.profit_loss for p in self.get_positions())

    def set_prices_manually(self, prices: dict[str, float]):
        """手動設定價格 (用於離線測試或 API 失敗時)"""
        for symbol, price in prices.items():
            self._price_cache[symbol] = StockQuote(
                symbol=symbol, name=symbol, price=price,
                currency="TWD", change_pct=0.0,
            )
