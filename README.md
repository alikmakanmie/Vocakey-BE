# Music Recognition API - Backend

Backend Flask untuk aplikasi pencarian lagu menggunakan voice, mirip Shazam. Menggunakan Shazam API untuk music recognition dan Genius API untuk lirik.

## 📋 Fitur

- ✅ Music recognition dari audio file
- ✅ Support multiple format audio (MP3, WAV, M4A, OGG, FLAC, AAC)
- ✅ Integrasi dengan Shazam API
- ✅ Integrasi dengan Genius API untuk lirik
- ✅ CORS enabled untuk Flutter mobile app
- ✅ RESTful API dengan JSON response

## 🚀 Cara Instalasi

### 1. Install Python
Pastikan Python 3.8+ sudah terinstall. Cek dengan:
```bash
python --version
```

### 2. Clone/Download Project
Download semua file ke folder project Anda.

### 3. Buat Virtual Environment (Opsional tapi disarankan)
```bash
python -m venv venv
```

Aktifkan virtual environment:
- **Windows**: `venv\Scripts\activate`
- **Mac/Linux**: `source venv/bin/activate`

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Dapatkan API Keys

#### A. RapidAPI Key (untuk Shazam)
1. Daftar di https://rapidapi.com
2. Login dan cari "Shazam" di marketplace
3. Subscribe ke "Shazam API" (ada free tier: 500 requests/bulan)
4. Copy API Key dari dashboard

#### B. Genius Access Token (untuk Lirik)
1. Daftar di https://genius.com
2. Login dan buka https://genius.com/api-clients
3. Klik "New API Client"
4. Isi form (App Name, App Website URL bisa pakai http://localhost)
5. Setelah dibuat, klik "Generate Access Token"
6. Copy token yang muncul

### 6. Masukkan API Keys
Buka file `app.py` dan ganti pada baris 20-21:

```python
# ===== LETAKKAN API KEYS ANDA DI SINI =====
RAPIDAPI_KEY = "paste_rapidapi_key_anda_disini"
GENIUS_ACCESS_TOKEN = "paste_genius_token_anda_disini"
# ==========================================
```

### 7. Jalankan Server
```bash
python app.py
```

Server akan berjalan di: http://localhost:5000

## 📖 Dokumentasi API

### 1. Health Check
**Endpoint:** `GET /api/health`

**Response:**
```json
{
  "status": "healthy",
  "message": "API is running",
  "rapidapi_key_configured": true,
  "genius_token_configured": true
}
```

### 2. Recognize Music
**Endpoint:** `POST /api/recognize`

**Content-Type:** `multipart/form-data`

**Parameters:**
- `audio` (required): File audio (mp3, wav, m4a, ogg, flac, aac)
- `get_lyrics` (optional): "true" atau "false" (default: false)

**Response Sukses:**
```json
{
  "success": true,
  "song": {
    "title": "Judul Lagu",
    "artist": "Nama Artis",
    "album": "Nama Album",
    "release_date": "2024",
    "cover_art": "https://...",
    "shazam_url": "https://...",
    "preview_url": "https://..."
  },
  "lyrics": {
    "success": true,
    "lyrics_url": "https://genius.com/...",
    "genius_id": 12345,
    "full_title": "Judul by Artis",
    "artist_names": "Nama Artis",
    "song_art_image": "https://..."
  }
}
```

**Response Error:**
```json
{
  "success": false,
  "error": "Deskripsi error"
}
```

## 🧪 Testing dengan cURL

### Test Health Check
```bash
curl http://localhost:5000/api/health
```

### Test Recognize (tanpa lirik)
```bash
curl -X POST http://localhost:5000/api/recognize \
  -F "audio=@path/to/your/audio.mp3"
```

### Test Recognize (dengan lirik)
```bash
curl -X POST http://localhost:5000/api/recognize \
  -F "audio=@path/to/your/audio.mp3" \
  -F "get_lyrics=true"
```

## 🧪 Testing dengan Postman

1. Buka Postman
2. Buat request baru: **POST** `http://localhost:5000/api/recognize`
3. Pilih tab **Body**
4. Pilih **form-data**
5. Tambahkan key:
   - Key: `audio`, Type: **File**, Value: pilih file audio Anda
   - Key: `get_lyrics`, Type: **Text**, Value: `true` (opsional)
6. Klik **Send**

## 🔧 Testing dengan Python

```python
import requests

url = "http://localhost:5000/api/recognize"

# Buka file audio
with open("test_audio.mp3", "rb") as audio_file:
    files = {"audio": audio_file}
    data = {"get_lyrics": "true"}
    
    response = requests.post(url, files=files, data=data)
    print(response.json())
```

## 📱 Integrasi dengan Flutter

Dari Flutter, Anda bisa menggunakan package `http` atau `dio`:

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

Future<Map<String, dynamic>> recognizeSong(String audioFilePath) async {
  var request = http.MultipartRequest(
    'POST',
    Uri.parse('http://YOUR_IP:5000/api/recognize'),
  );
  
  // Tambahkan file audio
  request.files.add(
    await http.MultipartFile.fromPath('audio', audioFilePath)
  );
  
  // Tambahkan parameter get_lyrics
  request.fields['get_lyrics'] = 'true';
  
  var response = await request.send();
  var responseData = await response.stream.bytesToString();
  
  return json.decode(responseData);
}
```

**Catatan:** Ganti `YOUR_IP` dengan IP address komputer Anda di network yang sama (jangan pakai localhost jika test di device fisik).

## 🐛 Troubleshooting

### Error: "Module not found"
Pastikan semua dependencies sudah terinstall:
```bash
pip install -r requirements.txt
```

### Error: API Keys tidak dikonfigurasi
Cek file `app.py` dan pastikan API keys sudah diisi dengan benar (tidak ada "YOUR_..._HERE")

### Error: "Connection refused" dari Flutter
- Pastikan server berjalan
- Jika test di emulator, gunakan `10.0.2.2:5000` (Android) atau `localhost:5000` (iOS)
- Jika test di device fisik, gunakan IP address komputer Anda

### Error: File size too large
Default max size adalah 10MB. Ubah di file `app.py` baris 16:
```python
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
```

## 📝 Catatan Penting

1. **Genius API Limitations**: Genius API tidak menyediakan full lyrics secara langsung. API hanya memberikan URL ke halaman Genius. Untuk mendapatkan lirik lengkap, Anda perlu:
   - Web scraping dari lyrics_url (memerlukan library seperti BeautifulSoup)
   - Atau gunakan API lirik lain seperti Lyrics.ovh atau Musixmatch

2. **Rate Limits**: 
   - Shazam Free Tier: 500 requests/bulan
   - Genius Free Tier: Unlimited tapi ada rate limiting

3. **Audio Quality**: Untuk hasil terbaik, pastikan audio memiliki kualitas yang baik dan tidak terlalu banyak noise.

## 🔒 Keamanan

Untuk production:
1. Jangan commit API keys ke Git (gunakan environment variables)
2. Tambahkan rate limiting
3. Implement authentication
4. Gunakan HTTPS
5. Validate dan sanitize input

## 📞 Support

Jika ada pertanyaan atau masalah, silakan hubungi developer.

---

**Dibuat dengan ❤️ menggunakan Flask dan Claude**