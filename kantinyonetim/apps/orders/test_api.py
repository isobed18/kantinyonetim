import requests

API_URL = "http://localhost:8000/api/voice-order/"
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU1ODA2NjYwLCJpYXQiOjE3NTU4MDQ4NjAsImp0aSI6IjNkYjFlYzFjNzFiYTQwMjg4OGQxNmM1ZDNhZGFhYjQyIiwidXNlcl9pZCI6IjQifQ.H_TyVjfLJGJ_2IBa8ZGM5er404NM_RKDJ9vj_PuzreQ"


AUDIO_FILE_PATH = r"C:\Users\ishak\kantinyonetimproje\kantinyonetim\media\audio\siparisdeneme2.m4a" 

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
