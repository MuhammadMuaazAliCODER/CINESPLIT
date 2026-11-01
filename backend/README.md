# CineSplit Backend

The backend is a Django 5.2 and Django REST Framework API. PyMongo is the persistence layer for all CineSplit application data; SQLite is configured only for Django framework functionality. The project retains its custom MongoDB-backed user model, JWT authentication, permissions, and throttling.

## Features

- Registration, verification email, sign-in, refresh-token rotation, profiles, and password changes.
- Movie/chapter and series/season/episode/special CRUD, publishing, and ordering.
- Public discovery, favorites, watch progress/history, and ratings/reviews.
- Administrator-only analytics, Cloudinary media uploads, association lookup, and media library.
- MongoDB indexes for slugs, parent relationships, ordering, user-scoped engagement, and media metadata.

## Setup and configuration

Use Python 3.10+ compatible with the pinned ranges in `requirements.txt`. From the repository root, create a local file only if it does not already exist:

```powershell
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Set these in `backend/.env`:

- `DJANGO_SECRET_KEY` and `JWT_SECRET_KEY`: separate random values.
- `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`: debug setting and allowed hosts.
- `DJANGO_CORS_ALLOWED_ORIGINS`: exact browser origins; settings also use this list for CSRF trusted origins.
- `MONGODB_URI`, `MONGODB_DATABASE`: Mongo connection and database name.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `SMTP_USE_SSL`, `DEFAULT_FROM_EMAIL`: verification email delivery.
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`: all three are required for upload configuration. They are read only by the backend.

Settings load `backend/.env` using `python-dotenv`. Existing non-empty process environment values retain precedence; blank inherited Cloudinary variables are filled from non-empty values in `.env`. Missing Cloudinary configuration produces a controlled HTTP 503 on upload, with missing variable names (never values) in the response. The Cloudinary SDK is declared in `requirements.txt`.

Start Django from `backend/`:

```powershell
python manage.py check
python manage.py runserver 127.0.0.1:8000
```

For MongoDB transactions, use a replica set or compatible sharded cluster; standalone MongoDB does not support the multi-document transactions used by chapter and series content operations.

## Administrator provisioning

Create a verified admin with an interactive password prompt:

```powershell
python manage.py create_admin
```

To promote an existing active, verified account, explicitly invoke:

```powershell
python manage.py create_admin --promote-email admin@example.com
```

Promotion requires typing `PROMOTE`. Passwords are never printed. The command uses the application's MongoDB user collection and existing hashing implementation.

## API routes

All routes below are prefixed by `/api`. OpenAPI is at `/schema/`, Swagger UI at `/docs/`, and ReDoc at `/redoc/`.

| Area | Routes and behavior |
| --- | --- |
| Health | `GET /health/` reports MongoDB availability and Cloudinary configuration. |
| Accounts | `/auth/`: CSRF, register, verify/resend, login, refresh, logout, profile, and password change. |
| Movies | `/movies/`: published list, featured list, genres, and slug detail. Supports validated search/filter/sort/pagination. |
| Chapters | `/movies/{movie_slug}/chapters/` and detail; published items require a published parent movie. Admin CRUD and reorder are under `/admin/movies/`. |
| Series | `/series/`: published lists, featured/genres, slug detail, seasons, regular episodes, specials, and episode detail. Admin operations are under `/admin/series/`. |
| Discovery | `GET /discover/`, `/discover/featured/`, `/discover/latest/` for published movie and series discovery. |
| Favorites | `/favorites/`: authenticated list/add/state/remove. Records are scoped to the authenticated user. |
| Watch history | `/watch-history/`: authenticated progress save/list, item state, and removal. |
| Reviews | `/reviews/{content_type}/{content_id}/`: public summary/list, authenticated create, and owner-only update/delete. |
| Media | `/admin/media/`: admin library; `/admin/media/{content_type}/{content_id}/` association lookup; add `/video/` or `/poster/` for multipart upload. Supported content types are movie, chapter, episode. |
| Analytics | `GET /admin/analytics/` requires administrator authorization. |

All admin endpoints enforce permissions in Django. Public content serializers and services filter drafts and unpublished parent content. Object IDs and parent relationships are validated in backend services.

## Media upload and delivery

The upload service validates role, declared content type, file signature, and size before calling Cloudinary. Videos are uploaded as Cloudinary video resources; posters use image resources. The backend stores the Cloudinary public ID, secure URL, format, duration, uploader and association in MongoDB and embeds the permitted metadata in published content responses. Client input does not select arbitrary Cloudinary public IDs.

When replacing an asset, the new upload is associated before the prior Cloudinary asset is destroyed. Failed remote cleanup is recorded in `media_orphans` for visibility in the admin media library. Content deletion detaches associated media metadata and queues remote cleanup failures. Cloudinary transformations used by the frontend player produce on-demand width-limited delivery URLs; actual transformation behavior depends on Cloudinary availability/account configuration.

## MongoDB collections and indexes

Index definitions are in the app `mongo.py` modules and are initialized when the relevant collection is accessed. Important constraints include:

- Movies and series: unique global slug.
- Chapters: unique `(movie_id, chapter_number)` and `(movie_id, slug)`.
- Seasons: unique `(series_id, season_number)` and `(series_id, slug)`.
- Episodes: partial unique indexes for regular episode number/slug scoped to season, and special number/slug scoped to series. The filters distinguish `type: regular` from `type: special`.
- Favorites, progress and reviews: user/content unique indexes to prevent duplicates and isolate records.
- Media: unique content/role association; orphan cleanup records have unique Cloudinary public IDs.

Chapter and series create/update/delete/reorder operations use transactions to preserve parent revisions, ordering, and cascading deletions. MongoDB replica-set transaction support is required for these operations. Single-document favorites, progress, and reviews use MongoDB atomic operations and unique indexes rather than multi-document transactions. Cloudinary cleanup is an external operation and is handled with a durable orphan queue rather than being part of a MongoDB transaction.

## Validation

Run from `backend/`:

```powershell
python manage.py check
python manage.py test
python manage.py spectacular --validate
```

Unit tests do not prove connectivity to a live MongoDB cluster, SMTP provider, or Cloudinary account. Verify those integrations in a safe environment before production use.

## Code map

- `config/`: settings, Mongo client, Cloudinary configuration, routing.
- `accounts/`: custom authentication, users, permissions, throttling and provisioning command.
- `movies/`, `series/`: content services, serializers, views, indexes and tests.
- `media/`: Cloudinary upload/association, cleanup and media library.
- `favorites/`, `watch_progress/`, `reviews/`, `analytics/`: engagement and admin reporting APIs.
- `core/`: health, shared content resolution, and discovery.

Never commit `.env` files. Keep live credentials out of source control and API responses.