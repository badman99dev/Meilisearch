#!/bin/sh

# -u लगाने से Python लॉग्स को बफर नहीं करेगा और तुरंत रेंडर की स्क्रीन पर भेजेगा
python -u /sync.py &

# Meilisearch को पब्लिक IP पर चलाओ
meilisearch --http-addr 0.0.0.0:7700
