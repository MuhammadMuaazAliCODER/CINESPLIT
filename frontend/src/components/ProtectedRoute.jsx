import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ requiredRole }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return <div className="page-loading" role="status">Restoring your session…</div>
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />
  if (requiredRole && user.role !== requiredRole) return <Navigate to="/" replace />
  return <Outlet />
}
