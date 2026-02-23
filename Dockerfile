# 1. Python का हल्का और स्टेबल वर्शन लें (इसमें apt-get और pip पहले से होता है)
FROM python:3.9-slim

# 2. Meilisearch डाउनलोड करने के लिए 'curl' इंस्टॉल करें
RUN apt-get update && apt-get install -y curl

# 3. Meilisearch का लेटेस्ट वर्शन डाउनलोड करें और उसे सिस्टम में सेट करें
RUN curl -L https://install.meilisearch.com | sh
RUN mv ./meilisearch /usr/local/bin/

# 4. अपनी Python लाइब्रेरीज़ इंस्टॉल करें
RUN pip install mysql-connector-python requests

# 5. अपनी स्क्रिप्ट्स को कंटेनर में कॉपी करें
COPY sync.py /sync.py
COPY start.sh /start.sh
RUN chmod +x /start.sh

# 6. पोर्ट 7700 खोलें
EXPOSE 7700

# 7. स्क्रिप्ट स्टार्ट करें
CMD ["/start.sh"]
