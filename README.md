# Mapa Planes 🐧🦖

A modern web application for creating and managing a personal, interactive map of places to visit or places already visited. Built with Python 3.11+, FastAPI, Folium, Supabase, and OpenCage.

## Features

- **User Authentication:** Secure signup, login, and logout using Supabase Auth. User-specific data access is enforced by Row Level Security (RLS) via Supabase.
- **Place Management:**
  - Create new places with name, category (Restaurant, Park, etc.), and status (Pending, Prioritized).
  - Add location via geocoding address/name or by pinning directly on a map.
  - View personal places as markers on an interactive map (Folium/Leaflet).
  - Update place details, category, and status.
  - Mark places as 'Visited', add reviews, ratings (1-5 stars), and upload images.
  - Soft delete places (removes from view while maintaining DB records; associated images are deleted from storage).
- **Interactive Map:**
  - Markers colored by status and iconed by category.
  - Interactive popups for details, status updates, editing, and review management.
  - Filter markers by category and/or status.
  - Automatic map centering based on markers.
- **Calendar Integration:** ics-based export for visits, allowing users to add planned visits to their personal calendars with customizable reminders and timezone support.
- **Automatic Timezone Detection:** Uses `timezonefinder` to automatically determine the IANA timezone of a place based on its coordinates, ensuring accurate calendar events.
- **Geocoding:** Uses OpenCage Geocoder API to convert addresses/place names into coordinates.
- **Image Handling:** Upload and manage place images using Supabase Storage.
- **Free Tier Focused:** Designed to run primarily on free services (Supabase, OpenCage free tier).

## Tech Stack

- **Backend:** Python 3.11+, FastAPI (Asynchronous)
- **Authentication & Database:** Supabase (Auth, PostgreSQL, Storage) with Async Client
- **Mapping:** Folium / Leaflet.js
- **Geocoding:** OpenCage Geocoder API
- **Frontend:** HTML (Jinja2), Vanilla JavaScript (Modular), CSS3
- **Dev Tools:** Ruff (Linting & Formatting)
- **Key Dependencies:** `pydantic-settings`, `timezonefinder`, `ics`, `python-jose`, `passlib`, `python-dotenv`.

## Project Structure

```text
└── ./
    ├── app/                    # Main application module
    │   ├── auth/               # Authentication logic & dependencies
    │   ├── core/               # Configuration & settings
    │   ├── crud/               # Database operations (CRUD)
    │   ├── db/                 # Database initialization (Async Supabase)
    │   ├── models/             # Pydantic models for validation
    │   ├── routers/            # FastAPI routers (API & Pages)
    │   ├── services/           # Business logic (Geocoding, Mapping, Timezones)
    │   ├── main.py             # Entry point
    │   └── middleware.py       # Custom middleware
    ├── static/                 # Static assets (CSS, JS)
    ├── templates/              # Jinja2 HTML templates
    ├── .env.example            # Environment template
    ├── pyproject.toml          # Tooling configuration (Ruff)
    ├── README.md               # This file
    └── requirements.txt        # Dependencies
```

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <repository-folder>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    venv\Scripts\activate  # Windows
    # source venv/bin/activate  # Linux/macOS
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    -   Copy `.env.example` to `.env`.
    -   \*\*Supabase:\*\* Sign up for a free Supabase account ([supabase.com](https://supabase.com/)). Create a new project.
        -   Navigate to \*\*Project Settings > API\*\*. Copy the `Project URL` and `anon public` key into `SUPABASE_URL` and `SUPABASE_KEY` in your `.env` file.
        -   \*\*Required:\*\* Copy the `service_role secret` key into `SUPABASE_SERVICE_ROLE_KEY`. \*\*Keep this key secure!\*\* It is used for administrative tasks like deleting images from storage.
        -   In the Supabase Dashboard:
            -   Go to the \*\*SQL Editor\*\* and run the necessary SQL to create the `places` and `visits` tables and enable Row Level Security (RLS). You'll need to set RLS policies to ensure users can only access their own data.
            -   Go to \*\*Storage\*\*. Create a new \*\*public\*\* bucket named exactly `place-images`.
            -   Configure \*\*Storage Policies\*\* (RLS for Storage) to allow authenticated users to upload (`insert`) and delete (`delete`) objects within their user-specific folder path (e.g., `places/{user_id}/*`), and allow public read access for viewing images.
    -   \*\*OpenCage:\*\* Sign up for a free OpenCage Geocoder account ([opencagedata.com](https://opencagedata.com/)). Get your API key and add it to `OPENCAGE_API_KEY` in `.env`.
    -   \*\*SECRET_KEY:\*\* Generate a strong secret key (e.g., `openssl rand -hex 32`) and replace the default value in `SECRET_KEY`.
    -   \*\*CORS:\*\* Adjust `BACKEND_CORS_ORIGINS` for production if needed. `["*"]` is okay for local development.

## Development

This project uses **Ruff** for linting and formatting.

-   **Check for linting issues:**
    ```bash
    ruff check .
    ```
-   **Apply automatic fixes:**
    ```bash
    ruff check . --fix
    ```
-   **Format code:**
    ```bash
    ruff format .
    ```

## Running Locally

Ensure `APP_ENV` is set to `development` in your `.env`.

Start the development server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Visit http://localhost:8000.

## Deployment Notes

This application can be deployed to platforms supporting Python ASGI applications (like Render, Fly.io, Heroku, etc.).

- Ensure all required environment variables (.env content) are set on the deployment platform.
- Set `APP_ENV=production` in the production environment.
- Make sure `BACKEND_CORS_ORIGINS` is configured correctly for your production frontend URL.
- Use a production-grade ASGI server like Uvicorn with Gunicorn workers.
