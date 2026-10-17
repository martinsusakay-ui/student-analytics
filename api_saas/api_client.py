# api_client.py
import requests


class PublicAPIClient:
    """
    Client untuk mengakses public API (tanpa auth).
    Cocok untuk testing sebelum pakai API LMS asli.
    """

    def get_futurama_characters(self):
        url = "https://api.sampleapis.com/futurama/characters"
        r = requests.get(url, timeout=15)
        return r.status_code, self._safe_json(r)

    def get_coffee_hot(self):
        url = "https://api.sampleapis.com/coffee/hot"
        r = requests.get(url, timeout=15)
        return r.status_code, self._safe_json(r)

    def get_jsonplaceholder_users(self):
        url = "https://jsonplaceholder.typicode.com/users"
        r = requests.get(url, timeout=15)
        return r.status_code, self._safe_json(r)

    def get_jsonplaceholder_posts(self):
        url = "https://jsonplaceholder.typicode.com/posts"
        r = requests.get(url, timeout=15)
        return r.status_code, self._safe_json(r)

    def get_cat_facts(self, limit=10):
        url = f"https://catfact.ninja/facts?limit={limit}"
        r = requests.get(url, timeout=15)
        return r.status_code, self._safe_json(r)

    @staticmethod
    def _safe_json(r):
        try:
            return r.json()
        except Exception:
            return {"raw_text": r.text}