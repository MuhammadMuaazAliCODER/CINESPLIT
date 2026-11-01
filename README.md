# CineSplit

CineSplit is a streaming-style catalog and content-management platform. It combines a React/Vite frontend with a Django REST API, custom JWT authentication, and MongoDB persistence through PyMongo.

## Features

- Account registration, email verification, sign-in, profile management, and refresh-token handling.
- Public movie and series catalogs, search/discovery, filters, featured content, and detail pages.
- Movie chapters; series seasons, regular episodes, and specials.
- Administrator tools for content CRUD, publication, ordering, Cloudinary media uploads, a media library, and analytics.
- Favorites, ratings/reviews, watch history, continue watching, and saved playback position.
- Custom video controls: seek, play/pause, 10-second skip, volume, playback speed, fullscreen, and Cloudinary delivery-size choices.

Django uses SQLite only for its internal framework components. CineSplit application records are stored in MongoDB using PyMongo.

## Technology and layout

- **Frontend:** React 19, React Router, Axios, Vite, Tailwind CSS, Font Awesome.
- **Backend:** Python, Django 5.2, Django REST Framework, drf-spectacular.
- **Data and authentication:** MongoDB/PyMongo, bcrypt, custom JWT authentication.
- **Media:** Cloudinary Python SDK (credentials are backend-only).

```text
backend/   Django apps, API, MongoDB services/indexes, and backend configuration
frontend/  React app, routes, API services, and styles
```

See [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md) for component-level details.

## Requirements

- Python supported by Django 5.2 (Python 3.10+).
- Node.js 18+ and npm.
- A MongoDB replica set or compatible sharded deployment. MongoDB Atlas is supported.
- SMTP credentials for email verification.
- Cloudinary credentials to upload and deliver posters/videos.

MongoDB must be reachable from the backend host and permit transactions for transactional content operations.

## Local setup

Run these commands from the repository root in PowerShell. Copy example files only when the target `.env` does not already exist; never overwrite a file containing local settings or credentials.

### Backend

```powershell
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Configure `backend/.env`:

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY`, `JWT_SECRET_KEY` | Separate, private random secrets. |
| `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` | Debug mode and permitted backend hosts. |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Exact browser origins, including scheme and port. |
| `MONGODB_URI`, `MONGODB_DATABASE` | MongoDB connection and application database. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `SMTP_USE_SSL`, `DEFAULT_FROM_EMAIL` | Verification email delivery. Do not enable TLS and SSL together. |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Optional until media uploads are used; all three are required for Cloudinary. Keep them in backend `.env`, never frontend `.env`. |

Django loads `backend/.env`. Non-empty process environment values take precedence; empty inherited Cloudinary variables fall back to non-empty values from that file. Restart Django after changing backend configuration.

Start the API from `backend/`:

```powershell
python manage.py check
python manage.py runserver 127.0.0.1:8000
```

Create a new verified administrator with the interactive prompt:

```powershell
python manage.py create_admin
```

Promoting an existing account requires an explicit command and confirmation:

```powershell
python manage.py create_admin --promote-email admin@example.com
```

The account must already be active and verified. The command does not print passwords.

### Frontend

In a second terminal, from the repository root:

```powershell
if (-not (Test-Path frontend/.env)) { Copy-Item frontend/.env.example frontend/.env }
Set-Location frontend
npm ci
npm run dev
```

`frontend/.env` uses `VITE_API_BASE_URL=http://localhost:8000` (backend origin only; the API client adds `/api`). Vite serves the app at `http://127.0.0.1:5174/`. Restart Vite after changing its `.env`.

## Media uploads and playback

Sign in as an administrator, open **Studio → Movies** or **Studio → Series**, create or select content, and use its media controls to upload a poster or video. Movie chapters and series episodes have their own media controls. Content must be published, along with its required parent content, to be publicly playable.

Uploads are validated server-side by file type, signature, and size. Videos and posters are sent to Cloudinary; MongoDB stores media metadata and the content association. The custom player offers Auto, 360p, 480p, 720p, and 1080p delivery choices for Cloudinary video URLs. Cloudinary creates resized deliveries server-side; a selected maximum size cannot increase the resolution of a smaller original. Actual playback and transformed delivery require valid Cloudinary credentials and a live Cloudinary account.

## API overview

All API routes use the `/api/` prefix. Swagger UI and ReDoc are available at `/api/docs/` and `/api/redoc/`; the OpenAPI schema is at `/api/schema/`.

| API area | Base path | Purpose |
| --- | --- | --- |
| Health | `/api/health/` | MongoDB status and Cloudinary configuration status. |
| Authentication | `/api/auth/` | Registration, verification, login, refresh, logout, and profiles. |
| Movies/chapters | `/api/movies/`, `/api/admin/movies/` | Public catalogs and admin movie/chapter management. |
| Series | `/api/series/`, `/api/admin/series/` | Public series, seasons, episodes, specials, and admin management. |
| Discovery | `/api/discover/` | Search and filters, featured and latest content. |
| Favorites | `/api/favorites/` | Signed-in user's favorites. |
| Watch history | `/api/watch-history/` | Signed-in user's progress and history. |
| Reviews | `/api/reviews/` | Public review summaries and authenticated review management. |
| Media | `/api/admin/media/` | Admin upload, association lookup, and media library. |
| Analytics | `/api/admin/analytics/` | Admin dashboard counts and recent activity. |

Administrative APIs enforce authorization on the backend. Frontend route guards only improve navigation and are not a security boundary. Public content APIs filter out drafts and enforce published parent visibility.

## Validation

From `backend/`:

```powershell
python manage.py check
python manage.py test
python manage.py spectacular --validate
```

From `frontend/`:

```powershell
npm test
npm run build
```

Automated checks do not replace testing against the deployment's own MongoDB replica set, SMTP provider, Cloudinary account, and browser/device combination.

## Security and deployment

- Never commit `.env` files or put private credentials in `VITE_*` variables. Use the `.env.example` files as templates.
- Use production-only random secrets, `DJANGO_DEBUG=false`, correct hosts, exact CORS/CSRF origins, and HTTPS.
- Keep Cloudinary credentials server-side. Configure SMTP for real email verification.
- Do not expose drafts; the API performs publication checks independently of frontend visibility.
- Do not use a standalone MongoDB server for operations that require multi-document transactions.

No license is currently specified in this repository.