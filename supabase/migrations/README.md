# Supabase Migrations

This directory contains SQL migration files to manage the database schema of the **Mapa de Planes** application. Following Supabase best practices, we use migrations to keep the database in sync across different environments.

## Prerequisite: Supabase CLI

To manage migrations, you need the Supabase CLI installed on your machine.

### Installation

If you haven't installed it yet, follow the instructions for your OS:

- **Windows (using Scoop or Powershell):**
  ```powershell
  # Using Scoop
  scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
  scoop install supabase

  # Or using NPM (Global)
  npm install supabase --save-dev
  ```
- **macOS/Linux:**
  ```bash
  brew install supabase/tap/supabase
  ```

For more details, visit the [official Supabase CLI documentation](https://supabase.com/docs/guides/cli/getting-started).

## Setting up the CLI

1.  **Login to Supabase:**
    ```bash
    npx supabase login
    ```
2.  **Initialize Supabase in the project root (if not already done):**
    ```bash
    npx supabase init
    ```
3.  **Link your local project to the Supabase project:**
    Get your `Project ID` from the Supabase Dashboard (Project Settings > General).
    ```bash
    npx supabase link --project-ref <your-project-id>
    ```

## Managing Migrations

### Pushing Migrations to Production

Once you are linked, you can apply all new migrations in the `supabase/migrations` folder to your remote database:

```bash
npx supabase db push
```

### Creating New Migrations

To create a new migration script:
```bash
npx supabase migration new <name_of_migration>
```
This will create a new timestamped `.sql` file in this directory.

### Checking Database Status

To see which migrations have been applied:
```bash
npx supabase migration list
```

## Migration Files in this Directory

- `20260222000001_add_description_to_places.sql`: Adds the `description` column to the `places` table.
- `20260222000002_add_visit_photos_table.sql`: Creates the `visit_photos` table to support multiple photos per review.
