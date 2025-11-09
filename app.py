from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import base64
import hashlib
import hmac
import time
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)  # Enable CORS untuk Flutter bisa akses dari mobile

# Konfigurasi
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'ogg', 'flac', 'aac', 'webm'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# ===== LETAKKAN API KEYS ANDA DI SINI =====

# ACRCloud API (untuk music recognition)
# Dapatkan dari: https://console.acrcloud.com
ACRCLOUD_ACCESS_KEY = "dff45393ab2ae47135ed493223c2d50a"
ACRCLOUD_ACCESS_SECRET = "524yGfSoPScMSwANINaNWC210ZywDDEQWnp3d2UT"
ACRCLOUD_HOST = "identify-ap-southeast-1.acrcloud.com"  # Sesuaikan region Anda

# Spotify API (untuk data lagu)
# Dapatkan dari: https://developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID = "20440da8b4824788b442888be722525a"
SPOTIFY_CLIENT_SECRET = "32f4c8f1c99e437d9a0f7d8d35079430"

# Genius API (untuk lirik)
# Dapatkan dari: https://genius.com/api-clients
GENIUS_ACCESS_TOKEN = "8JVvCUjCQgj0MX_4AgURrY1eA-ejQEwzPzdhWoWQ8NAnsy9pd_ygM7D_faZ6nZDX"

# ==========================================

# Buat folder uploads jika belum ada
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Cache untuk Spotify token
spotify_token_cache = {
    'token': None,
    'expires_at': 0
}


