import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)

class RecommenderSystem:
    def __init__(self, df: pd.DataFrame):
        self.df = df.reset_index(drop=True)
        # We need a clean title to index mapping
        self.indices = pd.Series(self.df.index, index=self.df['Title'].str.lower()).to_dict()
        self.cosine_sim = None
        self._build_tfidf_matrix()

    def _build_tfidf_matrix(self):
        """
        Build the TF-IDF matrix based on the movie 'Overview' and 'Genre'.
        We combine both strings to give weight to genre overlap as well as plot similarity.
        """
        logger.info("Building TF-IDF Matrix...")
        
        # Combine Overview and Genre for a richer text profile
        # First, ensure Genre_List exists and is converted to string
        if 'Genre_List' in self.df.columns:
            genres_str = self.df['Genre_List'].apply(lambda x: " ".join(x) if isinstance(x, list) else "")
        else:
            genres_str = ""

        # Create the combined feature
        # We repeat genres so they have a higher weight in the TF-IDF vector
        combined_features = self.df['Overview'].fillna('') + " " + genres_str + " " + genres_str
        
        # Initialize Vectorizer ignoring English stop words
        tfidf = TfidfVectorizer(stop_words='english')
        
        # Fit and transform the data
        tfidf_matrix = tfidf.fit_transform(combined_features)
        
        # Compute cosine similarity matrix
        logger.info("Computing Cosine Similarity Matrix...")
        self.cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
        logger.info("NLP Engine Ready.")

    def get_recommendations(self, title: str, top_n: int = 10) -> pd.DataFrame:
        """
        Returns the top_n most similar movies based on content.
        """
        title_lower = title.lower()
        if title_lower not in self.indices:
            logger.warning(f"Movie '{title}' not found in database.")
            return pd.DataFrame()
            
        # Get the index of the movie that matches the title
        idx = self.indices[title_lower]
        
        # If there are duplicate titles, take the first one
        if isinstance(idx, pd.Series):
            idx = idx.iloc[0]

        # Get the pairwsie similarity scores of all movies with that movie
        sim_scores = list(enumerate(self.cosine_sim[idx]))

        # Sort the movies based on the similarity scores
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

        # Get the scores of the 10 most similar movies (ignoring the first one which is itself)
        # We get top_n + 1 just in case, but we explicitly filter out the input title
        sim_scores = sim_scores[1:top_n+1]

        # Get the movie indices
        movie_indices = [i[0] for i in sim_scores]

        # Return the top N most similar movies
        return self.df.iloc[movie_indices].copy()

if __name__ == "__main__":
    # Test script
    from data_loader import load_movie_dataset
    df = load_movie_dataset("../datasets/mymoviedb (1).csv")
    recommender = RecommenderSystem(df)
    
    recs = recommender.get_recommendations("Spider-Man: No Way Home", top_n=5)
    print("\nRecommendations for Spider-Man: No Way Home:")
    print(recs[['Title', 'Genre']])
