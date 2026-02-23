import mysql.connector
import requests
import json
import os
import time
from datetime import date, datetime

def sync_database():
    print("🚀 Auto-Sync Script Started...")
    MEILI_URL = "http://localhost:7700"
    MASTER_KEY = os.getenv('MEILI_MASTER_KEY')
    headers = {'Authorization': f'Bearer {MASTER_KEY}', 'Content-Type': 'application/json'}
    
    # 1. Meilisearch के पूरी तरह चालू होने का इंतज़ार करें (10 सेकंड)
    time.sleep(10) 

    # 2. चेक करें कि क्या डेटा पहले से मौजूद है?
    try:
        stats = requests.get(f"{MEILI_URL}/indexes/movies/stats", headers=headers).json()
        if stats.get('numberOfDocuments', 0) > 0:
            print("✅ Data already exists in Meilisearch. Skipping sync.")
            return
    except Exception as e:
        print("Meilisearch starting up, proceeding to sync...")

    print("🔄 Connecting to TiDB...")
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

    # 3. Meilisearch Settings Update (ताकि सर्च Netflix जैसी बने)
    settings = {
        "searchableAttributes": ["title", "original_title", "director", "cast", "description", "tagline", "slug"],
        "filterableAttributes": ["release_year", "rating", "language", "audio_label", "quality_label", "is_series", "status", "country", "is_featured"],
        "sortableAttributes": ["release_year", "rating", "views", "downloads", "created_at", "vote_count"],
        "rankingRules": ["words", "typo", "proximity", "attribute", "sort", "exactness"]
    }
    requests.patch(f"{MEILI_URL}/indexes/movies/settings", headers=headers, json=settings)
    print("⚙️ Meilisearch Settings Applied!")

    # 4. TiDB से डेटा निकालना (Heavy Columns हटा दिए गए हैं)
    query = """
        SELECT id, slug, imdb_id, tmdb_id, youtube_id, title, original_title, description, tagline, 
               poster_url, backdrop_url, release_date, release_year, runtime, status, language, country, 
               is_series, total_seasons, total_episodes, last_air_date, quality_label, audio_label, 
               subtitle_label, rating, vote_count, views, downloads, is_featured, is_visible, 
               director, cast, created_at
        FROM movies WHERE is_visible = 1
    """
    cursor.execute(query)
    movies = cursor.fetchall()
    print(f"📦 Fetched {len(movies)} movies from TiDB. Starting upload...")

    # 5. Data Processing & Upload in Chunks (1000-1000 का बैच)
    for i in range(0, len(movies), 1000):
        chunk = movies[i:i + 1000]
        
        # Data Formatting: JSON में Date और Decimal सपोर्ट नहीं करता, इसलिए उन्हें सही करना होगा
        for m in chunk:
            m['rating'] = float(m['rating']) if m['rating'] else 0.0
            # Dates को String में बदलना
            for date_field in ['release_date', 'last_air_date', 'created_at']:
                if isinstance(m[date_field], (date, datetime)):
                    m[date_field] = m[date_field].strftime('%Y-%m-%d %H:%M:%S')

        # Send Batch to Meilisearch
        res = requests.post(f"{MEILI_URL}/indexes/movies/documents?primaryKey=id", headers=headers, json=chunk)

        if res.status_code == 202:
            print(f"✅ Synced chunk {i} to {i + len(chunk)}...")
        else:
            print(f"❌ Error syncing chunk {i}: {res.text}")
            
        time.sleep(1) # CPU को ठंडा रखने के लिए 1 सेकंड का ब्रेक

    print("🎉 BOOM! Entire Database Indexed Successfully!")
    db.close()

if __name__ == "__main__":
    sync_database()
  
