# app.py
import streamlit as st
import pandas as pd
from api_client import PublicAPIClient

st.set_page_config(
    page_title="Public API Dashboard",
    page_icon="📊",
    layout="wide",
)

if "client" not in st.session_state:
    st.session_state.client = PublicAPIClient()

client = st.session_state.client

st.title("📊 Dashboard Data dari Public API")
st.caption("Verifikasi alur: panggil API → parsing JSON → tampilkan di Streamlit")

# ---------- SIDEBAR ----------
with st.sidebar:
    st.header("⚙️ Pilih Sumber Data")
    source = st.radio(
        "Endpoint:",
        [
            "Futurama Characters",
            "Coffee (Hot)",
            "JSONPlaceholder - Users",
            "JSONPlaceholder - Posts",
            "Cat Facts",
        ],
    )
    st.divider()
    st.markdown("**Status:** semua endpoint publik, tanpa auth.")

# ---------- FETCH DATA ----------
status = None
data = None

if source == "Futurama Characters":
    status, data = client.get_futurama_characters()
elif source == "Coffee (Hot)":
    status, data = client.get_coffee_hot()
elif source == "JSONPlaceholder - Users":
    status, data = client.get_jsonplaceholder_users()
elif source == "JSONPlaceholder - Posts":
    status, data = client.get_jsonplaceholder_posts()
elif source == "Cat Facts":
    status, data = client.get_cat_facts(limit=20)

# ---------- TAMPILKAN ----------
if status != 200:
    st.error(f"Gagal ambil data. Status: {status}")
    st.json(data)
    st.stop()

st.success(f"Berhasil ambil data dari **{source}**")

# ============================================================
# FUTURAMA CHARACTERS
# ============================================================
if source == "Futurama Characters" and isinstance(data, list):

    def extract_name(name_field):
        """Handle dua format: dict {first,middle,last} atau str langsung."""
        if isinstance(name_field, dict):
            return " ".join(filter(None, [
                str(name_field.get("first", "") or ""),
                str(name_field.get("middle", "") or ""),
                str(name_field.get("last", "") or ""),
            ])).strip()
        elif isinstance(name_field, str):
            return name_field
        return ""

    rows = []
    for c in data:
        if not isinstance(c, dict):
            continue
        rows.append({
            "Nama": extract_name(c.get("name")),
            "Gender": c.get("gender"),
            "Species": c.get("species"),
            "Home Planet": c.get("homePlanet"),
            "Occupation": c.get("occupation"),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    # Filter species (hanya kalau kolom tidak kosong semua)
    species_valid = df["Species"].dropna().unique().tolist()
    if species_valid:
        species_list = ["Semua"] + sorted([str(s) for s in species_valid])
        pilihan = st.selectbox("Filter Species:", species_list)
        if pilihan != "Semua":
            st.dataframe(df[df["Species"] == pilihan], use_container_width=True)

    # Detail karakter
    st.subheader("Detail Karakter")
    if not df.empty:
        nama_pilih = st.selectbox("Pilih karakter:", df["Nama"].tolist())
        detail = None
        for c in data:
            if isinstance(c, dict) and extract_name(c.get("name")) == nama_pilih:
                detail = c
                break
        if detail:
            st.json(detail)

# ============================================================
# COFFEE (HOT)
# ============================================================
elif source == "Coffee (Hot)" and isinstance(data, list):
    rows = []
    for c in data:
        if not isinstance(c, dict):
            continue
        ingredients = c.get("ingredients", [])
        if not isinstance(ingredients, list):
            ingredients = [str(ingredients)]
        rows.append({
            "ID": c.get("id"),
            "Nama": c.get("title"),
            "Bahan": ", ".join([str(i) for i in ingredients]),
            "Deskripsi": (str(c.get("description") or ""))[:120] + "...",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    # Grid gambar
    st.subheader("Preview")
    cols = st.columns(4)
    for i, c in enumerate([x for x in data if isinstance(x, dict)][:8]):
        with cols[i % 4]:
            st.markdown(f"**{c.get('title', '-')}**")
            if c.get("image"):
                try:
                    st.image(c["image"], use_container_width=True)
                except Exception:
                    st.caption("(gambar gagal dimuat)")

# ============================================================
# JSONPLACEHOLDER - USERS
# ============================================================
elif source == "JSONPlaceholder - Users" and isinstance(data, list):
    rows = []
    for u in data:
        if not isinstance(u, dict):
            continue
        address = u.get("address") or {}
        company = u.get("company") or {}
        rows.append({
            "ID": u.get("id"),
            "Nama": u.get("name"),
            "Username": u.get("username"),
            "Email": u.get("email"),
            "Kota": address.get("city") if isinstance(address, dict) else None,
            "Perusahaan": company.get("name") if isinstance(company, dict) else None,
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    if not df.empty:
        st.subheader("Jumlah per Kota")
        kota_counts = df["Kota"].value_counts()
        st.bar_chart(kota_counts)

# ============================================================
# JSONPLACEHOLDER - POSTS
# ============================================================
elif source == "JSONPlaceholder - Posts" and isinstance(data, list):
    df = pd.DataFrame([p for p in data if isinstance(p, dict)])
    st.dataframe(df, use_container_width=True)

    if not df.empty and "userId" in df.columns:
        st.subheader("Filter by User")
        user_ids = sorted(df["userId"].dropna().unique().tolist())
        uid = st.selectbox("User ID:", user_ids)
        st.dataframe(df[df["userId"] == uid], use_container_width=True)

# ============================================================
# CAT FACTS
# ============================================================
elif source == "Cat Facts" and isinstance(data, dict):
    facts = data.get("data", [])
    df = pd.DataFrame(facts)
    st.dataframe(df, use_container_width=True)

    if not df.empty and "length" in df.columns and "fact" in df.columns:
        st.subheader("10 Fakta Terpanjang")
        top10 = df.sort_values("length", ascending=False).head(10)
        st.bar_chart(top10.set_index("fact")["length"])

else:
    # Fallback: tampilkan raw JSON kalau struktur tidak dikenali
    st.warning("Struktur data tidak dikenali. Menampilkan raw JSON:")
    st.json(data)