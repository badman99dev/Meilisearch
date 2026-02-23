# Meilisearch का ऑफिशियल लाइटवेट इमेज इस्तेमाल करें
FROM getmeili/meilisearch:latest

# पोर्ट 7700 को एक्सपोज करें
EXPOSE 7700

# पाथ को सही करें (सिर्फ meilisearch लिखें)
CMD ["meilisearch"]
