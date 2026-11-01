import { Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import LoginPage from './pages/LoginPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'
import AppLayout from './layouts/AppLayout.jsx'
import VerifyEmailPage from './pages/VerifyEmailPage.jsx'
import MovieCatalogPage from './pages/MovieCatalogPage.jsx'
import MovieDetailPage from './pages/MovieDetailPage.jsx'
import AdminMoviesPage from './pages/AdminMoviesPage.jsx'
import StatusPage from './pages/StatusPage.jsx'
import SeriesCatalogPage from './pages/SeriesCatalogPage.jsx'
import SeriesDetailPage from './pages/SeriesDetailPage.jsx'
import SeriesEpisodePage from './pages/SeriesEpisodePage.jsx'
import AdminSeriesPage from './pages/AdminSeriesPage.jsx'
import ChapterDetailPage from './pages/ChapterDetailPage.jsx'
import FavoritesPage from './pages/FavoritesPage.jsx'
import WatchHistoryPage from './pages/WatchHistoryPage.jsx'
import DiscoverPage from './pages/DiscoverPage.jsx'
import AdminDashboardPage from './pages/AdminDashboardPage.jsx'
import AdminMediaPage from './pages/AdminMediaPage.jsx'

export default function App() {
  return (
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
  )
}
