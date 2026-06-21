import pandas as pd
import requests
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", None)
DEFAULT_POSTER_URL = "https://via.placeholder.com/500x750?text=No+Poster+Available"

def fetch_poster_fallback(title: str, year: str = None) -> str:
    """
    Fetches a movie poster from the TMDB API.
    If no API key is set or the request fails, returns a default placeholder image.
    """
    if not TMDB_API_KEY:
        logger.warning("TMDB_API_KEY not found. Using default poster for '%s'.", title)
        return DEFAULT_POSTER_URL

    try:
        # Note: This is a simplified TMDB search endpoint.
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
        if year:
            search_url += f"&year={year}"
            
        response = requests.get(search_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data.get("results") and len(data["results"]) > 0:
            poster_path = data["results"][0].get("poster_path")
            if poster_path:
                return f"https://image.tmdb.org/t/p/w500{poster_path}"
                
        return DEFAULT_POSTER_URL
    except Exception as e:
        logger.error(f"Error fetching poster for '{title}': {e}")
        return DEFAULT_POSTER_URL

def parse_genres(genre_string):
    """
    Converts a comma-separated genre string into a cleaned list.
    Example: "Action, Adventure, Science Fiction" -> ["Action", "Adventure", "Science Fiction"]
    """
    if pd.isna(genre_string):
        return []
    return [g.strip() for g in str(genre_string).split(",")]

def load_movie_dataset(filepath: str) -> pd.DataFrame:
    """
    Loads and cleans the raw movie CSV dataset.
    """
    logger.info(f"Loading dataset from {filepath}")
    
    try:
        # TMDB CSVs often have embedded newlines and long strings causing buffer overflows.
        df = pd.read_csv(filepath, lineterminator='\n', engine='c')
    except pd.errors.ParserError:
        # Fallback to python engine which is slower but handles malformed data better
        df = pd.read_csv(filepath, engine='python', on_bad_lines='skip')
    except FileNotFoundError:
        logger.error(f"Dataset not found at {filepath}")
        raise
        
    # Clean up null overviews so the NLP TF-IDF engine doesn't crash
    df['Overview'] = df['Overview'].fillna("No overview available.")
    
    # Clean up null titles
    df['Title'] = df['Title'].fillna("Unknown Title")
    
    # Parse Genre strings into Python lists
    if 'Genre' in df.columns:
        df['Genre_List'] = df['Genre'].apply(parse_genres)
        
    # Apply poster fallback for missing posters
    # In a real heavy dataset (10k rows), we wouldn't want to run this synchronously for every single row
    # during load time. So we'll fill nulls with the default immediately, or apply fallback dynamically in the UI.
    # For now, we will fill completely missing poster columns with the default URL.
    if 'Poster_Url' in df.columns:
        df['Poster_Url'] = df['Poster_Url'].fillna(DEFAULT_POSTER_URL)
        
    return df

if __name__ == "__main__":
    # Test execution
    df = load_movie_dataset("../datasets/mymoviedb (1).csv")
    print(f"Loaded {len(df)} movies successfully.")
    print("Sample Genre Array:", df['Genre_List'].iloc[0])
