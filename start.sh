#!/bin/sh

# 1. Python सिंक स्क्रिप्ट को बैकग्राउंड में चलाओ
python /sync.py &

# 2. Meilisearch को फोरग्राउंड (सामने) चलाओ ताकि सर्वर चलता रहे
meilisearch
