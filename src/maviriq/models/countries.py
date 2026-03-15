"""Static country metadata for geographic personalization.

Used by the confidence scorer and synthesis agent to make market-size-aware
adjustments rather than treating Lithuania and Germany identically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class CountryMeta:
    name: str
    population_m: float  # millions
    gdp_per_capita_usd: int  # nominal, rounded
    primary_language: str
    market_tier: Literal["small", "medium", "large"]


# Tier definitions:
#   small  — population < 10M (Baltics, Nordics excl. Sweden)
#   medium — population 10-50M (Nordics, CE, Benelux, Ireland)
#   large  — population > 50M (US, UK, DE, FR, ES, IT)

COUNTRIES: dict[str, CountryMeta] = {
    "Lithuania": CountryMeta("Lithuania", 2.8, 25_000, "lt", "small"),
    "Latvia": CountryMeta("Latvia", 1.8, 21_000, "lv", "small"),
    "Estonia": CountryMeta("Estonia", 1.4, 29_000, "et", "small"),
    "Finland": CountryMeta("Finland", 5.6, 53_000, "fi", "small"),
    "Norway": CountryMeta("Norway", 5.5, 82_000, "no", "small"),
    "Denmark": CountryMeta("Denmark", 5.9, 68_000, "da", "small"),
    "Ireland": CountryMeta("Ireland", 5.1, 100_000, "en", "small"),
    "Austria": CountryMeta("Austria", 9.1, 56_000, "de", "small"),
    "Switzerland": CountryMeta("Switzerland", 8.8, 93_000, "de", "small"),
    "Poland": CountryMeta("Poland", 37.0, 19_000, "pl", "medium"),
    "Czech Republic": CountryMeta("Czech Republic", 10.8, 27_000, "cs", "medium"),
    "Netherlands": CountryMeta("Netherlands", 17.8, 57_000, "nl", "medium"),
    "Sweden": CountryMeta("Sweden", 10.5, 56_000, "sv", "medium"),
    "United Kingdom": CountryMeta("United Kingdom", 67.0, 46_000, "en", "large"),
    "Germany": CountryMeta("Germany", 84.0, 52_000, "de", "large"),
    "France": CountryMeta("France", 68.0, 44_000, "fr", "large"),
    "Spain": CountryMeta("Spain", 47.0, 30_000, "es", "large"),
    "Italy": CountryMeta("Italy", 59.0, 35_000, "it", "large"),
    "United States": CountryMeta("United States", 335.0, 80_000, "en", "large"),
}


def get_country_meta(target_market: str | None) -> CountryMeta | None:
    """Look up metadata for a target market. Returns None for Global/unknown."""
    if not target_market or target_market == "Global":
        return None
    return COUNTRIES.get(target_market)
