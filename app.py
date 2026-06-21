import streamlit as st
import pandas as pd
from src.data_loader import load_movie_dataset
from src.recommender import RecommenderSystem
from src.user_state import UserState
import urllib.parse
from youtubesearchpython import VideosSearch

# Cache Trailer Searches
@st.cache_data
def get_trailer_id(movie_title):
    try:
        videosSearch = VideosSearch(f"{movie_title} official movie trailer", limit=1)
        res = videosSearch.result()
        if res and 'result' in res and len(res['result']) > 0:
            return res['result'][0]['id']
    except:
        pass
    return "EngW7tLk6R8" # Fallback

# Page Config
st.set_page_config(page_title="Netflix Clone: AI Recommender", layout="wide", page_icon="🍿")

# Load Backend (Cached)
@st.cache_data
def load_data():
    # Use relative path inside the project directory so Streamlit Cloud can find it!
    return load_movie_dataset("data/mymoviedb.csv")

@st.cache_resource
def load_recommender(_df):
    return RecommenderSystem(_df)

df = load_data()
recommender = load_recommender(df)
user_state = UserState()

# Custom CSS for UI
st.markdown("""
<style>
    .movie-card {
        background-color: #1e293b;
        padding: 10px;
        border-radius: 10px;
        transition: transform 0.2s;
        cursor: pointer;
        height: 550px;
        margin-bottom: 25px;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
    }
    .movie-card:hover {
        transform: scale(1.05);
    }
</style>
""", unsafe_allow_html=True)

# Dialog for Movie Details
@st.dialog("🎬 Movie Details", width="large")
def movie_details_dialog(movie_row):
    title = movie_row['Title']
    poster = movie_row['Poster_Url']
    overview = movie_row['Overview']
    release_date = movie_row.get('Release_Date', 'Unknown')
    vote_avg = movie_row.get('Vote_Average', 'N/A')
    genres = ", ".join(movie_row.get('Genre_List', []))

    st.subheader(title)
    st.write(f"**Release Date:** {release_date} &nbsp;|&nbsp; **Rating:** {vote_avg}/10 ⭐ &nbsp;|&nbsp; **Genres:** {genres}")
    st.divider()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(poster, use_container_width=True)
    with col2:
        st.write(f"**Overview:** {overview}")
        
        st.write("### Your Library Actions")
        current_status = "None"
        for cat in ["watched", "my_list", "currently_watching"]:
            if title in user_state.state[cat]:
                current_status = cat

        # Custom Buttons instead of Selectbox
        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if current_status == "None":
                if st.button("➕ Add", key=f"add_{title}"):
                    user_state.mark_as(title, "my_list")
                    st.rerun()
            elif current_status == "currently_watching":
                if st.button("▶️ Continue Watching", key=f"watch_{title}"):
                    pass
            elif current_status == "my_list":
                st.button("✅ Added to list", disabled=True, key=f"added_{title}")
            elif current_status == "watched":
                st.button("✅ Watched", disabled=True, key=f"watched_{title}")
                
        with action_col2:
            if current_status not in ["None", "watched"]:
                if st.button("✔️ Mark as Watched", key=f"mark_watched_{title}"):
                    user_state.mark_as(title, "watched")
                    st.rerun()
            if current_status == "my_list":
                if st.button("▶️ Start Watching", key=f"start_watching_{title}"):
                    user_state.mark_as(title, "currently_watching")
                    st.rerun()

        st.divider()
        current_rating = user_state.get_rating(title)
        rating_status = "⭐ Rated" if current_rating else "📝 Rate this"
        st.write(f"### {rating_status}")
        
        new_rating = st.slider("Rate this movie (1-10)", 1, 10, int(current_rating or 5), key=f"rate_{title}")
        if st.button("Save Rating"):
            user_state.rate_movie(title, new_rating)
            st.rerun()

    st.divider()
    st.write("### 🎥 Watch Trailer")
    
    video_id = get_trailer_id(title)
    
    st.markdown(
        f'''
        <div style="display: flex; justify-content: center;">
            <iframe width="700" height="500" 
            src="https://www.youtube.com/embed/{video_id}?autoplay=1&mute=1&controls=1" 
            title="YouTube video player" frameborder="0" 
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" 
            allowfullscreen></iframe>
        </div>
        ''', unsafe_allow_html=True
    )

