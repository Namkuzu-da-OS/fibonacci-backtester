"""
DiNapoli Levels Backtester
Test DiNapoli Fibonacci methodology on historical data
"""

import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from schwab_client import SchwabClient, Candle
from dinapoli import (
    DiNapoliCalculator,
    Fibnode,
    ObjectivePoint,
    Confluence,
    Agreement,
    SwingPoint,
    find_swing_points,
    identify_market_swing
)


@dataclass
class LevelTest:
    """Result of testing a single level"""
    level_type: str  # "F3", "F5", "COP", "OP", "XOP", "Confluence", "Agreement"
    price: float
    touched: bool
    held: bool  # Did price respect the level?
    pierced: bool  # Was level pierced but then recovered?
    broken: bool  # Was level decisively broken?
    touch_count: int
    first_touch_idx: Optional[int]
    max_pierce_pct: float  # How far past the level price went


@dataclass
class BacktestResult:
    """Complete backtest results"""
    symbol: str
    period: str
    start_date: str
    end_date: str
    candle_count: int
    swing_count: int
    total_levels_tested: int
    levels: List[LevelTest]
    stats: Dict[str, float]


class DiNapoliBacktester:
    """Backtest DiNapoli Levels on historical data"""

    def __init__(
        self,
        client: SchwabClient,
        swing_lookback: int = 5,
        confluence_tolerance: float = 0.5,
        pierce_tolerance_pct: float = 0.3
    ):
        """
        Args:
            client: Schwab API client
            swing_lookback: Bars to look back/forward for swing detection
            confluence_tolerance: Percentage tolerance for Confluence
            pierce_tolerance_pct: How much a level can be pierced before "broken"
        """
        self.client = client
        self.calc = DiNapoliCalculator(confluence_tolerance_pct=confluence_tolerance)
        self.swing_lookback = swing_lookback
        self.pierce_tolerance_pct = pierce_tolerance_pct

    def run_backtest(
        self,
        symbol: str,
        period_type: str = "year",
        period: int = 1,
        frequency_type: str = "daily"
    ) -> BacktestResult:
        """
        Run backtest on historical data.

        Args:
            symbol: Stock symbol
            period_type: "day", "month", "year"
            period: Number of periods
            frequency_type: "minute", "daily", "weekly"

        Returns:
            BacktestResult with all level tests and statistics
        """
        # Fetch historical data
        candles = self.client.get_history(
            symbol,
            period_type=period_type,
            period=period,
            frequency_type=frequency_type
        )

        if not candles:
            raise ValueError(f"No data returned for {symbol}")

        # Extract price arrays
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]

        # Find swing points
        swing_highs, swing_lows = find_swing_points(highs, lows, self.swing_lookback)

        all_level_tests = []
        swing_count = 0

        # Process each potential market swing
        for i in range(len(swing_highs)):
            # Get swings up to this point
            current_highs = [h for h in swing_highs if h.index <= swing_highs[i].index]
            current_lows = [l for l in swing_lows if l.index <= swing_highs[i].index]

            if len(current_highs) < 2 or len(current_lows) < 1:
                continue

            focus, reactions, is_uptrend = identify_market_swing(current_highs, current_lows)

            if not focus or len(reactions) < 1:
                continue

            swing_count += 1

            # Calculate Fibnodes
            fibnodes = self.calc.calculate_fibnodes(
                focus.price,
                reactions[:5],  # Use up to 5 most recent reactions
                is_uptrend
            )

            # Get price range for tolerance calculations
            price_range = abs(focus.price - min(r.price for r in reactions))

            # Find Confluence
            confluences = self.calc.find_confluence(fibnodes, price_range)

            # Test Fibnodes on subsequent price action
            test_start = focus.index + 1
            test_candles = candles[test_start:test_start + 50]  # Test next 50 bars

            for fn in fibnodes:
                test = self._test_level(
                    fn.price,
                    "F3" if fn.ratio == 0.382 else "F5",
                    test_candles,
                    is_support=is_uptrend,
                    price_range=price_range
                )
                all_level_tests.append(test)

            # Test Confluence areas
            for conf in confluences:
                mid_price = (conf.price_low + conf.price_high) / 2
                test = self._test_level(
                    mid_price,
                    "Confluence",
                    test_candles,
                    is_support=is_uptrend,
                    price_range=price_range
                )
                all_level_tests.append(test)

            # Calculate and test Objective Points if we have ABC pattern
            if len(reactions) >= 1 and len(test_candles) > 0:
                # Find potential C point (retracement into fibnodes)
                c_candidates = []
                for j, tc in enumerate(test_candles[:20]):
                    for fn in fibnodes:
                        if is_uptrend and tc.low <= fn.price <= tc.high:
                            c_candidates.append((j, fn.price))
                        elif not is_uptrend and tc.low <= fn.price <= tc.high:
                            c_candidates.append((j, fn.price))

                if c_candidates:
                    c_idx, c_price = c_candidates[0]  # First touch

                    ops = self.calc.calculate_objective_points(
                        reactions[0].price,  # Point A
                        focus.price,  # Point B
                        c_price,  # Point C
                        is_uptrend
                    )

                    # Test OPs on remaining candles
                    op_test_candles = test_candles[c_idx:]
                    for op in ops:
                        test = self._test_level(
                            op.price,
                            op.name,
                            op_test_candles,
                            is_support=False,  # OPs are targets, not S/R
                            price_range=price_range
                        )
                        all_level_tests.append(test)

                    # Find and test Agreement
                    agreements = self.calc.find_agreement(fibnodes, ops, price_range)
                    for agr in agreements:
                        mid_price = (agr.price_low + agr.price_high) / 2
                        test = self._test_level(
                            mid_price,
                            "Agreement",
                            test_candles,
                            is_support=is_uptrend,
                            price_range=price_range
                        )
                        all_level_tests.append(test)

        # Calculate statistics
        stats = self._calculate_stats(all_level_tests)

        return BacktestResult(
            symbol=symbol,
            period=f"{period} {period_type}(s)",
            start_date=candles[0].datetime.strftime("%Y-%m-%d"),
            end_date=candles[-1].datetime.strftime("%Y-%m-%d"),
            candle_count=len(candles),
            swing_count=swing_count,
            total_levels_tested=len(all_level_tests),
            levels=all_level_tests,
            stats=stats
        )

    def _test_level(
        self,
        level_price: float,
        level_type: str,
        candles: List[Candle],
        is_support: bool,
        price_range: float
    ) -> LevelTest:
        """Test how price respects a specific level"""

        touched = False
        held = False
        pierced = False
        broken = False
        touch_count = 0
        first_touch_idx = None
        max_pierce_pct = 0.0

        pierce_threshold = level_price * (self.pierce_tolerance_pct / 100)

        for i, candle in enumerate(candles):
            # Check if price touched the level
            if candle.low <= level_price <= candle.high:
                touched = True
                touch_count += 1
                if first_touch_idx is None:
                    first_touch_idx = i

                # Check if level held
                if is_support:
                    # For support: price should stay above or bounce from level
                    if candle.close >= level_price:
                        held = True
                    else:
                        pierce_amount = level_price - candle.close
                        pierce_pct = (pierce_amount / level_price) * 100
                        max_pierce_pct = max(max_pierce_pct, pierce_pct)

                        if pierce_amount > pierce_threshold:
                            broken = True
                        else:
                            pierced = True
                else:
                    # For resistance/targets: check if reached
                    if candle.high >= level_price:
                        held = True  # "Held" means target was reached

            # For objectives (not S/R), just check if price reached the level
            if level_type in ["COP", "OP", "XOP"]:
                if is_support:
                    if candle.low <= level_price:
                        touched = True
                        held = True
                        if first_touch_idx is None:
                            first_touch_idx = i
                else:
                    if candle.high >= level_price:
                        touched = True
                        held = True
                        if first_touch_idx is None:
                            first_touch_idx = i

        return LevelTest(
            level_type=level_type,
            price=round(level_price, 2),
            touched=touched,
            held=held,
            pierced=pierced,
            broken=broken,
            touch_count=touch_count,
            first_touch_idx=first_touch_idx,
            max_pierce_pct=round(max_pierce_pct, 2)
        )

    def _calculate_stats(self, tests: List[LevelTest]) -> Dict[str, float]:
        """Calculate statistics from level tests"""

        stats = {}

        # Group by level type
        level_types = set(t.level_type for t in tests)

        for lt in level_types:
            lt_tests = [t for t in tests if t.level_type == lt]
            total = len(lt_tests)

            if total == 0:
                continue

            touched = sum(1 for t in lt_tests if t.touched)
            held = sum(1 for t in lt_tests if t.held)
            pierced = sum(1 for t in lt_tests if t.pierced)
            broken = sum(1 for t in lt_tests if t.broken)

            stats[f"{lt}_total"] = total
            stats[f"{lt}_touched_pct"] = round(touched / total * 100, 1) if total > 0 else 0
            stats[f"{lt}_held_pct"] = round(held / touched * 100, 1) if touched > 0 else 0
            stats[f"{lt}_pierced_pct"] = round(pierced / touched * 100, 1) if touched > 0 else 0
            stats[f"{lt}_broken_pct"] = round(broken / touched * 100, 1) if touched > 0 else 0

        # Overall stats
        total = len(tests)
        if total > 0:
            stats["overall_touched_pct"] = round(
                sum(1 for t in tests if t.touched) / total * 100, 1
            )
            touched_tests = [t for t in tests if t.touched]
            if touched_tests:
                stats["overall_held_pct"] = round(
                    sum(1 for t in touched_tests if t.held) / len(touched_tests) * 100, 1
                )

        return stats


