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

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<MovieCatalogPage />} />
        <Route path="movies/:slug" element={<MovieDetailPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="verify-email" element={<VerifyEmailPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="profile" element={<ProfilePage />} />
        </Route>
        <Route element={<ProtectedRoute requiredRole="admin" />}>
          <Route path="admin/movies" element={<AdminMoviesPage />} />
        </Route>
        <Route path="*" element={<StatusPage />} />
      </Route>
    </Routes>
  )
}
