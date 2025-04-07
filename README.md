# Mapa Planes 🐧🦖

A web application for creating and managing a personal, interactive map of places to visit or places already visited. Built with Python, FastAPI, Folium, Supabase, and OpenCage.

## Features

- **User Authentication:** Secure signup, login, and logout using Supabase Auth. User-specific data access enforced by Row Level Security (RLS) via Supabase.
- **Place Management:**
  - Create new places with name, category (Restaurant, Park, etc.), and initial status (Pending, Prioritized).
  - Add location via geocoding address/name or by pinning directly on a map.
  - View all personal places displayed as markers on an interactive map (Folium/Leaflet).
  - Update place details (name, category, location, status).
  - Mark places as 'Visited' and add reviews, ratings (1-5 stars), and upload an associated image.
  - Soft delete places (removes from view but kept in DB, associated image deleted from storage).
- **Interactive Map:**
  - Displays markers colored by status and iconed by category.
  - Click markers to view details, update status, edit, add/view review, or delete the place via popup forms/buttons.
  - Filter displayed markers by category and/or status.
  - Map automatically centers based on displayed markers.
- **Geocoding:** Uses OpenCage Geocoder API to convert addresses/place names into latitude/longitude coordinates.
- **Image Handling:** Upload place images to Supabase Storage (free tier object storage). View images in modals, remove images.
- **Free Tier Focused:** Designed to primarily use free services (Supabase, OpenCage free tier, potential deployment on free tiers like Render/Fly.io).

## Tech Stack

- **Backend:** Python 3.10+, FastAPI
- **Authentication:** Supabase Auth
- **Database:** Supabase (PostgreSQL)
- **Storage:** Supabase Storage
- **Mapping:** Folium (Python wrapper for Leaflet.js)
- **Geocoding:** OpenCage Geocoder API
- **Frontend:** HTML (Jinja2 Templating), Vanilla JavaScript (Modular), CSS3
- **Dependencies:** Pydantic (for data validation), Uvicorn (ASGI server), python-jose (JWT handling), python-dotenv & pydantic-settings (config).

## Project Structure

``
└── ./
├── app/ # Main application module
│ ├── auth/ # Authentication logic, dependencies, utils
│ ├── core/ # Configuration, core settings
│ ├── crud/ # Database Create, Read, Update, Delete operations
│ ├── db/ # Database setup and client generation
│ ├── models/ # Pydantic models for data validation & structure
│ ├── routers/ # FastAPI routers for API endpoints and HTML pages/forms
│ ├── services/ # Business logic services (Geocoding, Mapping)
│ ├── init.py
│ ├── main.py # FastAPI application entry point
│ └── middleware.py # Custom middleware (e.g., Auth redirects)
├── static/ # Frontend static assets
│ ├── css/
│ └── js/
├── templates/ # Jinja2 HTML templates
├── .env.example # Example environment variables file
├── .gitignore
├── README.md # This file
└── requirements.txt # Python dependencies

````


## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <repository-folder>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    # venv\Scripts\activate    # Windows
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    -   Copy `.env.example` to `.env`.
    -   **Supabase:** Sign up for a free Supabase account ([supabase.com](https://supabase.com/)). Create a new project.
        -   Navigate to Project Settings > API. Copy the `Project URL` and `anon public` key into `SUPABASE_URL` and `SUPABASE_KEY` in your `.env` file.
        -   (Optional but Recommended for Deletes) Also copy the `service_role secret` key into `SUPABASE_SERVICE_ROLE_KEY`. **Keep this key secure!**
        -   In the Supabase Dashboard:
            -   Go to the SQL Editor and run the necessary SQL to create the `places` table and enable Row Level Security (RLS). You'll need to define the table schema (columns like `id`, `user_id`, `name`, `latitude`, `longitude`, `category`, `status`, etc.) and set RLS policies to ensure users can only access their own data. *A `schema.sql` file should ideally be added to the repo.*
            -   Go to Storage. Create a new **public** bucket named exactly as specified in `SUPABASE_BUCKET_NAME` (default: `place-images`).
            -   Configure Storage Policies (RLS for Storage) to allow authenticated users to upload (`insert`) and delete (`delete`) objects within their user-specific folder path (e.g., `places/{user_id}/*`), and allow public read access if desired for viewing images.
    -   **OpenCage:** Sign up for a free OpenCage Geocoder account ([opencagedata.com](https://opencagedata.com/)). Get your API key and add it to `OPENCAGE_API_KEY` in `.env`.
    -   **SECRET_KEY:** Generate a strong secret key (e.g., `openssl rand -hex 32`) and replace the default value in `SECRET_KEY`.
    -   **CORS:** Adjust `BACKEND_CORS_ORIGINS` for production if needed. `["*"]` is okay for local development.

5.  **Database Schema:**
    -   Ensure the `places` table is created in your Supabase database with the correct columns and types matching the Pydantic models in `app/models/places.py`.
    -   Ensure appropriate Row Level Security (RLS) policies are enabled on the `places` table in Supabase to restrict access based on `user_id`.

## Running Locally

Ensure `APP_ENV` is set to `development` in your `.env` file.

Start the FastAPI development server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
````

Navigate to http://localhost:8000 in your browser.
Deployment (Notes)
This application can be deployed to platforms supporting Python ASGI applications (like Render, Fly.io, Heroku, etc.).
Ensure all required environment variables (.env content) are set on the deployment platform.
Set APP_ENV=production in the production environment.
Make sure BACKEND_CORS_ORIGINS is configured correctly for your production frontend URL.
Use a production-grade ASGI server like Uvicorn with Gunicorn workers.
