import pandas as pd
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_tv_shows(input_dir: str, output_path: str):
    """
    Reads normalized TV Show CSVs from input_dir and flattens them into a single CSV.
    Based on the ER Diagram provided.
    """
    logger.info(f"Starting ETL process from directory: {input_dir}")
    
    # Check if necessary files exist
    required_files = ["shows.csv", "genres.csv", "genre_types.csv", "show_votes.csv", "air_dates.csv"]
    for f in required_files:
        if not os.path.exists(os.path.join(input_dir, f)):
            logger.error(f"Missing required file: {f}")
            return
            
    # 1. Load the main shows table
    logger.info("Loading shows.csv...")
    shows_df = pd.read_csv(os.path.join(input_dir, "shows.csv"))
    
    # 2. Join Genres
    logger.info("Merging Genres...")
    genres_df = pd.read_csv(os.path.join(input_dir, "genres.csv"))
    genre_types_df = pd.read_csv(os.path.join(input_dir, "genre_types.csv"))
    
    # Merge genres with their names
    genres_merged = genres_df.merge(genre_types_df, on="genre_type_id", how="left")
    
    # Group by show_id and create a comma-separated string of genres
    genres_grouped = genres_merged.groupby("show_id")["genre_name"].apply(lambda x: ", ".join(x.dropna())).reset_index()
    genres_grouped.rename(columns={"genre_name": "Genre"}, inplace=True)
    
    # 3. Join Votes
    logger.info("Merging Votes...")
    votes_df = pd.read_csv(os.path.join(input_dir, "show_votes.csv"))
    # We assume 'show_id' is the join key
    
    # 4. Join Air Dates
    logger.info("Merging Air Dates...")
    air_dates_df = pd.read_csv(os.path.join(input_dir, "air_dates.csv"))
    # Filter for the first air date (is_first == 1 or True)
    # Depending on CSV format, it might be 1, True, "1", etc.
    first_air_dates = air_dates_df[air_dates_df["is_first"] == 1].copy()
    if first_air_dates.empty:
        # Fallback if boolean format is different
        first_air_dates = air_dates_df[air_dates_df["is_first"].astype(str) == "True"].copy()
    
    first_air_dates.rename(columns={"date": "Release Year"}, inplace=True)
    first_air_dates = first_air_dates[["show_id", "Release Year"]].drop_duplicates(subset=["show_id"])

    # 5. Bring it all together!
    logger.info("Flattening into master table...")
    master_df = shows_df.merge(genres_grouped, on="show_id", how="left")
    master_df = master_df.merge(votes_df, on="show_id", how="left")
    master_df = master_df.merge(first_air_dates, on="show_id", how="left")
    
    # Add optional Networks if they exist
    if os.path.exists(os.path.join(input_dir, "networks.csv")) and os.path.exists(os.path.join(input_dir, "network_types.csv")):
        logger.info("Merging Networks...")
        networks_df = pd.read_csv(os.path.join(input_dir, "networks.csv"))
        network_types_df = pd.read_csv(os.path.join(input_dir, "network_types.csv"))
        networks_merged = networks_df.merge(network_types_df, on="network_type_id", how="left")
        networks_grouped = networks_merged.groupby("show_id")["network_name"].apply(lambda x: ", ".join(x.dropna())).reset_index()
        networks_grouped.rename(columns={"network_name": "Network"}, inplace=True)
        master_df = master_df.merge(networks_grouped, on="show_id", how="left")
    
    # 6. Final Formatting mapping to our system's expected schema
    # Rename 'name' to 'Title', etc.
    column_mapping = {
        "name": "Title",
        "overview": "Overview",
        "popularity": "Popularity",
        "vote_average": "IMDb Rating",
        "number_of_seasons": "Seasons",
        "number_of_episodes": "Episodes"
    }
    master_df.rename(columns=column_mapping, inplace=True)
    
    # Ensure poster URL doesn't exist, so the backend system uses the default placeholder
    if "Poster URL" not in master_df.columns:
        master_df["Poster URL"] = None

    # Keep only the columns we actually want to feed into the recommendation engine
    desired_columns = ["Title", "Overview", "Popularity", "IMDb Rating", "Release Year", "Genre", "Seasons", "Episodes", "Network"]
    final_cols = [col for col in desired_columns if col in master_df.columns]
    master_df = master_df[final_cols]
    
    # Save to disk
    logger.info(f"Saving flattened dataset to {output_path}...")
    master_df.to_csv(output_path, index=False)
    logger.info(f"Success! Exported {len(master_df)} TV Series.")

if __name__ == "__main__":
    INPUT_FOLDER = "data"
    OUTPUT_FILE = "data/tv_series_master.csv"
    
    # Check if shows.csv exists in the data folder to avoid crashing if it's not there
    if os.path.exists(os.path.join(INPUT_FOLDER, "shows.csv")):
        process_tv_shows(INPUT_FOLDER, OUTPUT_FILE)
    else:
        print(f"shows.csv not found in {INPUT_FOLDER}. Please ensure the Kaggle dataset is present.")