def allowed_file(filename):
    """Check apakah file extension diperbolehkan"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_spotify_token():
    """
    Mendapatkan access token dari Spotify API
    Token akan di-cache untuk menghindari request berulang
    """
    # Cek cache
    current_time = time.time()
    if spotify_token_cache['token'] and current_time < spotify_token_cache['expires_at']:
        return spotify_token_cache['token']
    
    # Request token baru
    auth_url = "https://accounts.spotify.com/api/token"
    auth_string = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    auth_bytes = auth_string.encode('utf-8')
    auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
    
    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {"grant_type": "client_credentials"}
    
    try:
        response = requests.post(auth_url, headers=headers, data=data)
        if response.status_code == 200:
            token_data = response.json()
            token = token_data['access_token']
            expires_in = token_data['expires_in']  # dalam detik
            
            # Cache token
            spotify_token_cache['token'] = token
            spotify_token_cache['expires_at'] = current_time + expires_in - 60  # -60 detik buffer
            
            return token
        else:
            return None
    except Exception as e:
        print(f"Error getting Spotify token: {str(e)}")
        return None


def recognize_song_acrcloud(audio_file_path):
    """
    Mengenali lagu menggunakan ACRCloud API
    """
    try:
        # Baca file audio
        with open(audio_file_path, 'rb') as f:
            audio_data = f.read()
        
        # Generate signature untuk ACRCloud
        http_method = "POST"
        http_uri = "/v1/identify"
        data_type = "audio"
        signature_version = "1"
        timestamp = str(int(time.time()))
        
        string_to_sign = http_method + "\n" + http_uri + "\n" + ACRCLOUD_ACCESS_KEY + "\n" + data_type + "\n" + signature_version + "\n" + timestamp
        signature = base64.b64encode(
            hmac.new(
                ACRCLOUD_ACCESS_SECRET.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                digestmod=hashlib.sha1
            ).digest()
        ).decode('utf-8')
        
        # Prepare request
        url = f"https://{ACRCLOUD_HOST}/v1/identify"
        
        files = {
            'sample': audio_data
        }
        
        data = {
            'access_key': ACRCLOUD_ACCESS_KEY,
            'data_type': data_type,
            'signature_version': signature_version,
            'signature': signature,
            'sample_bytes': len(audio_data),
            'timestamp': timestamp
        }
        
        response = requests.post(url, files=files, data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result['status']['code'] == 0:  # Success
                # Parse metadata
                metadata = result['metadata']
                if 'music' in metadata and len(metadata['music']) > 0:
                    music = metadata['music'][0]
                    
                    # Ambil artists
                    artists = music.get('artists', [])
                    artist_name = artists[0]['name'] if artists else 'Unknown Artist'
                    
                    # Ambil album
                    album = music.get('album', {})
                    album_name = album.get('name', 'Unknown Album')
                    
                    return {
                        'success': True,
                        'title': music.get('title', 'Unknown'),
                        'artist': artist_name,
                        'album': album_name,
                        'release_date': music.get('release_date', 'Unknown'),
                        'duration_ms': music.get('duration_ms', 0),
                        'label': music.get('label', 'Unknown'),
                        'isrc': music.get('external_ids', {}).get('isrc', ''),
                        'score': result['status'].get('score', 0)
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Lagu tidak ditemukan di database ACRCloud'
                    }
            else:
                return {
                    'success': False,
                    'error': f"ACRCloud error: {result['status']['msg']}"
                }
        else:
            return {
                'success': False,
                'error': f'ACRCloud API error: {response.status_code}'
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'Error recognizing song: {str(e)}'
        }


def get_spotify_track_info(title, artist):
    """
    Mendapatkan informasi lengkap lagu dari Spotify API
    """
    token = get_spotify_token()
    if not token:
        return {
            'success': False,
            'error': 'Gagal mendapatkan Spotify token'
        }
    
    # Search track di Spotify
    search_url = "https://api.spotify.com/v1/search"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    params = {
        "q": f"track:{title} artist:{artist}",
        "type": "track",
        "limit": 1
    }
    
    try:
        response = requests.get(search_url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            if data['tracks']['items']:
                track = data['tracks']['items'][0]
                track_id = track['id']
                
                # Get audio features
                features_url = f"https://api.spotify.com/v1/audio-features/{track_id}"
                features_response = requests.get(features_url, headers=headers)
                
                audio_features = {}
                if features_response.status_code == 200:
                    features_data = features_response.json()
                    audio_features = {
                        'danceability': features_data.get('danceability', 0),
                        'energy': features_data.get('energy', 0),
                        'valence': features_data.get('valence', 0),
                        'tempo': features_data.get('tempo', 0),
                        'key': features_data.get('key', 0),
                        'mode': features_data.get('mode', 0)
                    }
                
                # Parse track info
                album = track['album']
                artists_list = [artist['name'] for artist in track['artists']]
                
                return {
                    'success': True,
                    'spotify_id': track_id,
                    'title': track['name'],
                    'artists': artists_list,
                    'album': album['name'],
                    'release_date': album.get('release_date', 'Unknown'),
                    'popularity': track.get('popularity', 0),
                    'duration_ms': track.get('duration_ms', 0),
                    'preview_url': track.get('preview_url', ''),
                    'spotify_url': track['external_urls'].get('spotify', ''),
                    'cover_art': album['images'][0]['url'] if album['images'] else '',
                    'audio_features': audio_features
                }
            else:
                return {
                    'success': False,
                    'error': 'Lagu tidak ditemukan di Spotify'
                }
        else:
            return {
                'success': False,
                'error': f'Spotify API error: {response.status_code}'
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'Error fetching Spotify data: {str(e)}'
        }


def get_lyrics_genius(song_title, artist_name):
    """
    Mendapatkan lirik lagu dari Genius API
    """
    search_url = "https://api.genius.com/search"
    headers = {
        "Authorization": f"Bearer {GENIUS_ACCESS_TOKEN}"
    }
    params = {
        "q": f"{song_title} {artist_name}"
    }
    
    try:
        response = requests.get(search_url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            if data['response']['hits']:
                song_info = data['response']['hits'][0]['result']
                
                return {
                    'success': True,
                    'lyrics_url': song_info.get('url', ''),
                    'genius_id': song_info.get('id', ''),
                    'full_title': song_info.get('full_title', ''),
                    'artist_names': song_info.get('artist_names', ''),
                    'song_art_image': song_info.get('song_art_image_url', ''),
                    'note': 'Genius API tidak menyediakan lirik langsung. Gunakan lyrics_url untuk web scraping atau gunakan API lirik lain.'
                }
            else:
                return {
                    'success': False,
                    'error': 'Lirik tidak ditemukan di Genius'
                }
        else:
            return {
                'success': False,
                'error': f'Genius API error: {response.status_code}'
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'Error fetching lyrics: {str(e)}'
        }


@app.route('/')
def home():
    """Homepage dengan dokumentasi API"""
    return jsonify({
        'message': 'Music Recognition API - Powered by ACRCloud + Spotify + Genius',
        'version': '2.0',
        'endpoints': {
            '/': 'Dokumentasi API',
            '/api/recognize': 'POST - Upload audio file untuk dikenali',
            '/api/search': 'GET - Search lagu di Spotify (by title/artist)',
            '/api/health': 'GET - Cek status API'
        },
        'usage': {
            'recognize': {
                'method': 'POST',
                'endpoint': '/api/recognize',
                'content_type': 'multipart/form-data',
                'parameters': {
                    'audio': 'Audio file (mp3, wav, m4a, ogg, flac, aac)',
                    'get_lyrics': 'Optional boolean (true/false) untuk mendapatkan lirik',
                    'use_spotify': 'Optional boolean (true/false) untuk mendapatkan data dari Spotify'
                },
                'example_response': {
                    'success': True,
                    'recognition': {
                        'source': 'ACRCloud',
                        'title': 'Song Title',
                        'artist': 'Artist Name'
                    },
                    'spotify': {
                        'preview_url': 'URL',
                        'popularity': 85,
                        'audio_features': {}
                    },
                    'lyrics': {
                        'lyrics_url': 'URL to Genius page'
                    }
                }
            },
            'search': {
                'method': 'GET',
                'endpoint': '/api/search?q=song+name+artist',
                'description': 'Search lagu di Spotify tanpa upload audio'
            }
        }
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint untuk cek status API"""
    return jsonify({
        'status': 'healthy',
        'message': 'API is running',
        'acrcloud_configured': bool(ACRCLOUD_ACCESS_KEY != "YOUR_ACRCLOUD_ACCESS_KEY_HERE"),
        'spotify_configured': bool(SPOTIFY_CLIENT_ID != "YOUR_SPOTIFY_CLIENT_ID_HERE"),
        'genius_configured': bool(GENIUS_ACCESS_TOKEN != "YOUR_GENIUS_ACCESS_TOKEN_HERE")
    })


