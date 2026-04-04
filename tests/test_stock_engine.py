"""StockEngine 單元測試 (使用手動設定價格，不依賴外部 API)"""

from engines.stock_engine import StockEngine, StockHolding


def _make_engine() -> StockEngine:
    """建立含兩檔持股的測試引擎"""
    engine = StockEngine([
        StockHolding(symbol="2330.TW", shares=100, cost_per_share=500.0),
        StockHolding(symbol="AAPL", shares=10, cost_per_share=150.0),
    ])
    engine.set_prices_manually({
        "2330.TW": 600.0,
        "AAPL": 200.0,
    })
    return engine


def test_add_holding():
    engine = StockEngine()
    engine.add_holding("2330.TW", 50, 500.0)
    assert len(engine.holdings) == 1
    assert engine.holdings[0].symbol == "2330.TW"
    assert engine.holdings[0].shares == 50


def test_remove_holding():
    engine = _make_engine()
    engine.remove_holding("AAPL")
    assert len(engine.holdings) == 1
    assert engine.holdings[0].symbol == "2330.TW"


def test_remove_holding_case_insensitive():
    engine = _make_engine()
    engine.remove_holding("aapl")
    assert len(engine.holdings) == 1


def test_get_positions():
    engine = _make_engine()
    positions = engine.get_positions()
    assert len(positions) == 2

    tsmc = next(p for p in positions if p.symbol == "2330.TW")
    assert tsmc.shares == 100
    assert tsmc.price == 600.0
    assert tsmc.market_value == 60_000  # 100 * 600
    assert tsmc.cost_basis == 50_000    # 100 * 500
    assert tsmc.profit_loss == 10_000   # 60,000 - 50,000
    assert tsmc.profit_loss_pct == 20.0 # 10,000 / 50,000 * 100


def test_get_positions_apple():
    engine = _make_engine()
    positions = engine.get_positions()
    aapl = next(p for p in positions if p.symbol == "AAPL")
    assert aapl.market_value == 2_000   # 10 * 200
    assert aapl.cost_basis == 1_500     # 10 * 150
    assert aapl.profit_loss == 500


def test_total_market_value():
    engine = _make_engine()
    # 60,000 + 2,000 = 62,000
    assert engine.total_market_value() == 62_000


def test_total_profit_loss():
    engine = _make_engine()
    # 10,000 + 500 = 10,500
    assert engine.total_profit_loss() == 10_500


def test_empty_engine():
    engine = StockEngine()
    assert engine.total_market_value() == 0
    assert engine.total_profit_loss() == 0
    assert engine.get_positions() == []


def test_zero_cost_basis():
    engine = StockEngine([
        StockHolding(symbol="TEST", shares=100, cost_per_share=0.0),
    ])
    engine.set_prices_manually({"TEST": 50.0})
    positions = engine.get_positions()
    assert len(positions) == 1
    assert positions[0].profit_loss_pct == 0.0  # 避免除以零


def test_positions_without_prices():
    engine = StockEngine([
        StockHolding(symbol="UNKNOWN", shares=100, cost_per_share=100.0),
    ])
    # 沒有設定價格 → 不會出現在 positions
    positions = engine.get_positions()
    assert len(positions) == 0


def test_set_prices_manually():
    engine = StockEngine([StockHolding("TEST", 10, 100.0)])
    engine.set_prices_manually({"TEST": 120.0})
    positions = engine.get_positions()
    assert positions[0].price == 120.0
    assert positions[0].market_value == 1_200
