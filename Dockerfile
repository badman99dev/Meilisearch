# Meilisearch का लेटेस्ट वर्शन इस्तेमाल करें
FROM getmeili/meilisearch:latest

# प्रोडक्शन के लिए पोर्ट 7700 सेट करें
EXPOSE 7700

# Meilisearch को रन करने की कमांड
CMD ["./meilisearch"]

