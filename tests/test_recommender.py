import pytest
import pandas as pd
from src.recommender import RecommenderSystem

@pytest.fixture
def dummy_movies():
    data = {
        "Title": ["Superhero A", "Superhero B", "Romance A"],
        "Overview": [
            "A superhero fights bad guys to save the world.",
            "Another superhero uses powers to save the world.",
            "A couple falls in love during a vacation."
        ],
        "Genre_List": [
            ["Action", "Sci-Fi"],
            ["Action", "Sci-Fi"],
            ["Romance", "Drama"]
        ]
    }
    return pd.DataFrame(data)

def test_recommender_system(dummy_movies):
    rec = RecommenderSystem(dummy_movies)
    
    # Recommend for Superhero A
    recommendations = rec.get_recommendations("Superhero A", top_n=1)
    
    # It should recommend Superhero B, not Romance A
    assert len(recommendations) == 1
    assert recommendations.iloc[0]["Title"] == "Superhero B"

def test_recommender_missing_movie(dummy_movies):
    rec = RecommenderSystem(dummy_movies)
    
    # Recommend for a missing movie
    recommendations = rec.get_recommendations("Missing Movie", top_n=1)
    assert len(recommendations) == 0
