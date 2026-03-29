from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
import json
import os

app = FastAPI()

DB = "songs.db"
DATASET = "songs_dataset.json"
AUDIO_DIR = "audio"   # folder where your mp3 files are stored


# --------------------- DATABASE SETUP ----------------------
def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Main songs table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            artist TEXT,
            genre TEXT,
            lyrics TEXT,
            tags TEXT
        )
    """)

    # Playlists table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS playlists (
            name TEXT PRIMARY KEY,
            songs TEXT
        )
    """)

    # Song requests table (user requests a song)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS song_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            artist TEXT
        )
    """)

    # Users table (for personalized analytics)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE
        )
    """)

    # Listening history (user plays)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS listening_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            song_id INTEGER,
            ts TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


# --------------------- LOAD DATASET ------------------------
def preload_songs():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM songs")
    count = cur.fetchone()[0]

    if count > 0:
        print("Songs already present — skipping preload.")
        conn.close()
        return

    if not os.path.exists(DATASET):
        print("Dataset not found.")
        conn.close()
        return

    with open(DATASET, "r", encoding="utf8") as f:
        data = json.load(f)

    for s in data:
        cur.execute("""
            INSERT INTO songs (title, artist, genre, lyrics, tags)
            VALUES (?, ?, ?, ?, ?)
        """, (s["title"], s["artist"], s["genre"], s["lyrics"], s["tags"]))

    conn.commit()
    conn.close()
    print("Dataset loaded successfully.")


preload_songs()


# ---------------------- MODELS -----------------------------
class SongInput(BaseModel):
    title: str
    artist: str
    genre: str = ""
    lyrics: str = ""
    tags: str = ""


class SearchQuery(BaseModel):
    query: str


class PlaylistCreate(BaseModel):
    name: str


class PlaylistAdd(BaseModel):
    playlist: str
    song_id: int


class SongRequestInput(BaseModel):
    title: str
    artist: str


class UserLogin(BaseModel):
    username: str


class PlayLog(BaseModel):
    user_id: int
    song_id: int


# ---------------------- AI CLASSIFIER (for requests) -----------------------------
def ai_classify_song(title: str, artist: str):
    """
    Simple rule-based classifier that guesses genre, tags, and placeholder lyrics
    from title + artist. This counts as a lightweight AI component.
    """
    text = f"{title} {artist}".lower()

    genre = "Pop"
    tags = []

    # Very rough heuristics based on common keywords
    if any(k in text for k in ["arijit", "ar rahman", "bollywood", "naatu", "kesariya", "tum hi ho", "srivalli"]):
        genre = "Bollywood"
        tags += ["hindi", "bollywood"]

    if any(k in text for k in ["bts", "k-pop", "kpop"]):
        genre = "K-pop"
        tags += ["kpop", "korean"]

    if any(k in text for k in ["alan walker", "avicii", "dj snake"]):
        genre = "EDM"
        tags += ["edm", "electronic"]

    if any(k in text for k in ["imagine dragons", "linkin park", "rock"]):
        genre = "Rock"
        tags += ["rock", "energetic"]

    if any(k in text for k in ["love", "ishq", "dil", "heart", "romantic", "tera", "meri"]):
        tags.append("romantic")

    if any(k in text for k in ["sad", "cry", "yaad", "hurt"]):
        tags.append("sad")

    if not tags:
        tags.append("requested")

    tags = list(dict.fromkeys(tags))
    tags_str = ",".join(tags)

    lyrics = f"Requested song '{title}' by {artist}. (Lyrics to be updated by moderator.)"

    return genre, lyrics, tags_str


# --------------------- USER LOGIN ---------------------------

@app.post("/user/login/")
def user_login(u: UserLogin):
    username = u.username.strip()
    if not username:
        raise HTTPException(400, "Username cannot be empty.")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE username=?", (username,))
    row = cur.fetchone()

    if row:
        user_id = row[0]
    else:
        cur.execute("INSERT INTO users (username) VALUES (?)", (username,))
        conn.commit()
        user_id = cur.lastrowid

    conn.close()
    return {"user_id": user_id, "username": username}


# --------------------- SONG CRUD ---------------------------

@app.get("/songs/")
def get_songs():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM songs")
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "title": r[1],
            "artist": r[2],
            "genre": r[3],
            "lyrics": r[4],
            "tags": r[5],
        }
        for r in rows
    ]


