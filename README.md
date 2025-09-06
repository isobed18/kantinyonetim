
# Kantin Yönetim — Web + Sesli Sipariş Mobil Uygulama

Kantin Yönetim; bir **Django tabanlı REST API + hafif web arayüzü** ile, ona bağlı **Expo/React Native mobil uygulamadan** oluşan iki parçalı bir sistemdir. Amaç; kantin/menü yönetimini kolaylaştırmak, müşterilerin hızlı sipariş vermesini sağlamak ve **sesli sipariş** desteğiyle mutfak/personel akışını hızlandırmaktır.

- **Web/Backend**: Menü öğeleri ve stok yönetimi, sipariş akışı, kullanıcı/rol yönetimi, denetim kayıtları ve bildirimler. Tüm servisler JSON REST API olarak da sunulur.
- **Mobil (Expo/React Native)**: Kullanıcı girişi (JWT), menü görüntüleme, **sesli sipariş → otomatik çözümleme → onayla ve oluştur** akışı, “Siparişlerim”, personel için **sipariş durumu** yönetimi (kaydırarak durum değiştir, iptal et).

> Kısacası: Müşteri sesle sipariş verir, sistem yazıya çevirir ve menüye eşler, kullanıcı onaylar, sipariş oluşturulur; personel ekranından hazırlanır ve tamamlanır.

---

## Mimari Genel Bakış

```
repo-root/
├─ requirements.txt              # Sunucu bağımlılıkları (Django, DRF, Whisper, Torch, vb.)
├─ kantinyonetim/               # Django projesi (REST API + web UI)
│  ├─ manage.py
│  ├─ kantinyonetim/            # settings.py, urls.py, wsgi.py
│  └─ apps/
│     ├─ menu/                  # Menü öğeleri CRUD + resim yükleme
│     ├─ orders/                # Sipariş, sipariş öğesi, sesli sipariş çözümleme akışı
│     ├─ stock/                 # Stok yönetimi
│     └─ users/                 # Kullanıcı/rol, denetim logu, bildirimler, JWT
└─ mobile_app/
   └─ kantinyonetim/            # Expo/React Native uygulaması
      ├─ app/                   # Ekranlar (tabs: home, menu, staff, profile, vs.)
      ├─ constants/constants.ts # API taban adresi (LAN IP burada değiştirilecek)
      └─ package.json           # Mobil bağımlılıklar
```

---

## Başlıca Özellikler

### 1) Mobil Uygulama (Expo/React Native)
- **JWT ile giriş**: `/api/token/` üzerinden kullanıcı adı/e‑posta + şifre ile giriş; token’lar `AsyncStorage`’da tutulur.
- **Menü**: Kategorili liste, fiyat/uygunluk bilgisi, öğe görseli.
- **Sesli Sipariş Akışı**:
  - Telefonda ses kaydı alınır, **sunucuya yüklenir**, Whisper modeli ile **Türkçe** konuşma **yazıya** çevrilir.
  - Metinden **ürün + adet** çıkarılır, **özet** kullanıcıya gösterilir.
  - Kullanıcı **onaylar → sipariş** oluşur (`/api/confirm-order/`). Stok kontrolleri yapılır, toplam hesaplanır.
- **Siparişlerim**: Kullanıcı kendi sipariş geçmişini ve durumlarını görebilir.
- **Personel Sekmesi**:
  - Gelen siparişleri görme.
  - **Kaydırarak** sipariş **durumu güncelleme** (ör. *pending → preparing → ready → completed*).
  - **İptal** edebilme (`/api/orders/{id}/cancel/`).
- **Bildirimler/Toast’lar**: Önemli aksiyonlarda görsel geri bildirim.

> Mobil klasörü: `mobile_app/kantinyonetim` (Expo, TypeScript, `expo-router`, `react-native-gesture-handler`, `react-native-toast-message` vb.)

