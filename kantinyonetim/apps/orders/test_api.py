import requests

API_URL = "http://localhost:8000/api/voice-order/"
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU1Njg4MDM3LCJpYXQiOjE3NTU2ODYyMzcsImp0aSI6IjRlYTRjNWY3NTNlZjRmODVhYzRkYTNmYWUzYjNiMDZiIiwidXNlcl9pZCI6IjYifQ.svAcAaNnveeF_C9EIFNXWb3WrYZjQkkEiregmg9m5Ss"

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
    print("Yanıt:", err.response.json())
except FileNotFoundError:
    print(f"Hata: Dosya bulunamadı - {AUDIO_FILE_PATH}")
except Exception as e:
    print(f"Beklenmeyen bir hata oluştu: {e}")
