import streamlit as st
import aiohttp
import asyncio
import ssl
import logging
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

GENIUS_API_KEY = ""
GENIUS_BASE_URL = "https://api.genius.com"
LASTFM_API_KEY = ""
LASTFM_BASE_URL = "http://ws.audioscrobbler.com/2.0/"

if 'search_history' not in st.session_state:
    st.session_state.search_history = []

async def search_song(lyrics):
    try:
        if not lyrics or len(lyrics.strip()) == 0:
            return None
            
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
            
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            headers = {"Authorization": f"Bearer {GENIUS_API_KEY}"}
            params = {"q": lyrics}
            
            async with session.get(f"{GENIUS_BASE_URL}/search", headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    hits = data.get("response", {}).get("hits", [])
                    
                    if hits:
                        song_info = {
                            "title": hits[0]["result"]["title"],
                            "artist": hits[0]["result"]["primary_artist"]["name"],
                            "url": hits[0]["result"]["url"]
                        }
                        
                        search_result = {
                            "text": lyrics,
                            "song": song_info,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        if 'search_history' in st.session_state:
                            st.session_state.search_history.append(search_result)
                        return search_result
                    return None
                return None
                    
    except Exception as e:
        st.error(f"Error searching for song: {str(e)}")
        return None


async def get_similar_songs(artist, track):
    try:
        params = {
            "method": "track.getsimilar",
            "artist": artist.replace("&", "and").replace("/", " ").strip(),
            "track": track.replace("&", "and").replace("/", " ").strip(),
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "limit": 5,
            "autocorrect": 1
        }
        
        logger.debug(f"Request to Last.fm API: {LASTFM_BASE_URL}")
        logger.debug(f"Parameters: {params}")
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            check_params = {
                "method": "track.getInfo",
                "artist": params["artist"],
                "track": params["track"],
                "api_key": LASTFM_API_KEY,
                "format": "json"
            }
            
            async with session.get(LASTFM_BASE_URL, params=check_params) as check_response:
                if check_response.status != 200:
                    logger.warning("Track not found in Last.fm database")
                    return []
                
            async with session.get(LASTFM_BASE_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Last.fm API response: {data}")
                    
                    if "error" in data:
                        logger.warning(f"Last.fm API returned error: {data.get('message')}")
                        return []
                        
                    similar_tracks = data.get("similartracks", {}).get("track", [])
                    if not similar_tracks:
                        return []
                    
                    if not isinstance(similar_tracks, list):
                        similar_tracks = [similar_tracks]
                    
                    return [
                        {
                            "title": track.get("name", "").strip(),
                            "artist": track.get("artist", {}).get("name", "").strip()
                        }
                        for track in similar_tracks
                        if isinstance(track, dict) and 
                        track.get("name") and 
                        track.get("artist", {}).get("name")
                    ]
                return []
                
    except Exception as e:
        logger.error(f"Error searching for similar songs: {str(e)}")
        return []

st.title("Search Songs by Lyrics")

lyrics = st.text_input("Enter song lyrics:")


if st.button("🔍 Find Song"):
    if lyrics:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(search_song(lyrics))
            
            if result:
                st.success(f"Found song: {result['song']['title']} - {result['song']['artist']}")
                st.markdown(f"[Open on Genius]({result['song']['url']})")
                
                try:
                    similar_songs = loop.run_until_complete(get_similar_songs(result['song']['artist'], result['song']['title']))
                    
                    if similar_songs:
                        st.subheader("Similar Songs:")
                        for song in similar_songs:
                            st.write(f"🎵 {song['title']} - {song['artist']}")
                    else:
                        st.info("No similar songs found")
                except Exception as e:
                    st.warning(f"Failed to load similar songs: {str(e)}")
                    
            else:
                st.warning("Could not find the song. Try different lyrics.")
                
            loop.close()
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
    else:
        st.warning("Please enter lyrics to search")

if st.session_state.search_history:
    st.subheader("Search History")
    for item in reversed(st.session_state.search_history):
        with st.expander(f"{item['timestamp']}: {item['song']['title']} - {item['song']['artist']}"):
            st.write(f"Search query: {item['text']}")
