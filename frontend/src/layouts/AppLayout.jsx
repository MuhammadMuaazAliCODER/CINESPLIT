import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faFilm, faMagnifyingGlass, faRightFromBracket, faUser } from '@fortawesome/free-solid-svg-icons'
import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import RouteIndexability from '../components/RouteIndexability.jsx'

export default function AppLayout() {
  const { user, loading, signOut } = useAuth()
  const [query, setQuery] = useState('')
  const navigate = useNavigate()
  function search(event) { event.preventDefault(); const value = query.trim(); navigate(value ? `/discover?q=${encodeURIComponent(value)}` : '/discover') }
  return (
    <div className="site-shell">
      <RouteIndexability />
      <header className="site-header">
        <Link className="brand" to="/" aria-label="CineSplit home"><FontAwesomeIcon icon={faFilm} aria-hidden="true" /><span>CINE<span className="brand-accent">SPLIT</span></span></Link>
        <nav aria-label="Main navigation">
          <Link className="nav-link" to="/">Movies</Link>
          <Link className="nav-link" to="/series">Series</Link>
          <Link className="nav-link" to="/discover">Discover</Link>
          <form className="header-search" role="search" onSubmit={search}><FontAwesomeIcon icon={faMagnifyingGlass} aria-hidden="true"/><input aria-label="Search movies and series" placeholder="Search" value={query} onChange={(event) => setQuery(event.target.value)}/></form>
          {loading ? <span className="nav-loading" role="status">Loading account…</span> : user ? <>
            {user.role === 'admin' && <Link className="nav-link" to="/admin">Studio</Link>}
            <Link className="nav-link" to="/favorites">Favorites</Link><Link className="nav-link" to="/continue-watching">Continue</Link><Link className="nav-link" to="/watch-history">History</Link>
            <Link className="nav-profile" to="/profile"><FontAwesomeIcon icon={faUser} aria-hidden="true" /><span>{user.full_name || user.username}</span></Link>
            <button className="nav-button" type="button" onClick={() => void signOut()}><FontAwesomeIcon icon={faRightFromBracket} aria-hidden="true" /><span>Sign out</span></button>
          </> : <><Link className="nav-link" to="/login">Sign in</Link><Link className="nav-cta" to="/register">Create account</Link></>}
        </nav>
      </header>
      <main className="app-shell"><Outlet /></main>
    </div>
  )
}
