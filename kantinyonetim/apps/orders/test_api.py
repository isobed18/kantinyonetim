import requests

API_URL = "http://localhost:8000/api/voice-order/"
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU1ODczMTg1LCJpYXQiOjE3NTU4NzEzODUsImp0aSI6IjEyY2U5MjIwNGJmOTQ5ZDZhYWM4ZmJkYzE3NGVlNGM0IiwidXNlcl9pZCI6IjYifQ.LJswch8HXUReNYYsrQOI6qqXzsiiImGidpcWdHgAg2M"


AUDIO_FILE_PATH = r"C:\Users\ishak\kantinyonetimproje\kantinyonetim\media\audio\deneme2.ogg" 

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