@app.route('/api/search', methods=['GET'])
def search_music():
    """
    Endpoint untuk search lagu di Spotify (tanpa upload audio)
    Query parameter: q (judul lagu atau artist)
    """
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Parameter q (query) tidak boleh kosong'
        }), 400
    
    token = get_spotify_token()
    if not token:
        return jsonify({
            'success': False,
            'error': 'Gagal mendapatkan Spotify token'
        }), 500
    
    # Search di Spotify
    search_url = "https://api.spotify.com/v1/search"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    params = {
        "q": query,
        "type": "track",
        "limit": 10
    }
    
    try:
        response = requests.get(search_url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            tracks = []
            
            for track in data['tracks']['items']:
                album = track['album']
                artists_list = [artist['name'] for artist in track['artists']]
                
                tracks.append({
                    'spotify_id': track['id'],
                    'title': track['name'],
                    'artists': artists_list,
                    'album': album['name'],
                    'release_date': album.get('release_date', 'Unknown'),
                    'popularity': track.get('popularity', 0),
                    'preview_url': track.get('preview_url', ''),
                    'spotify_url': track['external_urls'].get('spotify', ''),
                    'cover_art': album['images'][0]['url'] if album['images'] else ''
                })
            
            return jsonify({
                'success': True,
                'query': query,
                'total': len(tracks),
                'tracks': tracks
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': f'Spotify API error: {response.status_code}'
            }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error searching: {str(e)}'
        }), 500


@app.route('/api/recognize', methods=['POST'])
def recognize_music():
    """
    Endpoint utama untuk mengenali musik dari audio file
    """
    # Cek apakah file ada dalam request
    if 'audio' not in request.files:
        return jsonify({
            'success': False,
            'error': 'Tidak ada file audio dalam request'
        }), 400
    
    file = request.files['audio']
    
    # Cek apakah user memilih file
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'Tidak ada file yang dipilih'
        }), 400
    
    # Cek apakah file extension valid
    if not allowed_file(file.filename):
        return jsonify({
            'success': False,
            'error': f'Format file tidak didukung. Gunakan: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400
    
    # Cek parameter
    get_lyrics = request.form.get('get_lyrics', 'false').lower() == 'true'
    use_spotify = request.form.get('use_spotify', 'true').lower() == 'true'
    
    try:
        # Simpan file sementara
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Recognize lagu dengan ACRCloud
        recognition_result = recognize_song_acrcloud(filepath)
        
        # Hapus file setelah diproses
        os.remove(filepath)
        
        if not recognition_result['success']:
            return jsonify(recognition_result), 404
        
        # Response data
        response_data = {
            'success': True,
            'recognition': {
                'source': 'ACRCloud',
                'title': recognition_result['title'],
                'artist': recognition_result['artist'],
                'album': recognition_result['album'],
                'release_date': recognition_result['release_date'],
                'duration_ms': recognition_result['duration_ms'],
                'label': recognition_result['label'],
                'score': recognition_result['score']
            }
        }
        
        # Ambil data dari Spotify jika diminta
        if use_spotify:
            spotify_result = get_spotify_track_info(
                recognition_result['title'],
                recognition_result['artist']
            )
            response_data['spotify'] = spotify_result
        
        # Ambil lirik dari Genius jika diminta
        if get_lyrics:
            lyrics_result = get_lyrics_genius(
                recognition_result['title'],
                recognition_result['artist']
            )
            response_data['lyrics'] = lyrics_result
        
        return jsonify(response_data), 200
    
    except Exception as e:
        # Hapus file jika ada error
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
        
        return jsonify({
            'success': False,
            'error': f'Terjadi kesalahan: {str(e)}'
        }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("Music Recognition API v2.0")
    print("Powered by ACRCloud + Spotify + Genius")
    print("=" * 60)
    print(f"Server berjalan di: http://localhost:5000")
    print(f"Dokumentasi API: http://localhost:5000")
    print(f"Health Check: http://localhost:5000/api/health")
    print("=" * 60)
    
    # Peringatan jika API keys belum diisi
    if ACRCLOUD_ACCESS_KEY == "YOUR_ACRCLOUD_ACCESS_KEY_HERE":
        print("⚠️  WARNING: ACRCloud Access Key belum diisi!")
    if SPOTIFY_CLIENT_ID == "YOUR_SPOTIFY_CLIENT_ID_HERE":
        print("⚠️  WARNING: Spotify Client ID belum diisi!")
    if GENIUS_ACCESS_TOKEN == "YOUR_GENIUS_ACCESS_TOKEN_HERE":
        print("⚠️  WARNING: Genius Access Token belum diisi!")
    
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)