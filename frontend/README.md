# CineSplit Frontend

The frontend is a React single-page application built with Vite. It uses React Router for client-side routes, Axios for API requests, and Font Awesome for icons. The interface covers the movie catalogue and details, account flows, profiles, and administrator movie/chapter management.

## Current project status

- The app is configured for Vite on `http://localhost:5174` (`strictPort` is enabled).
- The centralized Axios client reads `VITE_API_BASE_URL`, defaults to `http://localhost:8000`, and appends `/api` once.
- Browser requests use cookies and CSRF headers; the shared client also adds JWT access tokens and handles access-token refresh/retry behavior.
- The public movie detail page lists published chapters and shows an empty state when none are published. It does not offer playback.
- The admin movie editor includes chapter create/edit/delete, publish/unpublish, and reorder controls.
- Administrator authorization is enforced by the backend. Frontend route guards are only a navigation aid.
- Video uploads/playback, favorites, watch history, reviews, ratings, and later milestone features are not implemented here.

## Requirements and setup

Use a current Node.js version with npm. From `frontend/`, install the locked dependencies and start Vite:

```powershell
npm ci
npm run dev
```

The development server runs at `http://localhost:5174`. The Django API should be available at `http://localhost:8000`.

If `frontend/.env` does not exist, create it from the example. Do not overwrite an existing `.env`:

```powershell
Copy-Item .env.example .env
```

The current example contains:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

Vite only exposes variables prefixed with `VITE_`. Set this value to the backend origin (without adding `/api`; the shared client adds that segment). Restart the Vite development server after changing environment files. Do not point this variable at the frontend port or port 5000 unless the backend architecture is intentionally changed.

## Routes

| Browser route | Page | Access |
| --- | --- | --- |
| `/` | Public movie catalogue | Public |
| `/movies/:slug` | Public movie details and published chapters | Public |
| `/register` | Registration | Public |
| `/login` | Sign in | Public |
| `/verify-email` | Email verification | Public |
| `/profile` | Account profile | Signed in |
| `/admin/movies` | Movie and chapter management | Administrator |

Unknown browser paths render the app's status/not-found page.

## API client and services

`src/services/api.js` owns the shared Axios instance. It combines the configured backend origin with `/api`, sends cookies, preserves CSRF behavior, attaches the in-memory access token, and serializes refresh requests so concurrent 401 responses share one refresh attempt.

- `src/services/auth.js`: authentication, CSRF, profile, and account requests.
- `src/services/movies.js`: public catalogue and administrator movie requests.
- `src/services/chapters.js`: public chapter listing and administrator chapter operations.

Services use relative `/movies/...` or `/admin/movies/...` paths against the shared client. Do not create a second Axios instance or add `/api` to `VITE_API_BASE_URL` without updating the client construction.

## Movie and chapter behavior

The catalogue requests published movies from the backend and provides search, filters, sort, pagination, loading, empty, and error states. Movie detail requests the movie and its published chapters. Chapter cards show chapter number, title, description, duration in minutes, and the availability label.

From the admin page, select a movie to edit it and open its chapter manager. Create appends a chapter to the current order. The up/down controls change the local order; **Save order** submits every chapter ID so the backend can validate and atomically store the order. Deleting a chapter requires browser confirmation; remaining chapters are renumbered by the backend. Draft chapters are visible only in the administrator interface.

## Scripts

Run from `frontend/`:

```powershell
npm run dev
npm test -- --test-reporter=spec
npm run build
npm run preview
```

The production build is written to `dist/`, which is generated output and should not be committed. The Node test suite checks API URLs/credentials and important catalogue, detail, admin, and chapter UI behavior. The Vite test harness may print a non-fatal warning if its configured HMR socket port `24678` is already occupied; that warning did not prevent the current tests from passing.

Milestone 4 verification completed with all 8 frontend tests passing and the production build succeeding.

## Source map

- `src/App.jsx`: route table.
- `src/layouts/`: shared page shell and navigation.
- `src/pages/`: route-level screens.
- `src/components/`: reusable forms, cards, guards, and chapter administration.
- `src/services/`: shared API client and endpoint functions.
- `src/styles/index.css`: application styles and responsive layouts.
- `tests/movies.test.mjs`: frontend API and movie/chapter checks.

The frontend `.env` may contain local configuration. Keep it out of source control and use `.env.example` as the safe template.
