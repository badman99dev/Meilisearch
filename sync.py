import mysql.connector
import requests
import json
import os
import time
from datetime import date, datetime

# --- GLOBAL CONFIGURATION ---
# Note: Ensure these ENV variables are set in your deployment environment
MEILI_URL = "http://localhost:7700" 
MASTER_KEY = os.getenv('MEILI_MASTER_KEY')
HEADERS = {'Authorization': f'Bearer {MASTER_KEY}', 'Content-Type': 'application/json'}

def update_meilisearch_settings():
    """Meilisearch की सेटिंग्स को Google/Netflix लेवल पर सेट करना (सिर्फ एक बार चलेगा)"""
    print("⚙️ Applying Enterprise-Grade Settings to Meilisearch...")

    settings = {
        # 1. सर्च के लिए (प्राथमिकता के अनुसार)
        "searchableAttributes": [
            "title", "original_title", "categories", "director", "cast", "tagline", "description", "slug"
        ],

        # 2. फिल्टर करने के लिए
        "filterableAttributes": [
            "categories", "release_year", "rating", "language", "audio_label", 
            "quality_label", "is_series", "status", "country", "is_featured"
        ],

        # 3. सॉर्ट करने के लिए
        "sortableAttributes": [
            "release_year", "rating", "views", "downloads", "created_at", "vote_count"
        ],

        # 4. रैंकिंग का नियम (सॉर्ट को एहमियत दी गई है)
        "rankingRules": [
            "words", "typo", "proximity", "attribute", "sort", "exactness"
        ],

        # 5. Typo Tolerance (स्पेलिंग की गलतियां माफ़ करना)
        "typoTolerance": {
            "enabled": True,
            "minWordSizeForTypos": { "oneTypo": 5, "twoTypos": 9 },
            "disableOnAttributes": ["slug"] # Slug पर स्पेलिंग मिस्टेक अलाउड नहीं
        },

        # 6. Pagination Limit (तुम्हारी 13k+ मूवीज़ के लिए बहुत ज़रूरी)
        "pagination": {
            "maxTotalHits": 20000
        }
    }

    try:
        res = requests.patch(f"{MEILI_URL}/indexes/movies/settings", headers=HEADERS, json=settings)
        if res.status_code in [200, 202]:
            print("✅ Settings applied successfully!")
        else:
            print(f"⚠️ Settings update issue: {res.text}")
    except Exception as e:
        print(f"⚠️ Failed to reach Meilisearch for settings: {e}")

def sync_database():
    """TiDB से डेटा निकालकर Meilisearch में डालना (हर 2 घंटे में चलेगा)"""
    print(f"\n🔄 Sync Cycle Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print("🔌 Connecting to TiDB Database...")
    try:
        db = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASS'),
            database=os.getenv('DB_NAME'),
            port=int(os.getenv('DB_PORT', 4000)),
            connect_timeout=10 # नेटवर्क को सुरक्षित रखने के लिए
        )
        cursor = db.cursor(dictionary=True)
    except Exception as e:
        print(f"❌ DB Connection Failed: {e}")
        return

    # 🔥 UPDATED QUERY: Hidden Categories & Empty Links Filter Added
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
        
        -- 🛑 1. Hidden Category Logic (अगर केटेगरी छिपी है, तो मूवी भी मत दिखाओ)
        AND m.id NOT IN (
            SELECT mc2.movie_id 
            FROM movie_categories mc2 
            JOIN categories c2 ON mc2.category_id = c2.id 
            WHERE c2.is_visible = 0
        )

        -- 🛑 2. Minimum 1 Link Logic (Download OR Streaming होना ही चाहिए)
        AND (
            (m.master_url IS NOT NULL AND m.master_url != '') 
            OR 
            EXISTS (SELECT 1 FROM download_links dl WHERE dl.movie_id = m.id)
        )

        GROUP BY m.id
    """

    try:
        cursor.execute(query)
        movies = cursor.fetchall()
        print(f"📦 Fetched {len(movies)} Valid Movies (Filtered Hidden/Empty). Starting Indexing...")
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        db.close()
        return

    # Data Processing & Upload (1000 के बैच में)
    for i in range(0, len(movies), 1000):
        chunk = movies[i:i + 1000]

        for m in chunk:
            # 1. Rating को Float बनाएं
            m['rating'] = float(m['rating']) if m['rating'] else 0.0

            # 2. Categories की Null Value फिक्स करें
            m['categories'] = m['categories'] if m['categories'] else ""

            # 3. Dates को String में बदलें
            for date_field in ['release_date', 'last_air_date', 'created_at']:
                if isinstance(m[date_field], (date, datetime)):
                    m[date_field] = m[date_field].strftime('%Y-%m-%d %H:%M:%S')

        # Meilisearch को बैच भेजें (primaryKey=id के साथ)
        try:
            res = requests.post(f"{MEILI_URL}/indexes/movies/documents?primaryKey=id", headers=HEADERS, json=chunk)
            if res.status_code == 202:
                print(f"✅ Synced chunk {i} to {i + len(chunk)}...")
            else:
                print(f"❌ Error syncing chunk {i}: {res.text}")
        except Exception as e:
            print(f"❌ Upload crashed at chunk {i}: {e}")

        time.sleep(1) # CPU को ठंडा रखने के लिए 1 सेकंड का ब्रेक

    print("🎉 BOOM! Entire Database Sync Completed Successfully!")
    db.close()

# --- MAIN EXECUTION LOOP ---
if __name__ == "__main__":
    print("⏳ Waiting 10 seconds for Meilisearch server to boot up...")
    time.sleep(10)

    # सबसे पहले सेटिंग्स अपडेट करो (सिर्फ 1 बार)
    update_meilisearch_settings()

    # फिर डेटाबेस सिंक का अनंत (Infinite) लूप चलाओ
    while True:
        try:
            sync_database()
            print("😴 Sync cycle finished. Sleeping for 2 hours (7200 seconds)...")
        except Exception as e:
            print(f"⚠️ Critical error in sync cycle: {e}")
            print("⏳ Will retry in 2 hours...")

        time.sleep(7200)
