import requests

API_URL = "http://localhost:8000/api/voice-order/"
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU1NjkyODMxLCJpYXQiOjE3NTU2OTEwMzEsImp0aSI6IjA0NjIwNWQzNGZlZDRmZDc5ZTNhZGNjMzcxMDE2ZGZkIiwidXNlcl9pZCI6IjYifQ.UbpdpndJ77OzpDEHa_Ub3R9jH_nwNMsChHAbZJqYRRo"


AUDIO_FILE_PATH = r"C:\Users\ishak\kantinyonetimproje\kantinyonetim\media\audio\siparisdeneme2.mp3" 

try: 
    with open(AUDIO_FILE_PATH, 'rb') as audio_file:
        files = {
            'audio': ('siparisdeneme1.mp3', audio_file, 'audio/mpeg')
        }
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}"
        }
        response = requests.post(API_URL, files=files, headers=headers)
        response.raise_for_status()
    print("istek gonderildi")
    print("yanıt:", response.json())
except requests.exceptions.HTTPError as err:
    print(f"HTTP Hatası: {err}")
    print("yanıt:", err.response.json())
except FileNotFoundError:
    print(f"hata Dosya bulunamıyor - {AUDIO_FILE_PATH}")
except Exception as e:
    print(f"beklenmeyen bir hata oluştu: {e}")
