import mysql.connector
import requests
import json
import os
import time
from datetime import date, datetime

def sync_database():
    print("\n🚀 Auto-Sync Script Started...")
    MEILI_URL = "http://localhost:7700"
    MASTER_KEY = os.getenv('MEILI_MASTER_KEY')
    headers = {'Authorization': f'Bearer {MASTER_KEY}', 'Content-Type': 'application/json'}
    
    # 1. Meilisearch के लिए थोड़ा इंतज़ार (ताकि सर्वर रेडी हो जाए)
    time.sleep(5) 

    print("🔄 Connecting to TiDB to fetch latest data...")
    try:
        db = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASS'),
            database=os.getenv('DB_NAME'),
            port=int(os.getenv('DB_PORT', 4000))
        )
        cursor = db.cursor(dictionary=True)
    except Exception as e:
        print(f"❌ DB Connection Failed: {e}")
        return

    # 2. Meilisearch Settings Update (Categories के साथ)
    settings = {
        "searchableAttributes": ["title", "original_title", "categories", "director", "cast", "description", "tagline", "slug"],
        "filterableAttributes": ["categories", "release_year", "rating", "language", "audio_label", "quality_label", "is_series", "status", "country", "is_featured"],
        "sortableAttributes": ["release_year", "rating", "views", "downloads", "created_at", "vote_count"],
        "rankingRules": ["words", "typo", "proximity", "attribute", "sort", "exactness"]
    }
    try:
        requests.patch(f"{MEILI_URL}/indexes/movies/settings", headers=headers, json=settings)
        print("⚙️ Meilisearch Settings Applied (With Categories)!")
    except Exception as e:
        print(f"⚠️ Failed to update settings: {e}")

    # 3. TiDB से डेटा निकालना (JOIN और GROUP_CONCAT के साथ)
    query = """
        SELECT m.id, m.slug, m.imdb_id, m.tmdb_id, m.youtube_id, m.title, m.original_title, 
               m.description, m.tagline, m.poster_url, m.backdrop_url, m.release_date, m.release_year, 
               m.runtime, m.status, m.language, m.country, m.is_series, m.total_seasons, m.total_episodes, 
               m.last_air_date, m.quality_label, m.audio_label, m.subtitle_label, m.rating, m.vote_count, 
               m.views, m.downloads, m.is_featured, m.is_visible, m.director, m.cast, m.created_at,
               GROUP_CONCAT(c.category_name SEPARATOR ', ') as categories
        FROM movies m
        LEFT JOIN movie_categories mc ON m.id = mc.movie_id
        LEFT JOIN categories c ON mc.category_id = c.id
        WHERE m.is_visible = 1
        GROUP BY m.id
    """
    cursor.execute(query)
    movies = cursor.fetchall()
    print(f"📦 Fetched {len(movies)} movies from TiDB. Starting upload...")

    # 4. Data Processing & Upload in Chunks (1000-1000 का बैच)
    for i in range(0, len(movies), 1000):
        chunk = movies[i:i + 1000]
        
        for m in chunk:
            # Rating को Float बनाना
            m['rating'] = float(m['rating']) if m['rating'] else 0.0
            
            # Categories की Null Value फिक्स करना
            if m['categories'] is None:
                m['categories'] = ""
                
            # Dates को String में बदलना
            for date_field in ['release_date', 'last_air_date', 'created_at']:
                if isinstance(m[date_field], (date, datetime)):
                    m[date_field] = m[date_field].strftime('%Y-%m-%d %H:%M:%S')

        # Send Batch to Meilisearch (primaryKey=id फिक्स के साथ)
        res = requests.post(f"{MEILI_URL}/indexes/movies/documents?primaryKey=id", headers=headers, json=chunk)

        if res.status_code == 202:
            print(f"✅ Synced chunk {i} to {i + len(chunk)}...")
        else:
            print(f"❌ Error syncing chunk {i}: {res.text}")
            
        time.sleep(1) # CPU को ठंडा रखने के लिए 1 सेकंड का ब्रेक

    print("🎉 BOOM! Entire Database Sync Completed Successfully!")
    db.close()

# 5. ऑटो-सिंक लूप (हर 2 घंटे में)
if __name__ == "__main__":
    while True:
        try:
            sync_database()
            print("⏳ Sync cycle finished. Sleeping for 2 hours...")
        except Exception as e:
            print(f"⚠️ Critical error in sync cycle: {e}")
            print("⏳ Will retry in 2 hours...")
        
        # 7200 सेकंड = 2 घंटे (अगर 1 घंटा करना हो तो 3600 लिख सकते हो)
        time.sleep(7200)
