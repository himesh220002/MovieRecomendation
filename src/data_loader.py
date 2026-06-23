import pandas as pd
import requests
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

OMDB_API_KEY = os.environ.get("OMDB_API_KEY", None)
DEFAULT_POSTER_URL = "https://via.placeholder.com/500x750?text=No+Poster+Available"

import urllib.parse

def is_valid_poster(url: str, timeout: float = 2.0) -> bool:
    if not url or pd.isna(url) or url == "N/A" or url == DEFAULT_POSTER_URL or str(url) == "0":
        return False
    if str(url).startswith('data:'):
        return True
    try:
        r = requests.get(url, stream=True, timeout=timeout)
        return r.status_code < 400
    except Exception:
        return False

def fetch_poster_fallback(title: str, media_type: str = "Movie", year: str = None) -> str:
    """
    Fetches a movie or TV poster dynamically using a cascading fallback:
    1. Try TVMaze (Fastest, Free)
    2. Try OMDB API (Requires API Key)
    3. Return DEFAULT_POSTER_URL (which triggers the UI's dummy poster logic)
    """
    
    # Priority 1: TVMaze
    try:
        search_url = f"https://api.tvmaze.com/search/shows?q={urllib.parse.quote(title)}"
        response = requests.get(search_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0 and 'show' in data[0] and 'image' in data[0]['show'] and data[0]['show']['image']:
                poster = data[0]['show']['image'].get('original')
                if poster and is_valid_poster(poster, timeout=1.5):
                    return poster
    except Exception as e:
        logger.debug(f"TVMaze fallback missed for '{title}': {e}")

    # Priority 2: OMDB
    if OMDB_API_KEY:
        try:
            # We omit &type=movie if it's explicitly a TV Series to help OMDB find it
            type_param = "&type=movie" if media_type == "Movie" else ""
            search_url = f"http://www.omdbapi.com/?t={urllib.parse.quote(title)}{type_param}&apikey={OMDB_API_KEY}"
            if year:
                search_url += f"&y={year}"
                
            response = requests.get(search_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("Response") == "True" and data.get("Poster") and data.get("Poster") != "N/A":
                    poster = data.get("Poster")
                    if is_valid_poster(poster, timeout=1.5):
                        return poster
        except Exception as e:
            logger.debug(f"OMDB fallback missed for '{title}': {e}")

    # Priority 3: Fallback 
    # (Returning DEFAULT_POSTER_URL tells the UI to keep the random character poster)
    return DEFAULT_POSTER_URL

import re

LANGUAGE_MAP = {
    "en": "English", "eng": "English", "english": "English",
    "fr": "French", "fre": "French", "fra": "French", "french": "French",
    "es": "Spanish", "spa": "Spanish", "spanish": "Spanish",
    "ja": "Japanese", "jpn": "Japanese", "japanese": "Japanese",
    "hi": "Hindi", "hin": "Hindi", "hindi": "Hindi",
    "ko": "Korean", "kor": "Korean", "korean": "Korean",
    "zh": "Chinese", "zho": "Chinese", "chi": "Chinese", "chinese": "Chinese",
    "de": "German", "deu": "German", "ger": "German", "german": "German",
    "ru": "Russian", "rus": "Russian", "russian": "Russian",
    "it": "Italian", "ita": "Italian", "italian": "Italian",
    "pt": "Portuguese", "por": "Portuguese", "portuguese": "Portuguese",
    "ar": "Arabic", "ara": "Arabic", "arabic": "Arabic",
    "te": "Telugu", "tel": "Telugu", "telugu": "Telugu",
    "ta": "Tamil", "tam": "Tamil", "tamil": "Tamil",
    "ml": "Malayalam", "mal": "Malayalam", "malayalam": "Malayalam",
    "bn": "Bengali", "ben": "Bengali", "bengali": "Bengali"
}

def normalize_languages(lang_list):
    """
    Accepts a list of language strings or a single string (comma-separated).
    Normalizes short codes to full names and deduplicates.
    """
    if not lang_list:
        return []
    
    if isinstance(lang_list, str):
        raw_langs = re.split(r'[,/]', lang_list)
    else:
        raw_langs = []
        for item in lang_list:
            if isinstance(item, str):
                raw_langs.extend(re.split(r'[,/]', item))
                
    normalized = set()
    for lang in raw_langs:
        lang = lang.strip().lower()
        if not lang or lang == "n/a" or lang == "none":
            continue
            
        full_name = LANGUAGE_MAP.get(lang)
        if full_name:
            normalized.add(full_name)
        else:
            normalized.add(lang.title())
            
    return sorted(list(normalized))

def fetch_extended_metadata(title: str, media_type: str = "Movie", year: str = None) -> dict:
    """
    Fetches extended metadata (languages) from APIs.
    We try both TVMaze and OMDB to aggregate languages.
    """
    metadata = {
        "languages": []
    }
    
    # TVMaze
    try:
        search_url = f"https://api.tvmaze.com/search/shows?q={urllib.parse.quote(title)}"
        response = requests.get(search_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0 and 'show' in data[0]:
                show_data = data[0]['show']
                if 'language' in show_data and show_data['language']:
                    metadata["languages"].append(show_data['language'])
    except Exception as e:
        logger.debug(f"TVMaze extended fetch failed for '{title}': {e}")

    # OMDB
    if OMDB_API_KEY:
        try:
            type_param = "&type=movie" if media_type == "Movie" else ""
            search_url = f"http://www.omdbapi.com/?t={urllib.parse.quote(title)}{type_param}&apikey={OMDB_API_KEY}"
            if year:
                search_url += f"&y={year}"
                
            response = requests.get(search_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("Response") == "True":
                    if data.get("Language") and data.get("Language") != "N/A":
                        metadata["languages"].append(data.get("Language"))
        except Exception as e:
            logger.debug(f"OMDB extended fetch failed for '{title}': {e}")

    return metadata

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
