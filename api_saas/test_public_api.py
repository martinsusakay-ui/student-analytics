# test_public_api.py
"""
Test koneksi ke SampleAPIs (public API, tanpa auth).
Jalankan: python test_public_api.py
"""
import requests
import json


def test_endpoint(url, label, limit=2):
    print(f"\n=== {label} ===")
    print(f"URL: {url}")
    try:
        r = requests.get(url, timeout=15)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            # Kalau list, tampilkan beberapa item pertama
            if isinstance(data, list):
                print(f"Total item: {len(data)}")
                print(f"Contoh {limit} item pertama:")
                print(json.dumps(data[:limit], indent=2)[:800])
            elif isinstance(data, dict):
                print("Contoh isi (dict):")
                print(json.dumps(data, indent=2)[:800])
            return data
        else:
            print(f"Body: {r.text[:300]}")
    except requests.exceptions.Timeout:
        print("⚠️ Timeout — server sibuk atau tidak merespons.")
    except requests.exceptions.ConnectionError:
        print("⚠️ Connection error — cek koneksi internet.")
    except Exception as e:
        print(f"⚠️ Error: {type(e).__name__}: {e}")
    return None


if __name__ == "__main__":
    # Endpoint utama yang Anda coba
    test_endpoint(
        "https://api.sampleapis.com/futurama/characters",
        "Futurama Characters",
    )

    # Fallback 1: endpoint SampleAPIs lain
    test_endpoint(
        "https://api.sampleapis.com/coffee/hot",
        "Coffee (Hot)",
    )

    # Fallback 2: public API alternatif yang stabil
    test_endpoint(
        "https://jsonplaceholder.typicode.com/users",
        "JSONPlaceholder - Users",
    )

    test_endpoint(
        "https://jsonplaceholder.typicode.com/posts",
        "JSONPlaceholder - Posts",
    )

    # Fallback 3: API edukasi
    test_endpoint(
        "https://catfact.ninja/facts?limit=2",
        "Cat Facts",
    )

    print("\n✅ Selesai. Kalau salah satu endpoint di atas berhasil (status 200),")
    print("   berarti koneksi internet & library requests Anda sudah OK.")
    print("   Selanjutnya kita bisa pakai endpoint itu untuk test Streamlit.")