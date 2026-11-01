# CineSplit Frontend

The frontend is a React single-page application built with Vite and React Router. It uses a shared Axios client, the existing authentication context, Font Awesome icons, and the app's responsive dark streaming-catalog design.

## Features

- Movie and series catalogs, details, discovery search, featured shelves, and release-year sorting.
- Movie chapter navigation and series season, episode, and special navigation.
- Sign-up, email verification, sign-in, profile, and sign-out flows.
- Favorites, ratings and reviews, watch history, continue watching, and playback resume for signed-in users.
- Admin Studio pages for movies/chapters, series/seasons/episodes/specials, media uploads/library, and analytics.
- Custom video player with seek, play/pause, ±10-second skip, volume, fullscreen, playback speed, and Cloudinary quality choices.

## Setup

Use Node.js 18+ and npm. From `frontend/`:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
npm ci
npm run dev
```

The example environment is:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

Set this to the backend origin only. `src/services/api.js` appends `/api`, sends cookies and CSRF headers, attaches the in-memory JWT access token, and coalesces concurrent token-refresh attempts. Do not add credentials to frontend environment variables: Vite exposes `VITE_*` values to browser code. Restart Vite after changing `.env`.

The development server binds to `127.0.0.1:5174` (strict port).

## Routes

| Route | Page | Access |
| --- | --- | --- |
| `/` | Movie catalog, featured/latest shelves, continue-watching shelf | Public; shelf personalized when signed in |
| `/discover` | Search and filter movies/series | Public |
| `/series` | Series catalog | Public |
| `/series/:slug` | Series details, seasons, episodes and specials | Public; published content only |
| `/series/:slug/episodes/:episodeSlug` | Episode/special playback, favorites and reviews | Public page; engagement requires sign-in |
| `/movies/:slug` | Movie details, chapters, playback and reviews | Public page; engagement requires sign-in |
| `/movies/:slug/chapters/:chapterSlug` | Chapter playback, favorites and reviews | Public page; engagement requires sign-in |
| `/register`, `/verify-email`, `/login` | Account flows | Public |
| `/profile`, `/favorites`, `/watch-history`, `/continue-watching` | Account and personal library | Signed in |
| `/admin` | Analytics dashboard | Administrator |
| `/admin/movies`, `/admin/series`, `/admin/media` | Content and media administration | Administrator |

Backend permissions remain authoritative; hiding a frontend route does not grant or enforce API access.

## Media player

The reusable player is `src/components/VideoPlayer.jsx`. It preserves playback progress, resumes saved positions for signed-in users, and saves progress periodically and on pause/end. Keyboard controls are Space (play/pause), Left/Right arrows (seek 10 seconds), and M (mute). The settings menu includes playback speed and, for Cloudinary video delivery URLs, Auto/360p/480p/720p/1080p choices.

Quality choices request Cloudinary server-side resized variants with automatic quality encoding. They are maximum delivery widths, not guarantees that an uploaded source contains that many pixels. Valid Cloudinary configuration and network access are needed to play Cloudinary media; transformed playback has not been verified against every account/browser configuration.

## API services

- `src/services/api.js`: shared Axios setup, CSRF, cookies and JWT refresh.
- `src/services/auth.js`: registration, verification, authentication and profiles.
- `src/services/movies.js`, `src/services/chapters.js`: movie and chapter APIs.
- `src/services/series.js`: series, season, episode and special APIs.
- `src/services/media.js`: media administration.
- `src/services/engagement.js`: discovery, favorites, watch progress, reviews and analytics.

Keep requests in these service modules rather than creating independent Axios clients.

## Scripts

Run from `frontend/`:

```powershell
npm run dev
npm test
npm run build
npm run preview
```

The build output in `dist/` is generated. Tests use Node's built-in test runner (`node --test`).

## Source map

- `src/App.jsx`: routes and access gates.
- `src/layouts/`: shared site layout and navigation.
- `src/pages/`: catalog, detail, account, personal library, and Studio pages.
- `src/components/`: cards, uploaders, reviews, engagement controls, and video player.
- `src/services/`: shared API and endpoint functions.
- `src/styles/index.css`: global styles and responsive layouts.
- `tests/`: frontend API and page behavior checks.

Keep `frontend/.env` private and use `.env.example` as the safe template.