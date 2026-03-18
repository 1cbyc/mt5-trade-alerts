"""
Correlation tracker — alerts when normally-correlated symbols diverge.

Uses Pearson correlation on recent H1 close prices fetched directly from MT5.
No external dependencies beyond MetaTrader5 (numpy used only if available,
falls back to pure-Python otherwise).
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Well-known correlation pairs with expected direction (+1 or -1)
KNOWN_PAIRS = {
    ('XAUUSD', 'XAGUSD'): +1,   # gold / silver — positive
    ('NAS100', 'US30'):    +1,   # tech / dow — positive
    ('NAS100', 'US500'):   +1,   # tech / S&P — positive
    ('XAUUSD', 'DXY'):    -1,    # gold / dollar — negative (informational only)
}


def _pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    """Pure-Python Pearson correlation coefficient."""
    n = len(xs)
    if n < 3:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = sum((x - mean_x) ** 2 for x in xs) ** 0.5
    den_y = sum((y - mean_y) ** 2 for y in ys) ** 0.5
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


class CorrelationTracker:
    """
    Tracks rolling correlation between configured symbol pairs and fires alerts
    when correlation drops below a threshold.
    """

    def __init__(
        self,
        pairs: List[Tuple[str, str]],
        lookback_bars: int = 50,
        alert_threshold: float = 0.5,
        timeframe: int = 16385,   # MT5 TIMEFRAME_H1
    ):
        self.pairs = pairs
        self.lookback_bars = lookback_bars
        self.alert_threshold = alert_threshold
        self.timeframe = timeframe
        # Track last known correlation per pair to detect drops
        self._last_correlation: Dict[Tuple[str, str], float] = {}
        self._alerted: set = set()

    def _get_closes(self, symbol: str) -> Optional[List[float]]:
        """Fetch the last N H1 close prices for a symbol."""
        try:
            import MetaTrader5 as mt5
            bars = mt5.copy_rates_from_pos(symbol, self.timeframe, 0, self.lookback_bars)
            if bars is None or len(bars) < 10:
                return None
            return [float(b[4]) for b in bars]  # index 4 = close
        except Exception as e:
            logger.warning(f"CorrelationTracker: could not fetch closes for {symbol}: {e}")
            return None

    def check_divergences(self) -> List[Dict]:
        """
        Check all configured pairs for correlation divergence.

        Returns a list of alert dicts for pairs that have diverged below the
        threshold and haven't already been alerted this session.
        """
        alerts = []
        for pair in self.pairs:
            sym_a, sym_b = pair
            closes_a = self._get_closes(sym_a)
            closes_b = self._get_closes(sym_b)
            if not closes_a or not closes_b:
                continue

            # Align lengths
            n = min(len(closes_a), len(closes_b))
            closes_a = closes_a[-n:]
            closes_b = closes_b[-n:]

            # Use % returns for correlation (more meaningful than raw prices)
            returns_a = [(closes_a[i] - closes_a[i-1]) / closes_a[i-1]
                         for i in range(1, n)]
            returns_b = [(closes_b[i] - closes_b[i-1]) / closes_b[i-1]
                         for i in range(1, n)]

            corr = _pearson(returns_a, returns_b)
            if corr is None:
                continue

            prev = self._last_correlation.get(pair)
            self._last_correlation[pair] = corr

            # Alert when correlation drops below threshold
            # (and previous reading was above — i.e. this is a fresh divergence)
            alert_key = f"corr_{sym_a}_{sym_b}_{round(corr, 1)}"
            if corr < self.alert_threshold and alert_key not in self._alerted:
                # Only alert if correlation was previously decent (> 0.6)
                if prev is None or prev > 0.6:
                    alerts.append({
                        'symbol_a': sym_a,
                        'symbol_b': sym_b,
                        'correlation': round(corr, 3),
                        'previous_correlation': round(prev, 3) if prev is not None else None,
                        'threshold': self.alert_threshold,
                        'bars_analysed': n - 1,
                        'alert_key': alert_key,
                    })
                    self._alerted.add(alert_key)

        return alerts

    def get_all_correlations(self) -> List[Dict]:
        """
        Return current correlation for all configured pairs.
        Used by the /correlation command.
        """
        result = []
        for pair in self.pairs:
            sym_a, sym_b = pair
            closes_a = self._get_closes(sym_a)
            closes_b = self._get_closes(sym_b)
            if not closes_a or not closes_b:
                result.append({'symbol_a': sym_a, 'symbol_b': sym_b, 'correlation': None,
                                'error': 'Could not fetch price data'})
                continue

            n = min(len(closes_a), len(closes_b))
            closes_a = closes_a[-n:]
            closes_b = closes_b[-n:]
            returns_a = [(closes_a[i] - closes_a[i-1]) / closes_a[i-1] for i in range(1, n)]
            returns_b = [(closes_b[i] - closes_b[i-1]) / closes_b[i-1] for i in range(1, n)]
            corr = _pearson(returns_a, returns_b)

            result.append({
                'symbol_a': sym_a,
                'symbol_b': sym_b,
                'correlation': round(corr, 3) if corr is not None else None,
                'bars_analysed': n - 1,
            })

        return result

    def clean_old_alerts(self):
        if len(self._alerted) > 200:
            self._alerted = set(list(self._alerted)[-200:])
