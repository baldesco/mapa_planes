# Mapa Planes

A simple web application to keep track of places you want to visit or have visited, displayed on an interactive map. Built with Python, FastAPI, Folium, and Supabase.

## Features

- Add new places with name and category.
- Geocode addresses/names to automatically get coordinates and address details (using Nominatim/OpenStreetMap).
- Display all places as markers on a Leaflet map (via Folium).
- Filter places shown on the map by category and visit status.
- Mark places as "Pending", "Pending Prioritized", or "Visited".
- Update status directly from the map popup.
- (Basic UI for) Add a text review and upload an image for visited places.
- Store data in a cloud PostgreSQL database (Supabase free tier).
- Store images in cloud object storage (Supabase Storage free tier).
- Option for local development using SQLite.

## Tech Stack

- **Backend:** Python 3.10+, FastAPI
- **Frontend:** HTML (Jinja2 Templating via FastAPI), minimal JavaScript, CSS
- **Mapping:** Folium (Python wrapper for Leaflet.js)
- **Geocoding:** Geopy library with Nominatim (OpenStreetMap data)
- **Cloud Database:** Supabase (PostgreSQL)
- **Cloud Storage:** Supabase Storage
- **Local Database:** SQLite (via SQLAlchemy)
- **Deployment:** Render (Free Tier)

## Setup

1.  **Clone the repository:**

    ```bash
    git clone <your-repo-url>
    cd mapa_planes
    ```

2.  **Create and activate a virtual environment:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    # venv\Scripts\activate  # Windows
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**

    - Copy `.env.example` to `.env`.
    - **Crucially:** Update `GEOCODING_USER_AGENT` in `.env` with a unique identifier and your email address as required by Nominatim's usage policy.
    - Set `APP_ENV` to `development` for local testing.
    - Update `DATABASE_URL` if you want a different SQLite file path.
    - (Optional for Cloud) Sign up for Supabase, create a project, and fill in `SUPABASE_URL`, `SUPABASE_KEY`. Create the `places` table using the SQL schema provided in the Supabase setup guide/comments. Create a public Storage bucket named `place-images` (or match `SUPABASE_BUCKET_NAME`) and set appropriate read/write policies.

5.  **Initialize Local Database (if using SQLite):**
    Run the database script directly to create the `.db` file and tables:
    ```bash
    python app/database.py
    ```

## Running Locally

Ensure `APP_ENV` is set to `development` in your `.env` file.

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
