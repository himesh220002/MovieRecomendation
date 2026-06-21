import json
import os
import logging

logger = logging.getLogger(__name__)

class UserState:
    def __init__(self, filepath: str = "data/user_state.json"):
        self.filepath = filepath
        self._ensure_file_exists()
        self.state = self.load_state()

    def _ensure_file_exists(self):
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if not os.path.exists(self.filepath):
            default_state = {
                "watched": [],
                "my_list": [],
                "currently_watching": [],
                "ratings": {}
            }
            with open(self.filepath, "w") as f:
                json.dump(default_state, f, indent=4)
            logger.info(f"Created new user state file at {self.filepath}")

    def load_state(self) -> dict:
        try:
            with open(self.filepath, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error("JSON Decode Error: user_state.json is malformed.")
            return {"watched": [], "my_list": [], "currently_watching": [], "ratings": {}}

    def save_state(self):
        with open(self.filepath, "w") as f:
            json.dump(self.state, f, indent=4)

    def mark_as(self, title: str, category: str):
        """
        Marks a movie into one of the valid categories: 'watched', 'my_list', 'currently_watching'
        Removes the movie from other lists to maintain exclusive state.
        """
        valid_categories = ["watched", "my_list", "currently_watching"]
        if category not in valid_categories:
            raise ValueError(f"Invalid category. Must be one of {valid_categories}")

        # Remove from all categories first
        for cat in valid_categories:
            if title in self.state[cat]:
                self.state[cat].remove(title)

        # Add to target category
        self.state[category].append(title)
        self.save_state()
        logger.info(f"Marked '{title}' as {category}")

    def remove_from_lists(self, title: str):
        """Removes a movie from all watchlists."""
        valid_categories = ["watched", "my_list", "currently_watching"]
        for cat in valid_categories:
            if title in self.state[cat]:
                self.state[cat].remove(title)
        self.save_state()

    def rate_movie(self, title: str, rating: int):
        """
        Saves a 1-10 rating for a movie.
        """
        if not (1 <= rating <= 10):
            raise ValueError("Rating must be between 1 and 10.")
            
        self.state["ratings"][title] = rating
        self.save_state()
        logger.info(f"Rated '{title}' {rating}/10")

    def get_rating(self, title: str):
        return self.state["ratings"].get(title, None)

if __name__ == "__main__":
    state = UserState()
    state.mark_as("Spider-Man", "watched")
    state.rate_movie("Spider-Man", 9)
    print(state.load_state())