@app.post("/add_song/")
def add_song(song: SongInput):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO songs (title, artist, genre, lyrics, tags)
        VALUES (?, ?, ?, ?, ?)
    """, (song.title, song.artist, song.genre, song.lyrics, song.tags))

    conn.commit()
    conn.close()

    return {"status": "success"}


# --------------------- SEARCH (not used in UI now) -------------------------------

@app.post("/search/")
def search_songs(q: SearchQuery):
    query = q.query.lower()

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM songs")
    rows = cur.fetchall()
    conn.close()

    results = []
    for s in rows:
        combined = (s[3] or "") + " " + (s[4] or "")
        if query in combined.lower():
            results.append({
                "id": s[0],
                "title": s[1],
                "artist": s[2],
                "genre": s[3],
            })

    return results


# --------------------- MOOD FILTER --------------------------

@app.get("/mood/{m}")
def mood_filter(m: str):
    mood = m.lower()

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM songs")
    rows = cur.fetchall()
    conn.close()

    mood_map = {
        "romantic": ["love", "romantic"],
        "happy": ["happy", "dance"],
        "sad": ["sad", "emotional"],
        "energetic": ["energetic", "party"],
        "calm": ["calm", "soft"],
    }

    keywords = mood_map.get(mood, [])

    results = []
    for s in rows:
        tags = (s[5] or "").lower()
        if any(k in tags for k in keywords):
            results.append({
                "id": s[0],
                "title": s[1],
                "artist": s[2],
                "genre": s[3],
            })

    return results


# --------------------- GENRE FILTER -------------------------

@app.get("/genre/{g}")
def genre_filter(g: str):
    genre = g.lower()

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM songs")
    rows = cur.fetchall()
    conn.close()

    results = [
        {
            "id": s[0],
            "title": s[1],
            "artist": s[2],
            "genre": s[3],
        }
        for s in rows
        if genre in (s[3] or "").lower()
    ]

    return results


# --------------------- AUDIO SERVE (FULL MP3) -----------------------

@app.get("/audio/{song_id}")
def get_audio(song_id: int):
    audio_path = f"{AUDIO_DIR}/{song_id}.mp3"

    if not os.path.exists(audio_path):
        raise HTTPException(404, "Audio file not found")

    return FileResponse(audio_path, media_type="audio/mpeg")


# --------------------- SONG REQUESTS (USER SIDE) -----------------------

@app.post("/request_song/")
def request_song(req: SongRequestInput):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO song_requests (title, artist) VALUES (?, ?)",
        (req.title, req.artist)
    )

    conn.commit()
    conn.close()

    return {"status": "requested"}


@app.get("/requests/")
def list_requests():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT id, title, artist FROM song_requests")
    rows = cur.fetchall()
    conn.close()

    return [
        {"id": r[0], "title": r[1], "artist": r[2]}
        for r in rows
    ]


@app.post("/requests/approve/{req_id}")
def approve_request(req_id: int):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT id, title, artist FROM song_requests WHERE id=?", (req_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        raise HTTPException(404, "Request not found")

    _, title, artist = row

    # Use AI classifier to guess genre, lyrics, tags
    genre, lyrics, tags = ai_classify_song(title, artist)

    cur.execute("""
        INSERT INTO songs (title, artist, genre, lyrics, tags)
        VALUES (?, ?, ?, ?, ?)
    """, (title, artist, genre, lyrics, tags))

    # Remove the request after approval
    cur.execute("DELETE FROM song_requests WHERE id=?", (req_id,))

    conn.commit()
    conn.close()

    return {
        "status": "approved",
        "song": {
            "title": title,
            "artist": artist,
            "genre": genre,
            "tags": tags
        }
    }


@app.delete("/requests/{req_id}")
def delete_request(req_id: int):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("DELETE FROM song_requests WHERE id=?", (req_id,))
    conn.commit()
    conn.close()

    return {"status": "deleted"}


# --------------------- PLAYLIST API -------------------------

@app.get("/playlists/")
def list_playlists():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT name, songs FROM playlists")
    rows = cur.fetchall()
    conn.close()

    data = {}
    for name, songs_json in rows:
        data[name] = json.loads(songs_json)

    return data


@app.post("/playlists/create/")
def create_playlist(p: PlaylistCreate):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("INSERT OR IGNORE INTO playlists (name, songs) VALUES (?, ?)",
                (p.name, json.dumps([])))

    conn.commit()
    conn.close()

    return {"status": "created"}


@app.post("/playlists/add_song/")
def playlist_add(p: PlaylistAdd):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Retrieve existing playlist
    cur.execute("SELECT songs FROM playlists WHERE name=?", (p.playlist,))
    row = cur.fetchone()

    if not row:
        conn.close()
        raise HTTPException(404, "Playlist not found")

    song_list = json.loads(row[0])

    if p.song_id not in song_list:
        song_list.append(p.song_id)

    cur.execute("UPDATE playlists SET songs=? WHERE name=?",
                (json.dumps(song_list), p.playlist))

    conn.commit()
    conn.close()

    return {"status": "song added"}


@app.get("/playlists/view/{name}")
def playlist_view(name: str):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT songs FROM playlists WHERE name=?", (name,))
    row = cur.fetchone()

    if not row:
        conn.close()
        raise HTTPException(404, "Playlist not found")

    song_ids = json.loads(row[0])

    songs = []
    for sid in song_ids:
        cur.execute("SELECT * FROM songs WHERE id=?", (sid,))
        s = cur.fetchone()
        if s:
            songs.append({
                "id": s[0],
                "title": s[1],
                "artist": s[2],
                "genre": s[3]
            })

    conn.close()
    return songs


# --------------------- LOG PLAY (LISTENING HISTORY) -------------------------

@app.post("/log_play/")
def log_play(p: PlayLog):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Validate user
    cur.execute("SELECT id FROM users WHERE id=?", (p.user_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(404, "User not found")

    # Validate song
    cur.execute("SELECT id FROM songs WHERE id=?", (p.song_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(404, "Song not found")

    cur.execute(
        "INSERT INTO listening_history (user_id, song_id, ts) VALUES (?, ?, datetime('now'))",
        (p.user_id, p.song_id)
    )

    conn.commit()
    conn.close()

    return {"status": "logged"}


# --------------------- ANALYTICS SUMMARY -------------------------

@app.get("/analytics/summary/{user_id}")
def analytics_summary(user_id: int):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Validate user
    cur.execute("SELECT id FROM users WHERE id=?", (user_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(404, "User not found")

    # Total plays
    cur.execute("SELECT COUNT(*) FROM listening_history WHERE user_id=?", (user_id,))
    total_plays = cur.fetchone()[0]

    # Top songs
    cur.execute("""
        SELECT s.id, s.title, s.artist, COUNT(*) as c
        FROM listening_history h
        JOIN songs s ON h.song_id = s.id
        WHERE h.user_id=?
        GROUP BY s.id, s.title, s.artist
        ORDER BY c DESC
        LIMIT 5
    """, (user_id,))
    top_songs_rows = cur.fetchall()
    top_songs = [
        {"id": r[0], "title": r[1], "artist": r[2], "plays": r[3]}
        for r in top_songs_rows
    ]

    # Top artists
    cur.execute("""
        SELECT s.artist, COUNT(*) as c
        FROM listening_history h
        JOIN songs s ON h.song_id = s.id
        WHERE h.user_id=?
        GROUP BY s.artist
        ORDER BY c DESC
        LIMIT 5
    """, (user_id,))
    top_artists_rows = cur.fetchall()
    top_artists = [
        {"artist": r[0], "plays": r[1]}
        for r in top_artists_rows
    ]

    # Mood distribution
    mood_map = {
        "romantic": ["love", "romantic"],
        "happy": ["happy", "dance"],
        "sad": ["sad", "emotional"],
        "energetic": ["energetic", "party"],
        "calm": ["calm", "soft"],
    }
    mood_counts = {k: 0 for k in mood_map.keys()}

    cur.execute("""
        SELECT s.tags
        FROM listening_history h
        JOIN songs s ON h.song_id = s.id
        WHERE h.user_id=?
    """, (user_id,))
    tag_rows = cur.fetchall()

    for (tags_str,) in tag_rows:
        tags = (tags_str or "").lower()
        for mood, keywords in mood_map.items():
            if any(k in tags for k in keywords):
                mood_counts[mood] += 1

    conn.close()

    return {
        "total_plays": total_plays,
        "top_songs": top_songs,
        "top_artists": top_artists,
        "moods": mood_counts
    }


# --------------------- ANALYTICS RECOMMENDATIONS -------------------------
# (kept as-is, even if UI stops using it; safe to keep)

@app.get("/analytics/recommend/{user_id}")
def analytics_recommend(user_id: int):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Validate user
    cur.execute("SELECT id FROM users WHERE id=?", (user_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(404, "User not found")

    # Songs the user has listened to
    cur.execute("""
        SELECT DISTINCT s.id, s.genre, s.tags
        FROM listening_history h
        JOIN songs s ON h.song_id = s.id
        WHERE h.user_id=?
    """, (user_id,))
    listened_rows = cur.fetchall()

    if not listened_rows:
        conn.close()
        return []

    listened_ids = set()
    genre_scores = {}
    tag_scores = {}

    for sid, genre, tags in listened_rows:
        listened_ids.add(sid)
        g = (genre or "").lower()
        if g:
            genre_scores[g] = genre_scores.get(g, 0) + 1

        for t in (tags or "").lower().split(","):
            t = t.strip()
            if t:
                tag_scores[t] = tag_scores.get(t, 0) + 1

    # All songs to consider for recommendations
    cur.execute("SELECT id, title, artist, genre, tags FROM songs")
    all_rows = cur.fetchall()
    conn.close()

    recs = []

    for sid, title, artist, genre, tags in all_rows:
        if sid in listened_ids:
            continue

        score = 0
        g = (genre or "").lower()
        if g in genre_scores:
            score += genre_scores[g] * 2

        for t in (tags or "").lower().split(","):
            t = t.strip()
            if t in tag_scores:
                score += tag_scores[t]

        if score > 0:
            recs.append((score, sid, title, artist, genre))

    recs.sort(reverse=True, key=lambda x: x[0])

    return [
        {
            "id": r[1],
            "title": r[2],
            "artist": r[3],
            "genre": r[4]
        }
        for r in recs[:10]
    ]


# --------------------- AI SIMILAR SONGS (NEW) -------------------------

@app.get("/similar/")
def similar_songs(song: str):
    """
    Return songs that are similar to a given song (by ID or title)
    based on genre, artist, and overlapping tags.
    """

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Try to resolve the base song
    if song.isdigit():
        cur.execute("SELECT id, title, artist, genre, tags FROM songs WHERE id=?", (int(song),))
    else:
        cur.execute("SELECT id, title, artist, genre, tags FROM songs WHERE title LIKE ?", (f"%{song}%",))

    base = cur.fetchone()
    if not base:
        conn.close()
        return {"error": "Song not found in inventory."}

    base_id, base_title, base_artist, base_genre, base_tags = base
    base_artist_l = (base_artist or "").lower()
    base_genre_l = (base_genre or "").lower()
    base_tag_set = {t.strip() for t in (base_tags or "").lower().split(",") if t.strip()}
    base_title_words = set((base_title or "").lower().split())

    # Fetch all songs
    cur.execute("SELECT id, title, artist, genre, tags FROM songs")
    all_rows = cur.fetchall()
    conn.close()

    recs = []

    for sid, title, artist, genre, tags in all_rows:
        if sid == base_id:
            continue

        score = 0
        artist_l = (artist or "").lower()
        genre_l = (genre or "").lower()
        tag_set = {t.strip() for t in (tags or "").lower().split(",") if t.strip()}
        title_words = set((title or "").lower().split())

        # Same artist = strong weight
        if artist_l and artist_l == base_artist_l:
            score += 4

        # Same genre
        if genre_l and genre_l == base_genre_l:
            score += 3

        # Tag overlap
        if base_tag_set and tag_set:
            overlap = base_tag_set & tag_set
            score += 2 * len(overlap)

        # Some title word overlap
        if base_title_words and title_words and (base_title_words & title_words):
            score += 1

        if score > 0:
            recs.append((score, sid, title, artist, genre))

    # Sort by score descending
    recs.sort(key=lambda x: x[0], reverse=True)

    # Return top 10
    return [
        {
            "id": r[1],
            "title": r[2],
            "artist": r[3],
            "genre": r[4],
        }
        for r in recs[:10]
    ]
