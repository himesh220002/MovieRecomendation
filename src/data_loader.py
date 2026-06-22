import pandas as pd
import requests
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", None)
DEFAULT_POSTER_URL = "https://via.placeholder.com/500x750?text=No+Poster+Available"

import urllib.parse

def fetch_poster_fallback(title: str, media_type: str = "Movie", year: str = None) -> str:
    """
    Fetches a movie or TV poster dynamically.
    For TV shows, it uses TVMaze (free, no API key).
    For Movies, it uses TMDB if TMDB_API_KEY is set.
    """
    if media_type == "TV Series":
        try:
            search_url = f"https://api.tvmaze.com/search/shows?q={urllib.parse.quote(title)}"
            response = requests.get(search_url, timeout=5)
            response.raise_for_status()
            data = response.json()
            if data and len(data) > 0 and 'show' in data[0] and 'image' in data[0]['show'] and data[0]['show']['image']:
                return data[0]['show']['image'].get('original', DEFAULT_POSTER_URL)
        except Exception as e:
            logger.error(f"Error fetching TVMaze poster for '{title}': {e}")
            return DEFAULT_POSTER_URL

    if not TMDB_API_KEY:
        logger.warning("TMDB_API_KEY not found. Using default poster for '%s'.", title)
        return DEFAULT_POSTER_URL

    try:
        endpoint = "tv" if media_type == "TV Series" else "movie"
        search_url = f"https://api.themoviedb.org/3/search/{endpoint}?api_key={TMDB_API_KEY}&query={title}"
        if year:
            if endpoint == "tv":
                search_url += f"&first_air_date_year={year}"
            else:
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

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes columns from different schemas (like TV Series) into the unified standard schema.
    """
    COLUMN_MAPPINGS = {
        "IMDb Rating": "Vote_Average",
        "Poster URL": "Poster_Url",
        "Trailer URL": "Trailer_Url",
        "Release Year": "Release_Date",
        "Network": "Network",
        "Seasons": "Seasons",
        "Episodes": "Episodes"
    }
    df = df.rename(columns=COLUMN_MAPPINGS)
    
    # Check if Media_Type can be inferred
    if "Media_Type" not in df.columns:
        if "Seasons" in df.columns or "Episodes" in df.columns:
            df["Media_Type"] = "TV Series"
        else:
            df["Media_Type"] = "Movie"
            
    return df

def load_all_datasets(data_dir: str = "data") -> pd.DataFrame:
    """
    Scans the data directory, loads all CSV files, normalizes their schemas, and merges them.
    """
    logger.info(f"Scanning directory for datasets: {data_dir}")
    
    if not os.path.exists(data_dir):
        logger.error(f"Data directory not found at {data_dir}")
        return pd.DataFrame()
        
    all_dfs = []
    
    for filename in os.listdir(data_dir):
        if filename.endswith(".csv"):
            filepath = os.path.join(data_dir, filename)
            logger.info(f"Loading dataset from {filepath}")
            try:
                # TMDB CSVs often have embedded newlines
                df = pd.read_csv(filepath, lineterminator='\n', engine='c')
            except pd.errors.ParserError:
                # Fallback to python engine
                df = pd.read_csv(filepath, engine='python', on_bad_lines='skip')
            except Exception as e:
                logger.error(f"Failed to load {filepath}: {e}")
                continue
                
            df = normalize_columns(df)
            all_dfs.append(df)
            
    if not all_dfs:
        logger.warning("No valid CSV datasets found.")
        return pd.DataFrame()
        
    # Merge all datasets
    final_df = pd.concat(all_dfs, ignore_index=True)
    
    # Drop duplicates by Title (keep the last one uploaded/merged)
    if "Title" in final_df.columns:
        final_df = final_df.drop_duplicates(subset=["Title"], keep="last")
        
    # Clean up null overviews so the NLP TF-IDF engine doesn't crash
    if "Overview" not in final_df.columns:
        final_df["Overview"] = "No overview available."
    final_df['Overview'] = final_df['Overview'].fillna("No overview available.")
    
    # Clean up null titles
    final_df['Title'] = final_df['Title'].fillna("Unknown Title")
    
    # Parse Genre strings into Python lists
    if 'Genre' in final_df.columns:
        final_df['Genre_List'] = final_df['Genre'].apply(parse_genres)
        
    # Apply poster fallback for missing posters
    if 'Poster_Url' in final_df.columns:
        final_df['Poster_Url'] = final_df['Poster_Url'].fillna(DEFAULT_POSTER_URL)
    else:
        final_df['Poster_Url'] = DEFAULT_POSTER_URL
        
    # Ensure standard numeric columns exist to avoid UI crashes
    if "Popularity" not in final_df.columns:
        final_df["Popularity"] = 0.0
    final_df["Popularity"] = pd.to_numeric(final_df["Popularity"], errors='coerce').fillna(0.0)
    
    if "Vote_Average" not in final_df.columns:
        final_df["Vote_Average"] = 0.0
    final_df["Vote_Average"] = pd.to_numeric(final_df["Vote_Average"], errors='coerce').fillna(0.0)
        
    return final_df

if __name__ == "__main__":
    # Test execution
    df = load_all_datasets("data")
    print(f"Loaded {len(df)} movies successfully.")
    print("Sample Genre Array:", df['Genre_List'].iloc[0])
