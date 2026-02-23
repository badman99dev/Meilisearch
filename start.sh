#!/bin/sh

# 1. Meilisearch को बैकग्राउंड में स्टार्ट करो
meilisearch &

# 2. Python सिंक स्क्रिप्ट को बैकग्राउंड में चलाओ
python3 /sync.py &

# 3. कंटेनर को ज़िंदा रखो (ताकि रेंडर इसे बंद न करे)
wait -n

