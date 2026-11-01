import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

const PRIVATE_PAGES = {
  '/login': ['Sign in | CineSplit', 'Sign in to your CineSplit account.'],
  '/register': ['Create an account | CineSplit', 'Create a CineSplit account to save favorites and playback progress.'],
  '/verify-email': ['Verify your email | CineSplit', 'Verify the email address for your CineSplit account.'],
  '/profile': ['Your profile | CineSplit', 'Manage your CineSplit account profile.'],
  '/favorites': ['Your favorites | CineSplit', 'Your saved CineSplit films and series.'],
  '/watch-history': ['Watch history | CineSplit', 'Your CineSplit watch history.'],
  '/continue-watching': ['Continue watching | CineSplit', 'Continue watching content from your CineSplit history.'],
  '/admin': ['Studio dashboard | CineSplit', 'CineSplit administrator dashboard.'],
  '/admin/movies': ['Manage movies | CineSplit', 'CineSplit movie and chapter administration.'],
  '/admin/series': ['Manage series | CineSplit', 'CineSplit series, season, and episode administration.'],
  '/admin/media': ['Media library | CineSplit', 'CineSplit administrator media library.'],
}

export default function RouteIndexability() {
  const location = useLocation()

  useEffect(() => {
    const pathname = location.pathname.replace(/\/+$/, '') || '/'
    const privateEntry = Object.entries(PRIVATE_PAGES).sort(([left], [right]) => right.length - left.length).find(([path]) => pathname === path || pathname.startsWith(`${path}/`))
    const knownPublicPath = pathname === '/' || pathname === '/discover' || pathname === '/series'
      || /^\/movies\/[a-z0-9-]+(?:\/chapters\/[a-z0-9-]+)?$/i.test(pathname)
      || /^\/series\/[a-z0-9-]+(?:\/episodes\/[a-z0-9-]+)?$/i.test(pathname)
    const noIndex = Boolean(privateEntry || !knownPublicPath || location.search || (import.meta.env.PROD && !import.meta.env.VITE_PUBLIC_SITE_URL))
    let robots = document.head.querySelector('meta[name="robots"]')
    if (!robots) {
      robots = document.createElement('meta')
      robots.name = 'robots'
      document.head.appendChild(robots)
    }
    robots.content = noIndex ? 'noindex, nofollow' : 'index, follow'
    if (privateEntry) {
      document.title = privateEntry[1][0]
      let description = document.head.querySelector('meta[name="description"]')
      if (!description) {
        description = document.createElement('meta')
        description.name = 'description'
        document.head.appendChild(description)
      }
      description.content = privateEntry[1][1]
      document.head.querySelector('link[rel="canonical"]')?.remove()
    }
  }, [location.pathname, location.search])

  return null
}