### 2) Web + REST API (Django + DRF)
- **Kimlik Doğrulama & Roller**: JWT (SimpleJWT). Roller: `customer`, `staff`, `admin`.
- **Menü Yönetimi**: CRUD, **resim yükleme** (`ImageField → MEDIA_ROOT/menu_images/`).
- **Stok Yönetimi**: Her menü öğesine stok tanımı. Güncellemede **denetim kaydı** (audit log).
- **Sipariş Akışı**:
  - Durumlar: `pending`, `preparing`, `ready`, `completed`, `cancelled`.
  - **Toplam tutar** otomatik hesaplanır (sinyaller ile `OrderItem` ekleme/silmede).
  - **İptal** ve **yeniden atama** işlemleri için özel eylemler.
- **Sesli Sipariş Çözümleme (Server‑side)**:
  - `openai-whisper` + (varsa) **CUDA** hızlandırma.
  - Türkçe konuşmayı yazıya çevirir, metinden ürün ve adetleri çıkarır, menü ile eşler.
- **Denetim Kaydı & Bildirimler**: Kullanıcı aksiyonları `AuditLog` ile saklanır; personele **yeni sipariş bildirimi** üretilebilir.
- **Hafif Web UI**: Django template + fetch tabanlı basit arayüz (giriş, menü, stok, log vb.).

---

## Hızlı API Özeti (örnekler)

> Tüm uçlar **JWT** ister (login hariç). Temel kök: `http://<SUNUCU-IP>:8000/api/`

| Uç Nokta | Metod | Açıklama |
|---|---|---|
| `/token/` | POST | Giriş (kullanıcı adı **veya** e‑posta + şifre) → `access` + `refresh` |
| `/token/refresh/` | POST | Access token yenileme |
| `/menu-items/` | GET/POST/PATCH/DELETE | Menü yönetimi (+ resim yükleme) |
| `/stock/` | GET/PATCH | Stok görüntüle/güncelle (personel/admin) |
| `/orders/` | GET/POST | Sipariş listele/oluştur |
| `/orders/{id}/` | PATCH | Sipariş **durumu** güncelle (personel) |
| `/orders/{id}/cancel/` | POST | Siparişi iptal et |
| `/parse-voice-order/` | POST (Form‑Data `audio`) | Ses dosyasını çözümle, **özet** döner |
| `/confirm-order/` | POST | Onaylanan özet ile **sipariş oluştur** |
| `/users/` | GET/POST/PATCH | Kullanıcı yönetimi (admin) |
| `/users/audit-logs/` | GET | Denetim kayıtları |

---

## Kurulum

### Gereksinimler
- **Python 3.10+**, **pip**, **virtualenv** (önerilir)
- **Node.js 18+**, **npm**
- **ffmpeg** (Whisper için gerekli)  
  - Windows: `choco install ffmpeg` (PowerShell/Chocolatey)  
  - macOS: `brew install ffmpeg`  
  - Linux (Ubuntu): `sudo apt-get install ffmpeg`
- (Opsiyonel) **CUDA** destekli Nvidia GPU + `torch` CUDA sürümü (Whisper hızlandırması için)

> Not: Repo’daki `requirements.txt` bazı sistemlerde **UTF‑16** kodlu olabilir. `pip -r requirements.txt` sırasında karakter hatası alırsanız dosyayı UTF‑8 olarak kaydedin.

---

### 1) Backend (Django) Kurulumu

```bash
# 1) Depoyu açın ve sanal ortam oluşturun
cd <repo-klasörü>                     # ör: kantinyonetim-main/
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

# 2) Bağımlılıkları kurun
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3) .env dosyasını OLUŞTURUN (manage.py'nin yanına)
cd kantinyonetim
# Windows
type NUL > .env
# macOS/Linux
# touch .env
```

`.env` dosyası içeriği (örnek):

```env
# manage.py ile AYNI klasörde (.env)
SECRET_KEY=<buraya-django-secret-key>
# İsteğe bağlı:
# DEBUG=True
# ALLOWED_HOSTS=*
```

**SECRET_KEY üretimi** (tek satır komut):
```bash
# Seçenek 1
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"

# Seçenek 2
python - << 'PY'
import secrets; print(secrets.token_urlsafe(64))
PY
```

Devam:
```bash
# 4) Veritabanı migrate
python manage.py migrate

# 5) Yönetici kullanıcı oluştur
python manage.py createsuperuser

# 6) Sunucuyu başlat (LAN erişimi için 0.0.0.0)
python manage.py runserver 0.0.0.0:8000
```