# UI Function to render a row of movies
def render_movie_grid(movies_df, key_prefix="", num_cols=5):
    if len(movies_df) == 0:
        st.write("No movies found.")
        return

    cols = st.columns(num_cols)
    for i, (_, row) in enumerate(movies_df.head(15).iterrows()):
        with cols[i % num_cols]:
            release = row.get('Release_Date', 'Unknown')
            rating = row.get('Vote_Average', 'N/A')
            genres_arr = row.get('Genre_List', [])
            genres = ", ".join(genres_arr[:2]) if genres_arr else "Unknown"
            
            movie_title_encoded = urllib.parse.quote(row['Title'])
            
            card_html = f"""
            <a href="?movie={movie_title_encoded}" target="_self" style="text-decoration: none; color: inherit; display: block;" class="movie-card">
                <img src="{row['Poster_Url']}" style="width: 100%; height: 425px; object-fit: cover; border-radius: 8px;">
                <div style='font-size: 1.1rem; color: #94a3b8; text-align: center; margin-top: 10px;'>
                    {release} | {rating}⭐ | {genres}
                </div>
                <h4 style='text-align: center; margin-top: 0.5rem; color: white; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical;'>{row['Title']}</h4>
            </a>
            """
            st.markdown(card_html, unsafe_allow_html=True)

# Main App Layout
st.title("🍿 AI Movie Recommendations")

# Check for query params to open dialog
if "movie" in st.query_params:
    selected_movie_title = st.query_params["movie"]
    st.query_params.clear() # Clear it so it doesn't reopen on refresh
    try:
        movie_row = df[df['Title'] == selected_movie_title].iloc[0]
        movie_details_dialog(movie_row)
    except IndexError:
        pass

tab1, tab2, tab3 = st.tabs(["📺 Discover", "🔍 Search & Filter", "📚 My Library"])

with tab1:
    st.header("Trending Now")
    trending = df.sort_values(by="Popularity", ascending=False).head(10)
    render_movie_grid(trending, key_prefix="trending")

    # Add Genre Rows
    genres_to_display = [
        ("Action", "Action"),
        ("Comedy", "Comedy"),
        ("Drama", "Drama"),
        ("Horror", "Horror"),
        ("Sci-Fi", "Science Fiction"),
        ("Fantasy", "Fantasy"),
        ("Romance", "Romance"),
        ("Thriller", "Thriller"),
        ("Mystery", "Mystery"),
        ("Western", "Western"),
        ("Animation", "Animation"),
        ("Musical", "Music")
    ]
    
    for display_name, actual_genre in genres_to_display:
        st.divider()
        st.header(display_name)
        # Filter by genre and sort by popularity
        genre_df = df[df['Genre'].fillna('').str.contains(actual_genre, case=False, regex=False)]
        genre_top = genre_df.sort_values(by="Popularity", ascending=False).head(10)
        render_movie_grid(genre_top, key_prefix=f"genre_{actual_genre}")
    
    # Show personalized recommendations if user has watched anything
    watched = user_state.state["watched"]
    if len(watched) > 0:
        last_watched = watched[-1]
        st.divider()
        st.header(f"Because you watched **{last_watched}**...")
        recs = recommender.get_recommendations(last_watched, top_n=10)
        if len(recs) > 0:
            render_movie_grid(recs, key_prefix="recs")

with tab2:
    st.header("Search the Database")
    search_query = st.text_input("Search by Title...")
    if search_query:
        results = df[df['Title'].str.contains(search_query, case=False, na=False)]
        render_movie_grid(results, key_prefix="search")
    else:
        st.write("Enter a movie title to search.")

with tab3:
    st.header("Your Library")
    
    st.subheader("Currently Watching")
    watching_df = df[df['Title'].isin(user_state.state["currently_watching"])]
    render_movie_grid(watching_df, key_prefix="watching")
    
    st.subheader("My List")
    mylist_df = df[df['Title'].isin(user_state.state["my_list"])]
    render_movie_grid(mylist_df, key_prefix="mylist")
    
    st.subheader("Watched")
    watched_df = df[df['Title'].isin(user_state.state["watched"])]
    render_movie_grid(watched_df, key_prefix="watched")
