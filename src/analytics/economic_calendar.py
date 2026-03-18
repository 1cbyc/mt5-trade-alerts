"""
Economic calendar integration using the ForexFactory public JSON feed.
Provides upcoming high-impact event alerts and a /news command feed.
"""
import json
import logging
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

CALENDAR_URLS = [
    'https://nfs.faireconomy.media/ff_calendar_thisweek.json',
    'https://nfs.faireconomy.media/ff_calendar_nextweek.json',
]

IMPACT_RANK = {'Low': 1, 'Medium': 2, 'High': 3}

IMPACT_EMOJI = {'High': '🔴', 'Medium': '🟡', 'Low': '🟢'}

# Known symbol → affected currencies mapping
SYMBOL_TO_CURRENCIES: Dict[str, List[str]] = {
    'XAUUSD': ['USD'], 'XAGUSD': ['USD'], 'WTI': ['USD'], 'USOIL': ['USD'],
    'NAS100': ['USD'], 'US30': ['USD'], 'US500': ['USD'], 'SPX500': ['USD'],
    'EURUSD': ['EUR', 'USD'], 'GBPUSD': ['GBP', 'USD'], 'USDJPY': ['USD', 'JPY'],
    'AUDUSD': ['AUD', 'USD'], 'USDCAD': ['USD', 'CAD'], 'USDCHF': ['USD', 'CHF'],
    'NZDUSD': ['NZD', 'USD'], 'EURGBP': ['EUR', 'GBP'], 'EURJPY': ['EUR', 'JPY'],
    'GBPJPY': ['GBP', 'JPY'], 'AUDCAD': ['AUD', 'CAD'], 'AUDNZD': ['AUD', 'NZD'],
    'AUDCHF': ['AUD', 'CHF'], 'CADCHF': ['CAD', 'CHF'], 'CADJPY': ['CAD', 'JPY'],
    'CHFJPY': ['CHF', 'JPY'], 'EURCAD': ['EUR', 'CAD'], 'EURCHF': ['EUR', 'CHF'],
    'EURNZD': ['EUR', 'NZD'], 'EURAUD': ['EUR', 'AUD'], 'GBPAUD': ['GBP', 'AUD'],
    'GBPCAD': ['GBP', 'CAD'], 'GBPCHF': ['GBP', 'CHF'], 'GBPNZD': ['GBP', 'NZD'],
    'NZDCAD': ['NZD', 'CAD'], 'NZDCHF': ['NZD', 'CHF'], 'NZDJPY': ['NZD', 'JPY'],
}


def get_currencies_from_symbols(symbols: List[str]) -> List[str]:
    """Derive a list of affected fiat currencies from a list of trading symbols."""
    currencies: set = set()
    for symbol in symbols:
        # Normalise: strip broker suffixes like .x, m, _micro, etc.
        clean = symbol.upper()
        for suffix in ['.X', '.M', '_MICRO', '_SB', 'M', 'X']:
            if clean.endswith(suffix):
                clean = clean[:-len(suffix)]
                break

        matched = False
        for map_sym, map_currencies in SYMBOL_TO_CURRENCIES.items():
            if clean == map_sym or clean.startswith(map_sym):
                currencies.update(map_currencies)
                matched = True
                break

        if not matched:
            # Try to parse as a 6-character forex pair
            alpha = ''.join(c for c in clean if c.isalpha())
            if len(alpha) == 6:
                currencies.add(alpha[:3])
                currencies.add(alpha[3:])

    return sorted(currencies)


class EconomicCalendar:
    """
    Fetches and caches the ForexFactory weekly calendar and exposes helpers
    for upcoming event alerts and the /news command.
    """

    def __init__(self, min_impact: str = 'High', advance_minutes: int = 15):
        self.min_impact = min_impact
        self.advance_minutes = advance_minutes
        self._events: List[Dict] = []
        self._cache_until: Optional[datetime] = None
        self.alerted: set = set()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch(self) -> List[Dict]:
        events = []
        for url in CALENDAR_URLS:
            try:
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': 'Mozilla/5.0 (compatible; MT5AlertBot/1.0)'}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    if isinstance(data, list):
                        events.extend(data)
            except Exception as e:
                logger.warning(f"Could not fetch economic calendar from {url}: {e}")
        return events

    def _refresh(self):
        now = datetime.now(timezone.utc)
        if self._cache_until and now < self._cache_until:
            return
        fetched = self._fetch()
        if fetched:
            self._events = fetched
            self._cache_until = now + timedelta(hours=1)
            logger.info(f"Economic calendar refreshed: {len(self._events)} events loaded")
        elif not self._events:
            # First fetch failed — retry in 5 minutes rather than waiting a full hour
            self._cache_until = now + timedelta(minutes=5)

    @staticmethod
    def _parse_time(date_str: str) -> Optional[datetime]:
        """Parse an ISO 8601 datetime string (with or without tz offset) to UTC."""
        try:
            dt = datetime.fromisoformat(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_upcoming_alerts(self, currencies: List[str]) -> List[Dict]:
        """
        Return events that fall within the configured alert window and have
        not already been alerted.  Each returned dict has all original fields
        plus 'minutes_until' and 'event_key'.
        """
        self._refresh()
        now = datetime.now(timezone.utc)
        min_rank = IMPACT_RANK.get(self.min_impact, 3)
        currencies_upper = {c.upper() for c in currencies}
        result = []

        for event in self._events:
            if IMPACT_RANK.get(event.get('impact', ''), 0) < min_rank:
                continue

            country = event.get('country', '').upper()
            if currencies_upper and country not in currencies_upper:
                continue

            event_time = self._parse_time(event.get('date', ''))
            if not event_time:
                continue

            minutes_until = (event_time - now).total_seconds() / 60

            # Alert window: from advance_minutes before the event up to 5 min after
            if -5.0 <= minutes_until <= self.advance_minutes:
                event_key = f"{event.get('date', '')}|{event.get('title', '')}|{country}"
                if event_key not in self.alerted:
                    result.append({
                        **event,
                        'minutes_until': round(minutes_until),
                        'event_key': event_key,
                        'event_time_utc': event_time,
                    })

        return result

    def mark_alerted(self, event_key: str):
        self.alerted.add(event_key)

    def get_events_for_display(
        self,
        currencies: List[str] = None,
        min_impact: str = 'Medium',
        days_ahead: int = 1,
    ) -> List[Dict]:
        """
        Return calendar events for the /news command.
        Covers today + days_ahead days, sorted by time.
        """
        self._refresh()
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days_ahead)
        min_rank = IMPACT_RANK.get(min_impact, 2)
        currencies_upper = {c.upper() for c in currencies} if currencies else set()
        result = []

        for event in self._events:
            if IMPACT_RANK.get(event.get('impact', ''), 0) < min_rank:
                continue
            if currencies_upper:
                country = event.get('country', '').upper()
                if country not in currencies_upper:
                    continue
            event_time = self._parse_time(event.get('date', ''))
            if not event_time:
                continue
            if now <= event_time <= cutoff:
                result.append({**event, 'event_time_utc': event_time})

        return sorted(result, key=lambda e: e['event_time_utc'])

    def clean_old_alerts(self):
        """Trim the alerted set to prevent unbounded growth (keep last 500)."""
        if len(self.alerted) > 500:
            self.alerted = set(list(self.alerted)[-500:])
