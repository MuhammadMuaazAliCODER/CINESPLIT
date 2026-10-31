import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faFilm, faRightFromBracket, faUser } from '@fortawesome/free-solid-svg-icons'
import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function AppLayout() {
  const { user, loading, signOut } = useAuth()
  return (
    <div className="site-shell">
      <header className="site-header">
        <Link className="brand" to="/" aria-label="CineSplit home"><FontAwesomeIcon icon={faFilm} aria-hidden="true" /><span>CINE<span className="brand-accent">SPLIT</span></span></Link>
        <nav aria-label="Main navigation">
          <Link className="nav-link" to="/">Movies</Link>
          {loading ? <span className="nav-loading" role="status">Loading account…</span> : user ? <>
            {user.role === 'admin' && <Link className="nav-link" to="/admin/movies">Studio</Link>}
            <Link className="nav-profile" to="/profile"><FontAwesomeIcon icon={faUser} aria-hidden="true" /><span>{user.full_name || user.username}</span></Link>
            <button className="nav-button" type="button" onClick={() => void signOut()}><FontAwesomeIcon icon={faRightFromBracket} aria-hidden="true" /><span>Sign out</span></button>
          </> : <><Link className="nav-link" to="/login">Sign in</Link><Link className="nav-cta" to="/register">Create account</Link></>}
        </nav>
      </header>
      <main className="app-shell"><Outlet /></main>
    </div>
  )
}
