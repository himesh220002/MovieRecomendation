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
        self.tfidf_matrix = None
        self._build_tfidf_matrix()

    def _build_tfidf_matrix(self):
        """
        Build the TF-IDF matrix based on the movie 'Overview' and 'Genre'.
        We combine both strings to give weight to genre overlap as well as plot similarity.
        """
        logger.info("Building TF-IDF Matrix...")
        
        # Create a combined features column that includes both Overview and Genres
        # This is extremely important because some newly uploaded datasets (like TV Series)
        # might lack an Overview, so the NLP engine falls back to clustering them purely by Genre!
        combined_features = self.df['Overview'].fillna('') + " " + self.df['Genre'].fillna('')
        
        # Initialize Vectorizer ignoring English stop words
        tfidf = TfidfVectorizer(stop_words='english')
        
        # Fit and transform the data
        self.tfidf_matrix = tfidf.fit_transform(combined_features)
        
        logger.info("NLP Engine Ready.")

    def get_recommendations(self, title: str, top_n: int = 12) -> pd.DataFrame:
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

        # Compute cosine similarity ONLY for the requested movie vector against all others
        movie_vector = self.tfidf_matrix[idx]
        sim_scores_array = cosine_similarity(movie_vector, self.tfidf_matrix).flatten()

        # Get the pairwsie similarity scores of all movies with that movie
        sim_scores = list(enumerate(sim_scores_array))

        # Sort the movies based on the similarity scores
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

        # Get the scores of the 12 most similar movies (ignoring the first one which is itself)
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
