"""Utils for the scraper"""
from src.scraper.mangafire_to import MangaFireToScraper
from src.scraper.asura_scans import AsuraScansScraper


def get_scraper(scanlation_group: str):
    """Get the appropriate scraper instance based on scanlation group"""
    if scanlation_group == "mangafire_to":
        return MangaFireToScraper()
    elif scanlation_group == "asura_scans":
        return AsuraScansScraper()
    else:
        raise ValueError(f"Unknown scanlation group: {scanlation_group}")
