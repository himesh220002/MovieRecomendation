import streamlit as st # pyrefly: ignore [missing-import]
import pandas as pd
from src.data_loader import load_all_datasets, fetch_poster_fallback, DEFAULT_POSTER_URL
from src.recommender import RecommenderSystem
from src.user_state import UserState
import urllib.parse
# pyrefly: ignore [missing-import]
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

@st.cache_data
def get_dynamic_poster_url(title, media_type, year):
    poster = fetch_poster_fallback(title, media_type=media_type, year=year)
    return poster

# Page Config
st.set_page_config(page_title="Netflix Clone: AI Recommender", layout="wide", page_icon="🍿")

# Load Backend (Cached)
@st.cache_data
def load_data():
    # Use relative path inside the project directory so Streamlit Cloud can find it!
    return load_all_datasets("data")

@st.cache_resource
def load_recommender(_df):
    return RecommenderSystem(_df)

df = load_data()
recommender = load_recommender(df)
user_state = UserState()

# Custom CSS for UI
st.markdown("""
<style>
    /* The visual card */
    .movie-card {
        background-color: #1e293b;
        padding: 10px;
        border-radius: 10px;
        transition: transform 0.2s, box-shadow 0.2s;
        height: 520px;
        margin-bottom: 10px;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
    }
    
    /* Target the Streamlit column that contains the movie card */
    div[data-testid="column"]:has(.movie-card) {
        position: relative;
    }
    
    /* Make the entire Streamlit button wrapper element absolute so it overlays the card */
    div[data-testid="column"]:has(.movie-card) > div:last-child {
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 100% !important;
        opacity: 0.001 !important;
        z-index: 9999 !important;
    }
    
    /* Ensure the button fills the wrapper */
    div[data-testid="column"]:has(.movie-card) .stButton,
    div[data-testid="column"]:has(.movie-card) .stButton button {
        width: 100% !important;
        height: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        cursor: pointer !important;
    }
    
    /* Trigger the scale effect on the card when hovering the column (which includes the invisible button) */
    div[data-testid="column"]:has(.movie-card):hover .movie-card {
        transform: scale(1.05);
        box-shadow: 0 10px 20px rgba(0,0,0,0.5);
    }
</style>
""", unsafe_allow_html=True)

