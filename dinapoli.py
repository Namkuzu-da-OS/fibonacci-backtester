"""
DiNapoli Levels Calculator
Based on "Trading with DiNapoli Levels" by Joe DiNapoli

Core calculations:
- Fibnodes (F3 and F5 retracements)
- Objective Points (COP, OP, XOP expansions)
- Confluence detection
- Agreement detection
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import math


@dataclass
class Fibnode:
    """A Fibonacci retracement level (support/resistance)"""
    price: float
    ratio: float  # 0.382 or 0.618
    reaction_idx: int  # Index of the reaction point that created this
    reaction_price: float  # Price of the reaction point
    focus_price: float  # Price of the focus number


@dataclass
class ObjectivePoint:
    """A Fibonacci expansion target (profit objective)"""
    price: float
    ratio: float  # 0.618 (COP), 1.0 (OP), or 1.618 (XOP)
    name: str  # "COP", "OP", or "XOP"
    point_a: float
    point_b: float
    point_c: float


@dataclass
class Confluence:
    """When two Fibnodes from different reactions align"""
    price_low: float
    price_high: float
    fibnode_1: Fibnode
    fibnode_2: Fibnode
    strength: float  # How close they are (0-1, 1 = exact)


@dataclass
class Agreement:
    """When a Fibnode and Objective Point align"""
    price_low: float
    price_high: float
    fibnode: Fibnode
    objective_point: ObjectivePoint
    strength: float


@dataclass
class SwingPoint:
    """A significant high or low point in price action"""
    price: float
    index: int
    is_high: bool
    timestamp: Optional[int] = None


class DiNapoliCalculator:
    """
    Calculator for DiNapoli Levels

    DiNapoli uses ONLY:
    - .382 and .618 for retracements (Fibnodes)
    - .618, 1.0, and 1.618 for expansions (Objective Points)
    """

    RETRACEMENT_RATIOS = [0.382, 0.618]
    EXPANSION_RATIOS = [(0.618, "COP"), (1.0, "OP"), (1.618, "XOP")]

    def __init__(self, confluence_tolerance_pct: float = 0.5):
        """
        Args:
            confluence_tolerance_pct: How close two Fibnodes must be to form Confluence
                                     (as percentage of price range)
        """
        self.confluence_tolerance_pct = confluence_tolerance_pct

    # =========================================================================
    # FIBNODE CALCULATIONS
    # =========================================================================

    def calculate_fibnodes(
        self,
        focus_price: float,
        reaction_points: List[SwingPoint],
        is_uptrend: bool
    ) -> List[Fibnode]:
        """
        Calculate Fibnodes (retracement levels) for a market swing.

        Args:
            focus_price: The extreme of the market swing (Focus Number)
            reaction_points: List of reaction lows (uptrend) or highs (downtrend)
            is_uptrend: True if we're measuring an up move

        Returns:
            List of Fibnodes (2 per reaction point: F3 and F5)

        Formula (for uptrend):
            F3 = B - 0.382(B - A)
            F5 = B - 0.618(B - A)

        Where B = Focus Number, A = Reaction point
        """
        fibnodes = []

        for reaction in reaction_points:
            a = reaction.price
            b = focus_price

            for ratio in self.RETRACEMENT_RATIOS:
                if is_uptrend:
                    # For uptrend: Focus is high, reactions are lows
                    # Fibnodes provide SUPPORT below the focus
                    price = b - ratio * (b - a)
                else:
                    # For downtrend: Focus is low, reactions are highs
                    # Fibnodes provide RESISTANCE above the focus
                    price = b + ratio * (a - b)

                fibnodes.append(Fibnode(
                    price=round(price, 4),
                    ratio=ratio,
                    reaction_idx=reaction.index,
                    reaction_price=a,
                    focus_price=b
                ))

        return fibnodes

    # =========================================================================
    # OBJECTIVE POINT CALCULATIONS
    # =========================================================================

    def calculate_objective_points(
        self,
        point_a: float,
        point_b: float,
        point_c: float,
        is_uptrend: bool
    ) -> List[ObjectivePoint]:
        """
        Calculate Objective Points (profit targets) using 3-point ABC system.

        CRITICAL: Expansions are calculated FROM Point C, NOT Point B!

        Args:
            point_a: Start of the initial move
            point_b: End of the initial move (the thrust)
            point_c: End of the retracement (entry point)
            is_uptrend: True if targeting upside

        Returns:
            List of 3 Objective Points: COP, OP, XOP

        Formulas (for uptrend):
            COP = 0.618(B - A) + C
            OP  = (B - A) + C
            XOP = 1.618(B - A) + C
        """
        ops = []
        ab_distance = abs(point_b - point_a)

        for ratio, name in self.EXPANSION_RATIOS:
            expansion = ratio * ab_distance

            if is_uptrend:
                price = point_c + expansion
            else:
                price = point_c - expansion

            ops.append(ObjectivePoint(
                price=round(price, 4),
                ratio=ratio,
                name=name,
                point_a=point_a,
                point_b=point_b,
                point_c=point_c
            ))

        return ops

    # =========================================================================
    # CONFLUENCE DETECTION
    # =========================================================================

    def find_confluence(
        self,
        fibnodes: List[Fibnode],
        price_range: float
    ) -> List[Confluence]:
        """
        Find Confluence areas where Fibnodes from different reactions align.

        Rules (from DiNapoli):
        1. Must be between a .382 and a .618 Fibnode
        2. Fibnodes must come from DIFFERENT Reaction Numbers
        3. "Closeness" depends on volatility and time frame

        Args:
            fibnodes: List of all Fibnodes
            price_range: The price range of the swing (for tolerance calc)

        Returns:
            List of Confluence areas
        """
        confluences = []
        tolerance = price_range * (self.confluence_tolerance_pct / 100)

        # Group fibnodes by reaction
        for i, fn1 in enumerate(fibnodes):
            for fn2 in fibnodes[i+1:]:
                # Must be from different reactions
                if fn1.reaction_idx == fn2.reaction_idx:
                    continue

                # Must be between .382 and .618 (one of each)
                ratios = sorted([fn1.ratio, fn2.ratio])
                if ratios != [0.382, 0.618]:
                    continue

                # Check if prices are close enough
                price_diff = abs(fn1.price - fn2.price)
                if price_diff <= tolerance:
                    strength = 1 - (price_diff / tolerance) if tolerance > 0 else 1.0

                    confluences.append(Confluence(
                        price_low=min(fn1.price, fn2.price),
                        price_high=max(fn1.price, fn2.price),
                        fibnode_1=fn1,
                        fibnode_2=fn2,
                        strength=round(strength, 3)
                    ))

        return confluences

    # =========================================================================
    # AGREEMENT DETECTION
    # =========================================================================

    def find_agreement(
        self,
        fibnodes: List[Fibnode],
        objective_points: List[ObjectivePoint],
        price_range: float
    ) -> List[Agreement]:
        """
        Find Agreement areas where a Fibnode and Objective Point align.

        Args:
            fibnodes: List of Fibnodes
            objective_points: List of Objective Points
            price_range: The price range (for tolerance calculation)

        Returns:
            List of Agreement areas
        """
        agreements = []
        tolerance = price_range * (self.confluence_tolerance_pct / 100)

        for fn in fibnodes:
            for op in objective_points:
                price_diff = abs(fn.price - op.price)
                if price_diff <= tolerance:
                    strength = 1 - (price_diff / tolerance) if tolerance > 0 else 1.0

                    agreements.append(Agreement(
                        price_low=min(fn.price, op.price),
                        price_high=max(fn.price, op.price),
                        fibnode=fn,
                        objective_point=op,
                        strength=round(strength, 3)
                    ))

        return agreements


# =============================================================================
# SWING DETECTION
# =============================================================================

def find_swing_points(
    highs: List[float],
    lows: List[float],
    lookback: int = 5
) -> Tuple[List[SwingPoint], List[SwingPoint]]:
    """
    Find significant swing highs and lows in price data.

    Args:
        highs: List of high prices
        lows: List of low prices
        lookback: Number of bars to look back/forward for swing detection

    Returns:
        Tuple of (swing_highs, swing_lows)
    """
    swing_highs = []
    swing_lows = []

    for i in range(lookback, len(highs) - lookback):
        # Check for swing high
        is_swing_high = True
        for j in range(i - lookback, i + lookback + 1):
            if j != i and highs[j] >= highs[i]:
                is_swing_high = False
                break

        if is_swing_high:
            swing_highs.append(SwingPoint(
                price=highs[i],
                index=i,
                is_high=True
            ))

        # Check for swing low
        is_swing_low = True
        for j in range(i - lookback, i + lookback + 1):
            if j != i and lows[j] <= lows[i]:
                is_swing_low = False
                break

        if is_swing_low:
            swing_lows.append(SwingPoint(
                price=lows[i],
                index=i,
                is_high=False
            ))

    return swing_highs, swing_lows


def identify_market_swing(
    swing_highs: List[SwingPoint],
    swing_lows: List[SwingPoint]
) -> Tuple[Optional[SwingPoint], List[SwingPoint], bool]:
    """
    Identify the current market swing and its reaction points.

    Returns:
        Tuple of (focus_point, reaction_points, is_uptrend)
    """
    if not swing_highs or not swing_lows:
        return None, [], True

    # Get most recent high and low
    latest_high = max(swing_highs, key=lambda x: x.index)
    latest_low = max(swing_lows, key=lambda x: x.index)

    # Determine trend based on which came last
    if latest_high.index > latest_low.index:
        # Uptrend: Focus is the high, reactions are the lows before it
        focus = latest_high
        reactions = [l for l in swing_lows if l.index < focus.index]
        is_uptrend = True
    else:
        # Downtrend: Focus is the low, reactions are the highs before it
        focus = latest_low
        reactions = [h for h in swing_highs if h.index < focus.index]
        is_uptrend = False

    # Sort reactions by index (most recent first for DiNapoli's method)
    reactions.sort(key=lambda x: x.index, reverse=True)

    return focus, reactions, is_uptrend


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example: Calculate DiNapoli Levels for a simple uptrend

    calc = DiNapoliCalculator(confluence_tolerance_pct=0.5)

    # Uptrend example
    focus = 100.0  # Recent high (Focus Number)
    reactions = [
        SwingPoint(price=90.0, index=0, is_high=False),  # Primary reaction (*)
        SwingPoint(price=92.0, index=5, is_high=False),  # Secondary reaction
    ]

    print("=" * 60)
    print("DINAPOLI LEVELS - UPTREND EXAMPLE")
    print("=" * 60)
    print(f"Focus Number: {focus}")
    print(f"Reactions: {[r.price for r in reactions]}")
    print()

    # Calculate Fibnodes
    fibnodes = calc.calculate_fibnodes(focus, reactions, is_uptrend=True)
    print("FIBNODES (Support Levels):")
    for fn in sorted(fibnodes, key=lambda x: x.price, reverse=True):
        ratio_name = "F3" if fn.ratio == 0.382 else "F5"
        marker = "*" if fn.reaction_price == min(r.price for r in reactions) else ""
        print(f"  {ratio_name}{marker} @ {fn.price:.2f} (from reaction @ {fn.reaction_price})")
    print()

    # Find Confluence
    price_range = focus - min(r.price for r in reactions)
    confluences = calc.find_confluence(fibnodes, price_range)
    if confluences:
        print("CONFLUENCE AREAS:")
        for conf in confluences:
            print(f"  K @ {conf.price_low:.2f} - {conf.price_high:.2f} (strength: {conf.strength:.0%})")
    print()

    # Calculate Objective Points (assuming entry at F5)
    point_a = reactions[0].price  # 90.0
    point_b = focus  # 100.0
    point_c = fibnodes[1].price if len(fibnodes) > 1 else 95.0  # Entry after retracement

    ops = calc.calculate_objective_points(point_a, point_b, point_c, is_uptrend=True)
    print("OBJECTIVE POINTS (Profit Targets):")
    for op in ops:
        print(f"  {op.name} @ {op.price:.2f}")
    print()

    # Find Agreement
    agreements = calc.find_agreement(fibnodes, ops, price_range)
    if agreements:
        print("AGREEMENT AREAS:")
        for agr in agreements:
            print(f"  {agr.fibnode.ratio} Fibnode + {agr.objective_point.name} @ {agr.price_low:.2f}")
