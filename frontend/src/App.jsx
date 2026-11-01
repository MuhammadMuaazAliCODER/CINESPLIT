import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import AppLayout from './layouts/AppLayout.jsx'

const LoginPage = lazy(() => import('./pages/LoginPage.jsx'))
const ProfilePage = lazy(() => import('./pages/ProfilePage.jsx'))
const RegisterPage = lazy(() => import('./pages/RegisterPage.jsx'))
const VerifyEmailPage = lazy(() => import('./pages/VerifyEmailPage.jsx'))
const MovieCatalogPage = lazy(() => import('./pages/MovieCatalogPage.jsx'))
const MovieDetailPage = lazy(() => import('./pages/MovieDetailPage.jsx'))
const AdminMoviesPage = lazy(() => import('./pages/AdminMoviesPage.jsx'))
const StatusPage = lazy(() => import('./pages/StatusPage.jsx'))
const SeriesCatalogPage = lazy(() => import('./pages/SeriesCatalogPage.jsx'))
const SeriesDetailPage = lazy(() => import('./pages/SeriesDetailPage.jsx'))
const SeriesEpisodePage = lazy(() => import('./pages/SeriesEpisodePage.jsx'))
const AdminSeriesPage = lazy(() => import('./pages/AdminSeriesPage.jsx'))
const ChapterDetailPage = lazy(() => import('./pages/ChapterDetailPage.jsx'))
const FavoritesPage = lazy(() => import('./pages/FavoritesPage.jsx'))
const WatchHistoryPage = lazy(() => import('./pages/WatchHistoryPage.jsx'))
const DiscoverPage = lazy(() => import('./pages/DiscoverPage.jsx'))
const AdminDashboardPage = lazy(() => import('./pages/AdminDashboardPage.jsx'))
const AdminMediaPage = lazy(() => import('./pages/AdminMediaPage.jsx'))

export default function App() {
  return (
    <Suspense fallback={<p className="movie-state" role="status">Loading CineSplit…</p>}>
      <Routes>
        <Route element={<AppLayout />}>
        <Route index element={<MovieCatalogPage />} />
        <Route path="series" element={<SeriesCatalogPage />} />
        <Route path="series/:slug" element={<SeriesDetailPage />} />
        <Route path="series/:slug/episodes/:episodeSlug" element={<SeriesEpisodePage />} />
        <Route path="discover" element={<DiscoverPage />} />
        <Route path="movies/:slug" element={<MovieDetailPage />} />
        <Route path="movies/:slug/chapters/:chapterSlug" element={<ChapterDetailPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="verify-email" element={<VerifyEmailPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="profile" element={<ProfilePage />} />
          <Route path="favorites" element={<FavoritesPage />} />
          <Route path="watch-history" element={<WatchHistoryPage />} />
          <Route path="continue-watching" element={<WatchHistoryPage continueOnly />} />
        </Route>
        <Route element={<ProtectedRoute requiredRole="admin" />}>
          <Route path="admin" element={<AdminDashboardPage />} />
          <Route path="admin/movies" element={<AdminMoviesPage />} />
          <Route path="admin/series" element={<AdminSeriesPage />} />
          <Route path="admin/media" element={<AdminMediaPage />} />
        </Route>
        <Route path="*" element={<StatusPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