# Dialog for Movie Details
@st.dialog("🎬 Movie Details", width="large")
def movie_details_dialog(movie_row):
    if "pending_toast" in st.session_state:
        st.toast(st.session_state.pop("pending_toast"))
        
    title = movie_row['Title']
    poster = movie_row['Poster_Url']
    poster_url = movie_row['Poster_Url']
    overview = movie_row['Overview']
    release_date_raw = movie_row.get('Release_Date', 'Unknown')
    release_year = str(release_date_raw)[:4] if pd.notna(release_date_raw) and release_date_raw != 'Unknown' else 'Unknown'
    vote_avg_raw = movie_row.get('Vote_Average', 'N/A')
    try:
        vote_avg = f"{float(vote_avg_raw):.1f}"
    except (ValueError, TypeError):
        vote_avg = str(vote_avg_raw)
    genres = ", ".join(movie_row.get('Genre_List', []))
    media_type = movie_row.get('Media_Type', 'Movie')

    # Dynamically fetch poster if it's missing, broken ("0"), or the fallback
    if str(poster_url) == "0" or poster_url == DEFAULT_POSTER_URL or pd.isna(poster_url):
        year_str = release_year if release_year != 'Unknown' else None
        poster_url = get_dynamic_poster_url(title, media_type, year_str)

    current_status = "None"
    for cat in ["watched", "my_list", "currently_watching"]:
        if title in user_state.state[cat]:
            current_status = cat
    
    def update_status(new_status, msg):
        user_state.mark_as(title, new_status)
        st.session_state["pending_toast"] = msg
        st.rerun()

    def update_rating(key):
        val = st.session_state[key]
        user_state.rate_movie(title, val)
        st.session_state["pending_toast"] = "⭐ Rating saved successfully!"
        st.rerun()
        
    def remove_movie(msg):
        user_state.remove_from_lists(title)
        st.session_state["pending_toast"] = msg
        st.rerun()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(poster_url, use_container_width=True)
    with col2:
        st.header(title)
        
        if media_type == "TV Series":
            st.write(f"**📺 TV Series** | **Rating:** {vote_avg}/10 ⭐")
            st.write(f"**Genres:** {genres}")
            st.write(f"**Year:** {release_year}")
            
            seasons = movie_row.get("Seasons")
            episodes = movie_row.get("Episodes")
            network = movie_row.get("Network")
            
            tv_details = []
            if pd.notna(seasons) and seasons != 0:
                tv_details.append(f"**Seasons:** {int(float(seasons))}")
            if pd.notna(episodes) and episodes != 0:
                tv_details.append(f"**Episodes:** {int(float(episodes))}")
            if pd.notna(network) and str(network).strip() and str(network) != 'nan':
                tv_details.append(f"**Network:** {network}")
                
            if tv_details:
                st.write(" | ".join(tv_details))
        else:
            st.write(f"**🎬 Movie** | **Rating:** {vote_avg}/10 ⭐")
            st.write(f"**Genres:** {genres}")
            st.write(f"**Year:** {release_year}")
            
        st.divider()
        st.write(f"**Overview:** {overview}")
        
        st.write("### Your Library Actions")
        
        # Custom Buttons instead of Selectbox
        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if current_status == "None":
                if st.button("➕ Add to My List", key=f"add_{title}"):
                    update_status("my_list", "✅ Added to your list!")
            elif current_status == "currently_watching":
                st.button("▶️ Continue Watching", disabled=True, key=f"watch_{title}")
            elif current_status == "my_list":
                st.button("✅ In My List", disabled=True, key=f"added_{title}")
            elif current_status == "watched":
                st.button("✅ Watched", disabled=True, key=f"watched_{title}")
                
        with action_col2:
            if current_status == "None":
                if st.button("✔️ Mark as Watched", key=f"mark_watched_{title}"):
                    update_status("watched", "✅ Marked as watched!")
            elif current_status == "my_list":
                if st.button("▶️ Start Watching", key=f"start_watching_{title}"):
                    update_status("currently_watching", "🍿 Started watching!")
                if st.button("✔️ Mark as Watched", key=f"mark_watched_btn_{title}"):
                    update_status("watched", "✅ Marked as watched!")
            elif current_status == "currently_watching":
                if st.button("✔️ Finish Watching", key=f"finish_watched_{title}"):
                    update_status("watched", "✅ Marked as watched!")
                
        if current_status != "None":
            if st.button("❌ Remove from Library", key=f"remove_{title}"):
                remove_movie("🗑️ Removed from library!")

        current_rating = user_state.get_rating(title)
        rating_status = "⭐ Rated" if current_rating else "📝 Rate this"
        st.write(f"### {rating_status}")
        
        rating_key = f"rate_{title}"
        st.slider("Rate this movie (1-10)", 1, 10, int(current_rating or 5), key=rating_key)
        if st.button("Save Rating", key=f"save_rate_{title}"):
            update_rating(rating_key)

    st.divider()
    st.write("### 🎥 Watch Trailer")
    
    video_id = get_trailer_id(title)
    st.video(f"https://www.youtube.com/watch?v={video_id}", autoplay=True, muted=True)

