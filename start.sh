#!/bin/sh

# 1. Python सिंक स्क्रिप्ट को बैकग्राउंड में चलाओ
python /sync.py &

# 2. Meilisearch को पब्लिक IP (0.0.0.0) पर चलाओ ताकि Render उसे देख सके
meilisearch --http-addr 0.0.0.0:7700