def format_results(result: BacktestResult) -> str:
    """Format backtest results for display"""

    lines = [
        "=" * 70,
        f"DINAPOLI LEVELS BACKTEST RESULTS",
        "=" * 70,
        f"Symbol: {result.symbol}",
        f"Period: {result.period} ({result.start_date} to {result.end_date})",
        f"Candles: {result.candle_count}",
        f"Swings Analyzed: {result.swing_count}",
        f"Total Levels Tested: {result.total_levels_tested}",
        "",
        "-" * 70,
        "STATISTICS BY LEVEL TYPE",
        "-" * 70,
    ]

    level_types = ["F3", "F5", "Confluence", "COP", "OP", "XOP", "Agreement"]

    for lt in level_types:
        total_key = f"{lt}_total"
        if total_key in result.stats:
            total = result.stats[total_key]
            touched = result.stats.get(f"{lt}_touched_pct", 0)
            held = result.stats.get(f"{lt}_held_pct", 0)
            broken = result.stats.get(f"{lt}_broken_pct", 0)

            lines.append(f"\n{lt}:")
            lines.append(f"  Total Levels: {total}")
            lines.append(f"  Touched: {touched}%")
            lines.append(f"  Held (when touched): {held}%")
            lines.append(f"  Broken: {broken}%")

    lines.extend([
        "",
        "-" * 70,
        "OVERALL STATISTICS",
        "-" * 70,
        f"Overall Touched: {result.stats.get('overall_touched_pct', 0)}%",
        f"Overall Held: {result.stats.get('overall_held_pct', 0)}%",
    ])

    return "\n".join(lines)


def save_results_json(result: BacktestResult, filename: str):
    """Save results to JSON file"""
    data = {
        "symbol": result.symbol,
        "period": result.period,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "candle_count": result.candle_count,
        "swing_count": result.swing_count,
        "total_levels_tested": result.total_levels_tested,
        "stats": result.stats,
        "levels": [asdict(l) for l in result.levels]
    }

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import sys

    # Default symbol
    symbol = sys.argv[1] if len(sys.argv) > 1 else "SPY"

    print(f"Running DiNapoli backtest on {symbol}...")
    print()

    client = SchwabClient()
    backtester = DiNapoliBacktester(client)

    try:
        # Run 1-year daily backtest
        result = backtester.run_backtest(
            symbol,
            period_type="year",
            period=1,
            frequency_type="daily"
        )

        # Display results
        print(format_results(result))

        # Save to JSON
        filename = f"backtest_{symbol}_{result.start_date}_{result.end_date}.json"
        save_results_json(result, filename)
        print(f"\nResults saved to: {filename}")

    except Exception as e:
        print(f"Error: {e}")
        raise
