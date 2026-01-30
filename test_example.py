"""
DiNapoli Levels - Concrete Example
Shows exactly how the levels are calculated step by step
"""

from schwab_client import SchwabClient
from dinapoli import (
    DiNapoliCalculator,
    SwingPoint,
    find_swing_points,
    identify_market_swing
)

def run_example(symbol: str = "SPY"):
    """Show a concrete example of DiNapoli level calculation"""

    client = SchwabClient()
    calc = DiNapoliCalculator(confluence_tolerance_pct=0.5)

    # Get recent data
    candles = client.get_history(symbol, period_type="month", period=3, frequency_type="daily")

    print("=" * 70)
    print(f"DINAPOLI LEVELS - CONCRETE EXAMPLE FOR {symbol}")
    print("=" * 70)
    print(f"\nAnalyzing {len(candles)} daily candles")
    print(f"Date range: {candles[0].datetime.strftime('%Y-%m-%d')} to {candles[-1].datetime.strftime('%Y-%m-%d')}")

    # Extract prices
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]

    # Find swing points
    swing_highs, swing_lows = find_swing_points(highs, lows, lookback=5)

    print(f"\n" + "-" * 70)
    print("STEP 1: IDENTIFY SWING POINTS (Reaction Numbers)")
    print("-" * 70)
    print(f"\nSwing Highs found: {len(swing_highs)}")
    for sh in swing_highs[-5:]:  # Last 5
        print(f"  {candles[sh.index].datetime.strftime('%Y-%m-%d')}: ${sh.price:.2f}")

    print(f"\nSwing Lows found: {len(swing_lows)}")
    for sl in swing_lows[-5:]:  # Last 5
        print(f"  {candles[sl.index].datetime.strftime('%Y-%m-%d')}: ${sl.price:.2f}")

    # Identify current market swing
    focus, reactions, is_uptrend = identify_market_swing(swing_highs, swing_lows)

    print(f"\n" + "-" * 70)
    print("STEP 2: IDENTIFY MARKET SWING")
    print("-" * 70)
    trend_str = "UPTREND" if is_uptrend else "DOWNTREND"
    print(f"\nCurrent Trend: {trend_str}")
    print(f"Focus Number (B): ${focus.price:.2f} on {candles[focus.index].datetime.strftime('%Y-%m-%d')}")
    print(f"\nReaction Points (A values):")
    for i, r in enumerate(reactions[:5]):
        marker = " (*)" if i == 0 else ""  # Primary reaction
        print(f"  R{i+1}{marker}: ${r.price:.2f} on {candles[r.index].datetime.strftime('%Y-%m-%d')}")

    # Calculate Fibnodes
    print(f"\n" + "-" * 70)
    print("STEP 3: CALCULATE FIBNODES (Support/Resistance)")
    print("-" * 70)
    print("\nUsing DiNapoli's formulas:")
    print("  F3 = B - 0.382(B - A)")
    print("  F5 = B - 0.618(B - A)")

    fibnodes = calc.calculate_fibnodes(focus.price, reactions[:3], is_uptrend)

    print(f"\nFibnodes calculated:")
    for fn in sorted(fibnodes, key=lambda x: x.price, reverse=True):
        ratio_name = "F3 (.382)" if fn.ratio == 0.382 else "F5 (.618)"
        b = fn.focus_price
        a = fn.reaction_price

        print(f"\n  {ratio_name} from Reaction @ ${a:.2f}:")
        print(f"    Formula: {b:.2f} - {fn.ratio}*({b:.2f} - {a:.2f})")
        print(f"    = {b:.2f} - {fn.ratio}*{b-a:.2f}")
        print(f"    = {b:.2f} - {fn.ratio*(b-a):.2f}")
        print(f"    = ${fn.price:.2f}")

    # Find Confluence
    print(f"\n" + "-" * 70)
    print("STEP 4: FIND CONFLUENCE (Aligned Fibnodes)")
    print("-" * 70)
    print("\nRule: Confluence occurs when F3 from one reaction aligns with F5 from another")

    price_range = abs(focus.price - min(r.price for r in reactions[:3]))
    confluences = calc.find_confluence(fibnodes, price_range)

    if confluences:
        for conf in confluences:
            print(f"\n  CONFLUENCE FOUND!")
            print(f"    F3 @ ${conf.fibnode_1.price:.2f} (from reaction @ ${conf.fibnode_1.reaction_price:.2f})")
            print(f"    F5 @ ${conf.fibnode_2.price:.2f} (from reaction @ ${conf.fibnode_2.reaction_price:.2f})")
            print(f"    Zone: ${conf.price_low:.2f} - ${conf.price_high:.2f}")
            print(f"    Strength: {conf.strength:.0%}")
    else:
        print("\n  No Confluence found (fibnodes not close enough)")

    # Calculate Objective Points
    print(f"\n" + "-" * 70)
    print("STEP 5: CALCULATE OBJECTIVE POINTS (Profit Targets)")
    print("-" * 70)
    print("\nUsing DiNapoli's formulas (calculated FROM Point C):")
    print("  COP = 0.618(B - A) + C")
    print("  OP  = (B - A) + C")
    print("  XOP = 1.618(B - A) + C")

    # Use the first (primary) reaction as A
    point_a = reactions[0].price
    point_b = focus.price

    # Find potential Point C (where price retraced to a Fibnode)
    # For this example, use the .618 Fibnode
    f5_nodes = [fn for fn in fibnodes if fn.ratio == 0.618]
    if f5_nodes:
        point_c = f5_nodes[0].price
    else:
        point_c = point_b - 0.618 * (point_b - point_a)

    print(f"\n  Point A (start of move): ${point_a:.2f}")
    print(f"  Point B (end of move/Focus): ${point_b:.2f}")
    print(f"  Point C (retracement entry): ${point_c:.2f}")

    ops = calc.calculate_objective_points(point_a, point_b, point_c, is_uptrend)

    print(f"\n  AB Distance: ${abs(point_b - point_a):.2f}")

    for op in ops:
        ab = abs(point_b - point_a)
        expansion = op.ratio * ab
        print(f"\n  {op.name}:")
        print(f"    Formula: {op.ratio}*({point_b:.2f} - {point_a:.2f}) + {point_c:.2f}")
        print(f"    = {op.ratio}*{ab:.2f} + {point_c:.2f}")
        print(f"    = {expansion:.2f} + {point_c:.2f}")
        print(f"    = ${op.price:.2f}")

    # Summary
    print(f"\n" + "=" * 70)
    print("SUMMARY - DINAPOLI LEVELS FOR " + symbol)
    print("=" * 70)

    current_price = candles[-1].close
    print(f"\nCurrent Price: ${current_price:.2f}")

    print(f"\nSUPPORT LEVELS (Fibnodes):")
    for fn in sorted(fibnodes, key=lambda x: x.price, reverse=True):
        ratio_name = "F3" if fn.ratio == 0.382 else "F5"
        dist = ((current_price - fn.price) / current_price) * 100
        print(f"  {ratio_name}: ${fn.price:.2f} ({dist:+.1f}% from current)")

    if confluences:
        print(f"\nCONFLUENCE ZONES (Strongest S/R):")
        for conf in confluences:
            mid = (conf.price_low + conf.price_high) / 2
            dist = ((current_price - mid) / current_price) * 100
            print(f"  K: ${conf.price_low:.2f} - ${conf.price_high:.2f} ({dist:+.1f}% from current)")

    print(f"\nPROFIT TARGETS (Objective Points):")
    for op in ops:
        dist = ((op.price - current_price) / current_price) * 100
        print(f"  {op.name}: ${op.price:.2f} ({dist:+.1f}% from current)")

    print()


if __name__ == "__main__":
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else "SPY"
    run_example(symbol)
