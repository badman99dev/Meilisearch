#!/bin/sh

# 1. Meilisearch को बैकग्राउंड में स्टार्ट करो
meilisearch &

# 2. Python सिंक स्क्रिप्ट को बैकग्राउंड में चलाओ
python /sync.py &

# 3. कंटेनर को ज़िंदा रखो
wait -n
