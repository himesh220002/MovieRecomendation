import pytest
import pandas as pd
from src.data_loader import parse_genres, fetch_poster_fallback, DEFAULT_POSTER_URL

def test_parse_genres():
    # Test valid string
    assert parse_genres("Action, Sci-Fi") == ["Action", "Sci-Fi"]
    # Test single genre
    assert parse_genres("Comedy") == ["Comedy"]
    # Test NaN/None
    assert parse_genres(pd.NA) == []
    assert parse_genres(None) == []

def test_fetch_poster_fallback_no_key():
    # Since TMDB_API_KEY is not set in tests by default, this should return default
    url = fetch_poster_fallback("Spider-Man")
    assert url == DEFAULT_POSTER_URL

# Note: testing load_movie_dataset requires a dummy CSV file or mocking pd.read_csv.
