import streamlit as st
import requests

API = "http://127.0.0.1:8000"

# ------------------------ PAGE CONFIG ------------------------
st.set_page_config(
    page_title="Songs Inventory Management System",
    layout="wide"
)

# ------------------------ GLOBAL STYLES ------------------------
custom_css = """
<style>
[data-testid="stAppViewContainer"] {
    background-image: linear-gradient(
        rgba(0,0,0,0.82), 
        rgba(0,0,0,0.92)
    ),
    url("https://images.pexels.com/photos/164745/pexels-photo-164745.jpeg");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
    color: #f5f5f5;
    font-family: "Segoe UI", sans-serif;
}

.block-container {
    padding-top: 2rem;
}

[data-testid="stSidebar"] {
    background: rgba(5, 5, 5, 0.93);
}

h1, h2, h3, h4, h5 {
    color: #f5f5f5 !important;
}

.stButton > button {
    background: linear-gradient(135deg, #1db954, #1aa34a);
    color: #ffffff !important;
    font-weight: 600;
    border-radius: 999px;
    border: none;
    padding: 0.5rem 1.4rem;
    box-shadow: 0 0 12px rgba(0,0,0,0.5);
    transition: all 0.2s ease-in-out;
    cursor: pointer;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #25e067, #1db954);
    transform: translateY(-1px) scale(1.02);
}

.card {
    background: rgba(15,15,15,0.86);
    border-radius: 18px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 0 18px rgba(0,0,0,0.65);
    border: 1px solid rgba(255,255,255,0.06);
}

.song-meta {
    font-size: 0.85rem;
    color: #cccccc;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)


# ------------------------ HELPERS ------------------------

def safe_get(url, params=None):
    try:
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error("❌ Could not connect to backend.")
        st.caption(str(e))
        return []


def safe_post(url, json_data):
    try:
        r = requests.post(url, json=json_data, timeout=5)
        r.raise_for_status()
        if r.text:
            return r.json()
        return {}
    except Exception as e:
        st.error("❌ Could not connect to backend.")
        st.caption(str(e))
        return None


def render_song_list(songs, log_for_user=False, context="main"):
    """Display songs with serial numbers + working audio."""
    if not songs:
        st.info("No songs found.")
        return

    user_id = st.session_state.get("user_id")

    for idx, s in enumerate(songs, start=1):
        sid = s.get("id")
        title = s.get("title", "Unknown")
        artist = s.get("artist", "Unknown")
        genre = s.get("genre", "")

        serial = f"{idx}. 🎵 {title}"

        col1, col2 = st.columns([4, 1])

        with col1:
            st.markdown(f"### {serial}")
            st.markdown(
                f"<span class='song-meta'>{artist} • {genre}</span>",
                unsafe_allow_html=True
            )

        play_key = f"{context}_play_{sid}_{idx}"
        audio_key = f"{context}_audio_{sid}_{idx}"

        with col2:
            if st.button("▶ Play", key=play_key):
                if log_for_user and user_id:
                    safe_post(f"{API}/log_play/", {"user_id": user_id, "song_id": sid})
                st.session_state[audio_key] = True

        if st.session_state.get(audio_key, False):
            st.audio(f"{API}/audio/{sid}")

        st.write("---")



# ------------------------ ROLE SELECTION ------------------------

if "role" not in st.session_state:
    st.markdown(
        """
        <div class="card">
            <h1>Select Mode</h1>
            <p style="color:#cccccc;">Choose whether you are a user or a moderator.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    # USER LOGIN
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        username = st.text_input("Enter your name", key="login_username")
        if st.button("Continue as User"):
            if not username.strip():
                st.warning("Please enter a valid name.")
            else:
                res = safe_post(f"{API}/user/login/", {"username": username})
                if res:
                    st.session_state["role"] = "user"
                    st.session_state["user_id"] = res["user_id"]
                    st.session_state["username"] = res["username"]
                    st.experimental_rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # MODERATOR LOGIN
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        pwd = st.text_input("Moderator Password", type="password")
        if st.button("Login as Moderator"):
            if pwd == "0613":
                st.session_state["role"] = "moderator"
                st.session_state.pop("user_id", None)
                st.session_state.pop("username", None)
                st.experimental_rerun()
            else:
                st.error("Incorrect password.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()


role = st.session_state.get("role")
user_id = st.session_state.get("user_id")
username = st.session_state.get("username", "")

# ------------------------ SIDEBAR NAV ------------------------

st.sidebar.title("🎧 Navigation")
st.sidebar.markdown(f"**Role:** `{role}`")
if username:
    st.sidebar.markdown(f"**User:** `{username}`")

if st.sidebar.button("🔄 Switch Role"):
    for k in ["role", "user_id", "username"]:
        st.session_state.pop(k, None)
    st.experimental_rerun()

if role == "moderator":
    pages = [
        "Home",
        "View All Songs",
        "Mood-Based Songs",
        "Genre Explorer",
        "Request a Song",
        "Add Song (Moderator)",
        "Manage Requests",
        "Playlist Builder",
    ]
else:
    pages = [
        "Home",
        "View All Songs",
        "Mood-Based Songs",
        "Genre Explorer",
        "Request a Song",
        "My Analytics",
        "My Recommendations",   # updated contents only
        "Playlist Builder",
    ]

page = st.sidebar.radio("Go to", pages)


# ------------------------ HOME ------------------------

if page == "Home":
    st.markdown(
        """
        <div class="card">
            <h1>Welcome to Songs Inventory Management System</h1>
            <p style="color:#cccccc;">A dark-themed music inventory with moods, genres, playlists, AI song requests and analytics.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("📂 View All Songs"):
            st.session_state["jump"] = "View All Songs"
    with c2:
        if st.button("🎼 Browse by Mood"):
            st.session_state["jump"] = "Mood-Based Songs"
    with c3:
        if st.button("🎶 Playlist Builder"):
            st.session_state["jump"] = "Playlist Builder"

    if "jump" in st.session_state:
        page = st.session_state.pop("jump")


# ------------------------ VIEW ALL SONGS ------------------------

if page == "View All Songs":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📂 All Songs")
    songs = safe_get(f"{API}/songs/")
    render_song_list(songs, log_for_user=(role=="user"), context="all")
    st.markdown('</div>', unsafe_allow_html=True)


# ------------------------ MOOD-BASED SONGS ------------------------

elif page == "Mood-Based Songs":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🎼 Browse by Mood")

    moods = ["romantic", "happy", "sad", "energetic", "calm"]
    cols = st.columns(5)

    chosen = None
    for col, m in zip(cols, moods):
        with col:
            if st.button(m.capitalize()):
                chosen = m

    if chosen:
        songs = safe_get(f"{API}/mood/{chosen}")
        render_song_list(songs, log_for_user=(role=="user"), context=f"mood_{chosen}")

    st.markdown('</div>', unsafe_allow_html=True)


# ------------------------ GENRE EXPLORER ------------------------

elif page == "Genre Explorer":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🎛 Browse by Genre")

    genres = ["Bollywood", "Pop", "EDM", "Rock", "Indie", "Punjabi", "K-pop", "Sufi", "Latin"]
    cols = st.columns(3)

    chosen = None
    for i, g in enumerate(genres):
        with cols[i % 3]:
            if st.button(g):
                chosen = g

    if chosen:
        songs = safe_get(f"{API}/genre/{chosen}")
        render_song_list(songs, log_for_user=(role=="user"), context=f"genre_{chosen}")

    st.markdown('</div>', unsafe_allow_html=True)


# ------------------------ REQUEST SONG ------------------------

elif page == "Request a Song":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📝 Request a Song")

    title = st.text_input("Song Title")
    artist = st.text_input("Artist")

    if st.button("Submit Request"):
        if not title or not artist:
            st.warning("Please fill both fields.")
        else:
            res = safe_post(f"{API}/request_song/", {"title": title, "artist": artist})
            if res:
                st.success("Your request has been submitted!")

    st.markdown('</div>', unsafe_allow_html=True)


# ------------------------ ADD SONG (MODERATOR) ------------------------

elif page == "Add Song (Moderator)":
    if role != "moderator":
        st.error("Access denied.")
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("➕ Add Song to Inventory")

        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Song Title")
            artist = st.text_input("Artist")
            genre = st.text_input("Genre")

        with col2:
            tags = st.text_input("Tags")
            lyrics = st.text_area("Lyrics", height=120)

        if st.button("Add Song"):
            safe_post(
                f"{API}/add_song/",
                {"title": title, "artist": artist, "genre": genre, "tags": tags, "lyrics": lyrics}
            )
            st.success("Song added!")

        st.markdown('</div>', unsafe_allow_html=True)


# ------------------------ MANAGE REQUESTS ------------------------

elif page == "Manage Requests":
    if role != "moderator":
        st.error("Access denied.")
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🧾 Pending Song Requests")

        reqs = safe_get(f"{API}/requests/")
        if not reqs:
            st.info("No pending requests.")
        else:
            for r in reqs:
                st.markdown(f"**{r['title']}** — {r['artist']}")
                colA, colB = st.columns(2)

                with colA:
                    if st.button("Approve (AI)", key=f"a{r['id']}"):
                        safe_post(f"{API}/requests/approve/{r['id']}", {})
                        st.success("Approved!")
                        st.experimental_rerun()

                with colB:
                    if st.button("Reject", key=f"d{r['id']}"):
                        requests.delete(f"{API}/requests/{r['id']}")
                        st.warning("Rejected.")
                        st.experimental_rerun()

                st.write("---")

        st.markdown('</div>', unsafe_allow_html=True)


# ------------------------ MY ANALYTICS ------------------------

elif page == "My Analytics":
    if role != "user":
        st.error("Login as user.")
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📊 My Listening Analytics")

        summary = safe_get(f"{API}/analytics/summary/{user_id}")
        if not summary or "total_plays" not in summary:
            st.info("No listening data yet.")
        else:
            total_plays = summary["total_plays"]

            st.metric("Total Plays Logged", total_plays)

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### 🎵 Top Songs")
                for s in summary["top_songs"]:
                    st.markdown(f"- **{s['title']}** — {s['artist']}")

            with col2:
                st.markdown("### 🎤 Top Artists")
                for a in summary["top_artists"]:
                    st.markdown(f"- **{a['artist']}**")

            st.markdown("### 🎚 Mood Profile")
            for mood, count in summary["moods"].items():
                st.markdown(f"- **{mood.capitalize()}**: {count}")

        st.markdown('</div>', unsafe_allow_html=True)


# ------------------------ AI SIMILAR SONGS FINDER ------------------------

elif page == "My Recommendations":
    if role != "user":
        st.error("Login as user.")
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("✨ AI Similar Songs Finder")

        st.markdown("Enter a **song title** or **song ID** to find similar songs.")

        query = st.text_input("Song Name or ID")

        if st.button("Find Similar Songs"):
            if not query.strip():
                st.warning("Please enter a song name or ID.")
            else:
                result = safe_get(f"{API}/similar/", params={"song": query})

                if isinstance(result, dict) and result.get("error"):
                    st.error(result["error"])
                else:
                    st.markdown("### 🎵 Similar Songs")
                    render_song_list(result, log_for_user=True, context="similar")

        st.markdown('</div>', unsafe_allow_html=True)


# ------------------------ PLAYLIST BUILDER ------------------------

elif page == "Playlist Builder":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🎶 Playlist Builder")

    new_name = st.text_input("New Playlist Name")
    if st.button("Create Playlist"):
        res = safe_post(f"{API}/playlists/create/", {"name": new_name})
        if res:
            st.success(f"Playlist '{new_name}' created!")

    st.write("---")

    playlists = safe_get(f"{API}/playlists/")
    names = list(playlists.keys())

    if names:
        chosen_list = st.selectbox("Select Playlist", names)

        all_songs = safe_get(f"{API}/songs/")
        mapping = {f"{s['title']} - {s['artist']}": s["id"] for s in all_songs}

        chosen_song = st.selectbox("Choose Song to Add", list(mapping.keys()))

        if st.button("Add Song"):
            safe_post(
                f"{API}/playlists/add_song/",
                {"playlist": chosen_list, "song_id": mapping[chosen_song]}
            )
            st.success("Song added!")

        if st.button("Show Playlist Songs"):
            pl_songs = safe_get(f"{API}/playlists/view/{chosen_list}")
            render_song_list(pl_songs, log_for_user=(role=="user"), context=f"pl_{chosen_list}")

    else:
        st.info("No playlists available.")

    st.markdown('</div>', unsafe_allow_html=True)
