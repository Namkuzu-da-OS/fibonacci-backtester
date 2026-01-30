"""
Schwab API Client
Connects to the local Schwab Trading Dashboard API
"""

import requests
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Candle:
    """OHLCV candle data"""
    timestamp: int  # Unix milliseconds
    open: float
    high: float
    low: float
    close: float
    volume: int

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp / 1000)


class SchwabClient:
    """Client for the Schwab Trading Dashboard API"""

    def __init__(self, base_url: str = "http://192.168.10.239:8000"):
        self.base_url = base_url
        self.session = requests.Session()

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request to API"""
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def check_auth(self) -> Dict[str, Any]:
        """Check Schwab authentication status"""
        return self._get("/api/auth/schwab/status")

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get current quote for a symbol"""
        return self._get(f"/api/quotes/{symbol}")

    def get_history(
        self,
        symbol: str,
        period_type: str = "month",
        period: int = 3,
        frequency_type: str = "daily",
        frequency: int = 1,
        extended_hours: bool = False
    ) -> List[Candle]:
        """
        Get historical price data.

        Args:
            symbol: Stock symbol (e.g., "SPY")
            period_type: "day", "month", "year", "ytd"
            period: Number of periods
            frequency_type: "minute", "daily", "weekly", "monthly"
            frequency: 1, 5, 10, 15, 30 (for minute)
            extended_hours: Include extended hours data

        Returns:
            List of Candle objects
        """
        params = {
            "period_type": period_type,
            "period": period,
            "frequency_type": frequency_type,
            "frequency": frequency,
            "extended_hours": str(extended_hours).lower()
        }

        data = self._get(f"/api/history/{symbol}", params)

        candles = []
        for c in data.get("candles", []):
            candles.append(Candle(
                timestamp=c["datetime"],
                open=c["open"],
                high=c["high"],
                low=c["low"],
                close=c["close"],
                volume=c["volume"]
            ))

        return candles

    def get_technicals(self, symbol: str) -> Dict[str, Any]:
        """Get technical indicators for a symbol"""
        return self._get(f"/api/technicals/{symbol}")


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    client = SchwabClient()

    # Check auth
    auth = client.check_auth()
    print(f"Auth status: {auth.get('authenticated', False)}")

    # Get SPY quote
    quote = client.get_quote("SPY")
    print(f"\nSPY Quote:")
    print(f"  Price: ${quote['quote']['lastPrice']:.2f}")
    print(f"  Change: {quote['quote']['netChange']:+.2f} ({quote['quote']['netPercentChange']:+.2f}%)")

    # Get history
    candles = client.get_history("SPY", period_type="month", period=1)
    print(f"\nSPY History ({len(candles)} candles):")
    for c in candles[-5:]:
        print(f"  {c.datetime.strftime('%Y-%m-%d')}: O={c.open:.2f} H={c.high:.2f} L={c.low:.2f} C={c.close:.2f}")
