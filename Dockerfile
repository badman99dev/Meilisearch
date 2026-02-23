# Meilisearch का ऑफिशियल इमेज
FROM getmeili/meilisearch:latest

# Python और ज़रूरी लाइब्रेरीज़ इनस्टॉल करें
USER root
RUN apt-get update && apt-get install -y python3 python3-pip
RUN pip3 install mysql-connector-python requests

# हमारी स्क्रिप्ट्स को कंटेनर में कॉपी करें
COPY sync.py /sync.py
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Meilisearch के लिए पोर्ट 7700
EXPOSE 7700

# सर्वर स्टार्ट होने पर start.sh चलाएं
CMD ["/start.sh"]
