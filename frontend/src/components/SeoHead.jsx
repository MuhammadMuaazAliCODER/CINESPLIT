import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

const SITE_URL = (import.meta.env.VITE_PUBLIC_SITE_URL || '').replace(/\/+$/, '')
const DEFAULT_DESCRIPTION = 'Discover films and series on CineSplit, with chapters, episodes, and stories to follow.'
const DEFAULT_IMAGE = SITE_URL ? `${SITE_URL}/cinesplit-social.svg` : ''

function canonicalPath(path) {
  if (!path || path === '/') return '/'
  return `/${path.replace(/^\/+|\/+$/g, '')}/`
}

function setMeta(selector, attributes, content) {
  let element = document.head.querySelector(selector)
  if (content == null || content === '') {
    element?.remove()
    return
  }
  if (!element) {
    element = document.createElement('meta')
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value)
    document.head.appendChild(element)
  }
  element.content = content
}

function asAbsoluteImage(image) {
  if (!image) return DEFAULT_IMAGE
  try {
    const url = new URL(image, SITE_URL || window.location.origin)
    return ['http:', 'https:'].includes(url.protocol) ? url.href : DEFAULT_IMAGE
  } catch {
    return DEFAULT_IMAGE
  }
}

export default function SeoHead({
  title = 'CineSplit | Films and series to follow',
  description = DEFAULT_DESCRIPTION,
  path,
  image,
  type = 'website',
  schema,
  noIndex = false,
}) {
  const location = useLocation()
  const normalizedPath = canonicalPath(path ?? location.pathname)
  const filteredUrl = Boolean(location.search)
  const privatePath = /^\/(?:admin|profile|favorites|watch-history|continue-watching|login|register|verify-email)(?:\/|$)/.test(location.pathname)
  const shouldNoIndex = noIndex || filteredUrl || privatePath || (import.meta.env.PROD && !SITE_URL)

  useEffect(() => {
    const pageTitle = title.trim() || 'CineSplit'
    const pageDescription = (description || DEFAULT_DESCRIPTION).trim().slice(0, 300)
    const canonicalUrl = SITE_URL && !shouldNoIndex ? `${SITE_URL}${normalizedPath}` : null
    const socialImage = asAbsoluteImage(image)
    document.title = pageTitle
    setMeta('meta[name="description"]', { name: 'description' }, pageDescription)
    setMeta('meta[name="robots"]', { name: 'robots' }, shouldNoIndex ? 'noindex, nofollow' : 'index, follow')
    setMeta('meta[property="og:type"]', { property: 'og:type' }, type)
    setMeta('meta[property="og:site_name"]', { property: 'og:site_name' }, 'CineSplit')
    setMeta('meta[property="og:title"]', { property: 'og:title' }, pageTitle)
    setMeta('meta[property="og:description"]', { property: 'og:description' }, pageDescription)
    setMeta('meta[property="og:image"]', { property: 'og:image' }, socialImage)
    setMeta('meta[property="og:image:alt"]', { property: 'og:image:alt' }, image ? `${pageTitle} poster` : 'CineSplit brand image')
    setMeta('meta[property="og:url"]', { property: 'og:url' }, canonicalUrl)
    setMeta('meta[name="twitter:card"]', { name: 'twitter:card' }, 'summary_large_image')
    setMeta('meta[name="twitter:title"]', { name: 'twitter:title' }, pageTitle)
    setMeta('meta[name="twitter:description"]', { name: 'twitter:description' }, pageDescription)
    setMeta('meta[name="twitter:image"]', { name: 'twitter:image' }, socialImage)
    setMeta('meta[name="twitter:image:alt"]', { name: 'twitter:image:alt' }, image ? `${pageTitle} poster` : 'CineSplit brand image')

    let canonical = document.head.querySelector('link[rel="canonical"]')
    if (!canonicalUrl) canonical?.remove()
    else {
      if (!canonical) {
        canonical = document.createElement('link')
        canonical.rel = 'canonical'
        document.head.appendChild(canonical)
      }
      canonical.href = canonicalUrl
    }

    const schemas = []
    if (SITE_URL && !shouldNoIndex) {
      schemas.push(
        { '@context': 'https://schema.org', '@type': 'Organization', name: 'CineSplit', url: `${SITE_URL}/`, logo: `${SITE_URL}/cinesplit-social.svg` },
        {
          '@context': 'https://schema.org',
          '@type': 'WebSite',
          name: 'CineSplit',
          url: `${SITE_URL}/`,
          potentialAction: { '@type': 'SearchAction', target: `${SITE_URL}/discover/?q={search_term_string}`, 'query-input': 'required name=search_term_string' },
        },
      )
    }
    if (Array.isArray(schema)) schemas.push(...schema.filter(Boolean))
    else if (schema) schemas.push(schema)
    let script = document.getElementById('cinesplit-page-schema')
    if (schemas.length) {
      if (!script) {
        script = document.createElement('script')
        script.id = 'cinesplit-page-schema'
        script.type = 'application/ld+json'
        document.head.appendChild(script)
      }
      script.textContent = JSON.stringify(schemas)
    } else script?.remove()
  }, [title, description, normalizedPath, image, type, schema, shouldNoIndex])

  return null
}
