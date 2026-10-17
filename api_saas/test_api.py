# test_api.py
import requests
from config import BASE_URL

EMAIL = "test_streamlit@example.com"
PASSWORD = "Test1234!"

print("=== 1. ROOT ===")
r = requests.get(f"{BASE_URL}/")
print(r.status_code, r.text[:200])

print("\n=== 2. /courses (no auth) ===")
r = requests.get(f"{BASE_URL}/courses")
print(r.status_code, r.text[:300])

print("\n=== 3. REGISTER ===")
r = requests.post(f"{BASE_URL}/auth/register", json={
    "email": EMAIL,
    "password": PASSWORD,
    "full_name": "Test Streamlit",
})
print(r.status_code, r.text[:300])

print("\n=== 4. LOGIN (JSON) ===")
r = requests.post(f"{BASE_URL}/auth/login", json={
    "email": EMAIL,
    "password": PASSWORD,
})
print(r.status_code, r.text[:300])

print("\n=== 5. LOGIN (form-urlencoded) ===")
r = requests.post(f"{BASE_URL}/auth/login", data={
    "username": EMAIL,
    "password": PASSWORD,
})
print(r.status_code, r.text[:300])

token = None
try:
    token = r.json().get("access_token")
except Exception:
    pass

if token:
    headers = {"Authorization": f"Bearer {token}"}
    print("\n=== 6. /users/me ===")
    r = requests.get(f"{BASE_URL}/users/me", headers=headers)
    print(r.status_code, r.text[:300])

    print("\n=== 7. /courses (auth) ===")
    r = requests.get(f"{BASE_URL}/courses", headers=headers)
    print(r.status_code, r.text[:300])
else:
    print("\n⚠️ Tidak dapat token, skip endpoint protected.")