# UI Function to render a row of movies
def render_movie_grid(movies_df, key_prefix="", num_cols=5):
    if len(movies_df) == 0:
        st.write("No movies found.")
        return

    cols = st.columns(num_cols, gap="small")
    for i, (_, row) in enumerate(movies_df.head(15).iterrows()):
        with cols[i % num_cols]:
            release_raw = row.get('Release_Date', 'Unknown')
            release_year = str(release_raw)[:4] if pd.notna(release_raw) and release_raw != 'Unknown' else 'Unknown'
            rating_raw = row.get('Vote_Average', 'N/A')
            try:
                rating = f"{float(rating_raw):.1f}"
            except (ValueError, TypeError):
                rating = str(rating_raw)
            genres_arr = row.get('Genre_List', [])
            genres = ", ".join(genres_arr[:2]) if genres_arr else "Unknown"
            
            movie_title_encoded = urllib.parse.quote(row['Title'])
            
            poster_url = row.get('Poster_Url')
            media_type = row.get('Media_Type', 'Movie')
            if str(poster_url) == "0" or poster_url == DEFAULT_POSTER_URL or pd.isna(poster_url):
                year_str = release_year if release_year != 'Unknown' else None
                poster_url = get_dynamic_poster_url(row['Title'], media_type, year_str)
            
            card_html = f"""
            <div style="display: block;" class="movie-card">
                <img src="{poster_url}" style="width: 100%; height: 425px; object-fit: cover; border-radius: 8px;">
                <div style='font-size: 0.9rem; color: #94a3b8; text-align: center; margin-top: 10px;'>
                    {release_year} | {rating}⭐ | {genres}
                </div>
                <p style='text-align: center; text-size: 1rem; margin-top: 0.5rem; color: white; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical;'>{row['Title']}</p>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            if st.button("View Details", key=f"btn_{key_prefix}_{i}_{movie_title_encoded}", type="primary"):
                movie_details_dialog(row)

# Main App Layout
st.title("🍿 AI Movie Recommendations")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎬 Movies", "📺 TV Shows", "🔍 Search & Filter", "📚 My Library", "⚙️ Settings & Data"])

# Helper function for headers with refresh buttons
def render_header_with_refresh(title, key):
    col1, col2 = st.columns([10, 1])
    with col1:
        st.header(title)
    with col2:
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        if st.button("🔄", key=f"refresh_{key}", help="Show different movies"):
            st.session_state[f"seed_{key}"] = st.session_state.get(f"seed_{key}", 0) + 1
    return st.session_state.get(f"seed_{key}", 0)

def get_valid_movies(pool_df, num_needed, seed):
    shuffled_pool = pool_df.sample(frac=1, random_state=seed) if len(pool_df) > 0 else pool_df
    valid_rows = []
    for _, row in shuffled_pool.iterrows():
        poster_url = row.get('Poster_Url')
        media_type = row.get('Media_Type', 'Movie')
        release_raw = row.get('Release_Date', 'Unknown')
        release_year = str(release_raw)[:4] if pd.notna(release_raw) and release_raw != 'Unknown' else 'Unknown'
        
        if str(poster_url) == "0" or poster_url == DEFAULT_POSTER_URL or pd.isna(poster_url):
            year_str = release_year if release_year != 'Unknown' else None
            poster_url = get_dynamic_poster_url(row['Title'], media_type, year_str)
            
        if poster_url != DEFAULT_POSTER_URL:
            row_dict = row.to_dict()
            row_dict['Poster_Url'] = poster_url
            valid_rows.append(row_dict)
            
        if len(valid_rows) >= num_needed:
            break
            
    return pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=pool_df.columns)

def render_discover_page(discover_df, prefix):
    seed = render_header_with_refresh("Trending Now", f"{prefix}_trending")
    trending_pool = discover_df.sort_values(by="Popularity", ascending=False).head(60)
    trending = get_valid_movies(trending_pool, 10, seed)
    render_movie_grid(trending, key_prefix=f"{prefix}_trending")

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
        genre_df = discover_df[discover_df['Genre'].fillna('').str.contains(actual_genre, case=False, regex=False)]
        if len(genre_df) == 0:
            continue
            
        st.divider()
        seed = render_header_with_refresh(display_name, f"{prefix}_{actual_genre}")
        
        genre_pool = genre_df.sort_values(by="Popularity", ascending=False).head(60)
        genre_top = get_valid_movies(genre_pool, 10, seed)
        
        render_movie_grid(genre_top, key_prefix=f"{prefix}_genre_{actual_genre}")
    
    # Show personalized recommendations if user has watched anything
    watched = user_state.state["watched"]
    if len(watched) > 0:
        last_watched = watched[-1]
        st.divider()
        st.header(f"Because you watched **{last_watched}**...")
        recs = recommender.get_recommendations(last_watched, top_n=10)
        if len(recs) > 0:
            # Filter recommendations to match the current media type tab
            media_type = "Movie" if prefix == "movies" else "TV Series"
            filtered_recs = recs[recs['Media_Type'] == media_type] if 'Media_Type' in recs.columns else recs
            if len(filtered_recs) > 0:
                render_movie_grid(filtered_recs, key_prefix=f"{prefix}_recs")

with tab1:
    movies_df = df[df.get("Media_Type", "Movie") == "Movie"]
    render_discover_page(movies_df, "movies")

with tab2:
    tv_df = df[df.get("Media_Type", "Movie") == "TV Series"]
    if len(tv_df) == 0:
        st.warning("No TV Shows available. Please upload a dataset in the Settings tab!")
    else:
        render_discover_page(tv_df, "tv")

with tab3:
    st.header("Search the Database")
    search_query = st.text_input("Search by Title...")
    if search_query:
        results = df[df['Title'].str.contains(search_query, case=False, na=False)]
        results = results.sort_values(by="Popularity", ascending=False)
        render_movie_grid(results, key_prefix="search")
    else:
        st.write("Enter a title to search.")

with tab4:
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

with tab5:
    st.header("⚙️ Settings & Data Management")
    st.write("Upload additional datasets (like new movies from 2022+ or TV Series) to seamlessly expand your recommendation engine. The system will automatically map the columns, handle duplicates, and merge them!")
    
    uploaded_file = st.file_uploader("Upload Supplementary CSV", type=["csv"])
    if uploaded_file is not None:
        if st.button("Merge & Update Database"):
            import os
            # Save the file to the data directory
            save_path = os.path.join("data", uploaded_file.name)
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"Successfully saved {uploaded_file.name}!")
            
            # Clear caches to rebuild the database and recommender engine
            st.cache_data.clear()
            st.cache_resource.clear()
            st.toast("🔄 Rebuilding database and AI engine...")
            st.rerun()