> **Whisper cihaz seçimi**: GPU yoksa `apps/orders/views.py` içinde
> ```py
> whisper_model = whisper.load_model("small", device="cpu")  # "cuda" yerine "cpu"
> ```
> olarak değiştirin. CUDA kuruluysa `"cuda"` daha hızlıdır.

> **Media**: Menü görselleri `MEDIA_ROOT/menu_images/` içine yüklenir. Geliştirmede Django otomatik servis eder.

---

### 2) Mobil (Expo/React Native) Kurulumu

```bash
# 1) Mobil dizine geçin
cd <repo-klasörü>/mobile_app/kantinyonetim

# 2) Bağımlılıkları kurun
npm install

# 3) Backend IP’nizi constants.ts içine yazın
#   Dosya: mobile_app/kantinyonetim/constants/constants.ts
#   Örnek:
#   export const API_URL = 'http://192.168.1.34:8000/api';
#
#   Windows IP öğrenme:
#     ipconfig | findstr /i "IPv4"
#   macOS/Linux IP öğrenme:
#     ifconfig | grep inet
#
#   Telefon/emülatör ile bilgisayar AYNI Wi‑Fi/LAN üzerinde olmalı.
#   Android emülatörde "localhost" yerine bilgisayar IP’sini kullanın.
#
# 4) Uygulamayı başlatın
npx expo start
# Android cihazda
npx expo start --android
# iOS (Mac)
npx expo start --ios
```

> **Giriş**: Mobil uygulama `/api/token/` ile giriş yapar. Kullanıcıyı **Django admin**’den oluşturabilir, role ataması yapabilirsiniz (`staff`, `admin`).

---

## Çalıştırma Sırası (Özet)
1. **Backend’i** başlatın: `python manage.py runserver 0.0.0.0:8000`
2. Tarayıcıdan kontrol: `http://<SUNUCU-IP>:8000/` ve `http://<SUNUCU-IP>:8000/api/menu-items/`
3. **Mobil** `constants.ts` içinde `API_URL`’i **ayarlayın** ve `npx expo start` ile açın.
4. Mobilde giriş yapın → Menü görün → Sesli sipariş → **Özet** → **Onayla** → Personel ekranında durumu ilerletin.

---

## Roller ve Yetkiler
- Varsayılan rol: `customer`
- Personel işlemleri için kullanıcıya `staff` veya `admin` rolü verin.
- Rol atama yöntemleri:
  - **Django admin** panelinden kullanıcıyı düzenleyin.
  - veya **API** ile (admin token’ı ile):  
    ```bash
    curl -X PATCH http://<IP>:8000/api/users/<id>/ \
      -H "Authorization: Bearer <ACCESS_TOKEN>" \
      -H "Content-Type: application/json" \
      -d '{"role":"staff"}'
    ```

---

## Sık Karşılaşılan Sorunlar

- **401 Unauthorized**: Access token süresi dolmuş olabilir. `/api/token/refresh/` ile yenileyin.
- **FFmpeg not found**: Whisper’ın ses çözümlemesi için `ffmpeg` kurulmalı.
- **CUDA/CPU uyumsuzluğu**: GPU yoksa `device="cpu"` kullanın.
- **Android emülatör “localhost”**: Emülatör içinden bilgisayar IP’sini kullanın (örn. `http://192.168.x.x:8000`).
- **Windows Güvenlik Duvarı**: LAN’dan erişim için 8000 portuna izin verin.
- **`requirements.txt` kodlaması**: Pip okuma hatası alırsanız dosyayı **UTF‑8** olarak kaydedin.

---

## Notlar
- Veri tabanı varsayılan olarak **SQLite**’tır. Üretimde Postgres gibi bir veritabanına geçirip `DATABASES` ayarını düzenleyin.
- Statik dosyalar/görsellerin üretim ortamında servis edilmesi için (nginx + whitenoise vb.) ek yapılandırma gerekir.

---

## Lisans
Proje içinde açıkça belirtilmemiştir. Kurum içi/kişisel kullanım için geliştirildiği varsayılmaktadır. Lisans eklemek isterseniz `LICENSE` dosyası oluşturun.
