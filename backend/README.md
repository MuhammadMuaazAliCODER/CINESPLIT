# CineSplit Backend

The backend is a Django REST Framework API. Django and DRF handle routing, validation, authentication integration, permissions, and schema generation. Application data is stored in MongoDB through PyMongo; the Django SQLite database is only configured for framework support and is not the movie or account datastore.

## Current project status

- Milestones 1–4 are represented in the current codebase: authentication and profiles, movie catalogue and administration, and movie chapters.
- Movie documents live in `movies`; chapter documents live in the dedicated `movie_chapters` collection.
- Movie and chapter identifiers use MongoDB ObjectIds. Movie and chapter public detail routes use slugs.
- Chapter writes, deletions, and full-list reorders run in MongoDB transactions. The configured MongoDB Atlas deployment was verified as a replica set with logical sessions.
- Public chapter APIs expose published chapters only, and only when the parent movie is published.
- Administrator permissions are checked by the backend; frontend role checks are not treated as authorization.
- Video storage, playback, streaming, uploads, and later milestone features are not implemented.

## Requirements and setup

Requirements are listed in `requirements.txt`. Use a supported 64-bit Windows Python installation that has compatible wheels for the dependencies. The repository's current root `.venv` was created with Python 3.14 MinGW; `rpds-py`, a transitive schema dependency, could not build in that environment. Backend verification was completed with the installed Python 3.13 runtime.

From the repository root, make a local backend environment file only if one does not already exist. Do not overwrite an existing `.env`, because it may contain real credentials:

```powershell
Copy-Item backend/.env.example backend/.env
```

Edit `backend/.env` and configure at least:

- `DJANGO_SECRET_KEY` and `JWT_SECRET_KEY` with separate random secrets.
- `MONGODB_URI` and `MONGODB_DATABASE` for MongoDB Atlas or another replica-set deployment.
- `DJANGO_DEBUG` and allowed hosts/origins appropriate to the environment.
- SMTP settings if email verification messages should be sent.
- Cloudinary credentials only where the existing integration requires them.

From `backend/`, install dependencies into the selected Python environment and start Django:

```powershell
python -m pip install -r requirements.txt
python manage.py check
python manage.py runserver 127.0.0.1:8000
```

The frontend's example environment points to `http://localhost:8000`. Keep the backend origin and the frontend CORS/CSRF origin settings aligned when changing either port.

## Main routes

All API routes are under `/api/`.

### Health and documentation

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health/` | Service and dependency health status |
| GET | `/api/schema/` | OpenAPI schema |
| GET | `/api/docs/` | Swagger UI |
| GET | `/api/redoc/` | ReDoc UI |

### Authentication and profiles

The authentication routes are mounted at `/api/auth/`:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/csrf/` | Obtain the CSRF cookie/token used by browser requests |
| POST | `/register/` | Register an account |
| POST | `/verify-email/` | Verify an email address |
| POST | `/resend-verification/` | Resend a verification message |
| POST | `/login/` | Authenticate and receive session/token data |
| POST | `/refresh/` | Refresh an access token using the refresh cookie |
| POST | `/logout/` | Log out and revoke/clear refresh credentials |
| GET/PATCH | `/me/` | Read or update the signed-in profile |
| POST | `/change-password/` | Change the signed-in user's password |

Authentication uses the custom Mongo JWT authentication and Mongo-backed throttling defined in the `accounts` app. Browser requests retain CSRF protection and cookie credentials.

### Public movies and chapters

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/movies/` | Browse published movies; supports validated filters and pagination |
| GET | `/api/movies/featured/` | Browse featured published movies |
| GET | `/api/movies/genres/` | List genres from published movies |
| GET | `/api/movies/{movie_slug}/` | Retrieve a published movie |
| GET | `/api/movies/{movie_slug}/chapters/` | List published chapters in chapter-number order |
| GET | `/api/movies/{movie_slug}/chapters/{chapter_slug}/` | Retrieve one published chapter |

Draft movies and chapters are not exposed publicly. The individual chapter endpoint also requires a published parent movie.

### Administrator movie and chapter management

All routes below require a signed-in administrator as determined by the backend:

| Method | Path | Purpose |
| --- | --- | --- |
| GET/POST | `/api/admin/movies/` | List or create movies |
| GET/PUT/PATCH/DELETE | `/api/admin/movies/{movie_id}/` | Read, replace, update, or delete a movie |
| GET/POST | `/api/admin/movies/{movie_id}/chapters/` | List all chapters, including drafts, or append a chapter |
| GET/PUT/PATCH/DELETE | `/api/admin/movies/{movie_id}/chapters/{chapter_id}/` | Read, replace, update, or delete a chapter |
| POST | `/api/admin/movies/{movie_id}/chapters/reorder/` | Atomically reorder the complete chapter list |

Chapter numbering starts at 1. Creation appends at the end. Chapter numbers cannot be changed through ordinary chapter updates: use the reorder endpoint with every chapter ID for that movie exactly once. Deleting a chapter compacts the remaining numbers, and its response indicates that renumbering occurred. A movie cannot be deleted while it has chapters; remove its chapters first.

## MongoDB collections and indexes

`movies.mongo` initializes movie indexes when its collection is first requested. Chapter indexes are initialized by `get_chapter_collection()`:

- Unique `movie_chapters_movie_number_unique` on `(movie_id, chapter_number)`.
- Unique `movie_chapters_movie_slug_unique` on `(movie_id, slug)`.
- `movie_chapters_movie_status_order` on `(movie_id, status, chapter_number)` for visibility and ordered listings.

The chapter collection was contacted during Milestone 4 verification and these three indexes were present. Avoid using standalone MongoDB for chapter mutation features because MongoDB multi-document transactions require a replica set or a compatible sharded cluster.

## Checks and tests

Run from `backend/` using the Python environment that has `requirements.txt` installed:

```powershell
python manage.py check
python manage.py test movies
python manage.py test
python manage.py spectacular --validate
```

Milestone 4 verification completed with Django system checks passing, 27 movie tests passing, 51 total backend tests passing, and schema validation reporting zero errors. Schema generation currently emits a non-fatal status-enum naming collision warning; the generated schema resolves it automatically.

## Code map

- `config/`: settings, MongoDB client, project URL configuration, WSGI/ASGI entry points.
- `accounts/`: registration, email verification, login, JWTs, CSRF, profiles, permissions, and throttling.
- `movies/`: movie services and APIs, chapter services and APIs, serializers, collection/index initialization, and tests.
- `core/`: health endpoint.
- `series/`, `media/`, `favorites/`, `watch_progress/`, `reviews/`, and `analytics/`: other app packages in the project; their inclusion does not imply that later milestones are complete.

Do not commit `.env` files. The committed `.env.example` files are templates and should contain no live credentials.
