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
    # 🌟 यहाँ 'categories' को Searchable और Filterable में जोड़ दिया गया है
    settings = {
        "searchableAttributes": ["title", "original_title", "categories", "director", "cast", "description", "tagline", "slug"],
        "filterableAttributes": ["categories", "release_year", "rating", "language", "audio_label", "quality_label", "is_series", "status", "country", "is_featured"],
        "sortableAttributes": ["release_year", "rating", "views", "downloads", "created_at", "vote_count"],
        "rankingRules": ["words", "typo", "proximity", "attribute", "sort", "exactness"]
    }
    requests.patch(f"{MEILI_URL}/indexes/movies/settings", headers=headers, json=settings)
    print("⚙️ Meilisearch Settings Applied (With Categories)!")

    # 4. TiDB से डेटा निकालना (Heavy Columns हटा दिए गए हैं, JOIN के साथ Categories जोड़ी गई हैं)
    # 🌟 GROUP_CONCAT से एक मूवी की सारी कैटेगरीज कॉमा (,) के साथ आ जाएंगी
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

    # 5. Data Processing & Upload in Chunks (1000-1000 का बैच)
    for i in range(0, len(movies), 1000):
        chunk = movies[i:i + 1000]
        
        # Data Formatting: JSON में Date और Decimal सपोर्ट नहीं करता, इसलिए उन्हें सही करना होगा
        for m in chunk:
            m['rating'] = float(m['rating']) if m['rating'] else 0.0
            
            # अगर किसी मूवी की कोई कैटेगरी नहीं है, तो उसे खाली स्ट्रिंग मान लें
            if m['categories'] is None:
                m['categories'] = ""
                
            # Dates को String में बदलना
            for date_field in ['release_date', 'last_air_date', 'created_at']:
                if isinstance(m[date_field], (date, datetime)):
                    m[date_field] = m[date_field].strftime('%Y-%m-%d %H:%M:%S')

        # Send Batch to Meilisearch
        # 🌟 Primary Key वाला फिक्स यहाँ मौजूद है
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
