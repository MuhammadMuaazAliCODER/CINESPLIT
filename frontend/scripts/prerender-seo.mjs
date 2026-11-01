import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const frontendDir = path.resolve(scriptDir, '..')
const distDir = path.join(frontendDir, 'dist')
const requiredSitemapUrlLimit = 40000

async function loadPublicEnv() {
  for (const name of ['.env.production.local', '.env.production', '.env.local', '.env']) {
    try {
      const content = await awaitReadEnv(name)
      for (const line of content.split(/\r?\n/)) {
        const match = line.match(/^\s*(VITE_[A-Z0-9_]+)\s*=\s*(.*?)\s*$/)
        if (!match || process.env[match[1]]) continue
        let value = match[2]
        if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) value = value.slice(1, -1)
        process.env[match[1]] = value
      }
    } catch { /* Optional local/production environment file. */ }
  }
}

function awaitReadEnv(name) {
  return readFile(path.join(frontendDir, name), 'utf8')
}

await loadPublicEnv()

const siteUrlText = (process.env.VITE_PUBLIC_SITE_URL || '').trim().replace(/\/+$/, '')
const apiOriginText = (process.env.VITE_API_BASE_URL || 'http://localhost:8000').trim().replace(/\/+$/, '')
const htmlEscape = (value = '') => String(value).replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character])
const jsonForHtml = (value) => JSON.stringify(value).replace(/</g, '\\u003c').replace(/>/g, '\\u003e').replace(/&/g, '\\u0026')
const textDescription = (value, fallback) => String(value || fallback).replace(/\s+/g, ' ').trim().slice(0, 300)

function validateSiteUrl(value) {
  if (!value) return null
  const productionBuild = process.argv.includes('--production')
  let url
  try { url = new URL(value) } catch { throw new Error('VITE_PUBLIC_SITE_URL must be a valid public origin, such as https://www.example.com.') }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('VITE_PUBLIC_SITE_URL must contain only the site origin, with no credentials, path, query, or fragment.')
  }
  if (productionBuild && ['localhost', '127.0.0.1', '::1'].includes(url.hostname)) {
    throw new Error('VITE_PUBLIC_SITE_URL cannot use localhost in a production SEO build.')
  }
  if (url.protocol !== 'https:' && !['localhost', '127.0.0.1', '::1'].includes(url.hostname)) {
    throw new Error('Use HTTPS for the configured production SEO domain.')
  }
  return url.origin
}

const siteUrl = validateSiteUrl(siteUrlText)
const apiOrigin = new URL(apiOriginText)
const apiRoot = `${apiOrigin.origin}${apiOrigin.pathname.replace(/\/+$/, '').replace(/\/api$/i, '')}/api`
const sitemapEntries = new Map()
const renderedPaths = new Set()

function robotsText(sitemap = '') {
  return `User-agent: *\nAllow: /\nDisallow: /api/\n${sitemap ? `\nSitemap: ${sitemap}\n` : ''}`
}

async function noDomainOutput() {
  await writeFile(path.join(distDir, 'robots.txt'), robotsText(), 'utf8')
  console.warn('SEO prerendering skipped: set VITE_PUBLIC_SITE_URL to the real public site origin. No sitemap or local canonical URLs were generated.')
}

function absoluteUrl(route) {
  const normalized = route === '/' ? '/' : `/${route.replace(/^\/+|\/+$/g, '')}/`
  return `${siteUrl}${normalized}`
}

function safeSegment(value) {
  return /^[a-z0-9]+(?:-[a-z0-9]+)*$/i.test(String(value || ''))
}

function addSitemap(route, lastmod) {
  const url = absoluteUrl(route)
  if (!sitemapEntries.has(url)) {
    const parsed = lastmod ? new Date(lastmod) : null
    sitemapEntries.set(url, parsed && Number.isFinite(parsed.getTime()) ? parsed.toISOString().slice(0, 10) : null)
  }
}

function schemaBase() {
  return [
    { '@context': 'https://schema.org', '@type': 'Organization', name: 'CineSplit', url: `${siteUrl}/`, logo: `${siteUrl}/cinesplit-social.svg` },
    {
      '@context': 'https://schema.org',
      '@type': 'WebSite',
      name: 'CineSplit',
      url: `${siteUrl}/`,
      potentialAction: { '@type': 'SearchAction', target: `${siteUrl}/discover/?q={search_term_string}`, 'query-input': 'required name=search_term_string' },
    },
  ]
}

function makeBreadcrumb(items) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map(([name, route], index) => ({ '@type': 'ListItem', position: index + 1, name, item: absoluteUrl(route) })),
  }
}

function safeImage(image) {
  if (!image) return `${siteUrl}/cinesplit-social.svg`
  try {
    const parsed = new URL(image)
    return parsed.protocol === 'https:' ? parsed.href : `${siteUrl}/cinesplit-social.svg`
  } catch {
    return `${siteUrl}/cinesplit-social.svg`
  }
}

function layout(title, description, image, schema, article, noIndex = false) {
  const canonical = noIndex ? '' : absoluteUrl(article.route)
  const socialImage = safeImage(image)
  const schemas = noIndex ? [] : [...schemaBase(), ...schema].filter(Boolean)
  let html = baseHtml
  html = html.replace(/<title>[^<]*<\/title>/i, `<title>${htmlEscape(title)}</title>`)
  html = html.replace(/<meta\s+name="description"[^>]*>/i, `<meta name="description" content="${htmlEscape(description)}" />`)
  html = html.replace(/<meta\s+name="robots"[^>]*>/i, `<meta name="robots" content="${noIndex ? 'noindex, nofollow' : 'index, follow'}" />`)
  const tags = [
    ...(canonical ? [`<link rel="canonical" href="${htmlEscape(canonical)}" />`] : []),
    `<meta property="og:type" content="${htmlEscape(article.type || 'website')}" />`,
    `<meta property="og:title" content="${htmlEscape(title)}" />`,
    `<meta property="og:description" content="${htmlEscape(description)}" />`,
    ...(canonical ? [`<meta property="og:url" content="${htmlEscape(canonical)}" />`] : []),
    `<meta property="og:image" content="${htmlEscape(socialImage)}" />`,
    `<meta property="og:image:alt" content="${htmlEscape(image ? `${title} poster` : 'CineSplit brand image')}" />`,
    '<meta name="twitter:card" content="summary_large_image" />',
    `<meta name="twitter:title" content="${htmlEscape(title)}" />`,
    `<meta name="twitter:description" content="${htmlEscape(description)}" />`,
    `<meta name="twitter:image" content="${htmlEscape(socialImage)}" />`,
    `<meta name="twitter:image:alt" content="${htmlEscape(image ? `${title} poster` : 'CineSplit brand image')}" />`,
    `<script id="cinesplit-page-schema" type="application/ld+json">${jsonForHtml(schemas)}</script>`,
  ].join('\n    ')
  html = html.replace('</head>', `    ${tags}\n  </head>`)
  html = html.replace('<div id="root"></div>', `<main id="seo-prerender" class="seo-prerender">${article.body}</main>\n    <div id="root"></div>`)
  return html
}

async function writePage(route, data) {
  const normalized = route === '/' ? '/' : `/${route.replace(/^\/+|\/+$/g, '')}/`
  const segments = normalized.split('/').filter(Boolean)
  if (segments.some((segment) => !safeSegment(segment))) throw new Error(`Unsafe public route segment while prerendering: ${normalized}`)
  const target = segments.length ? path.join(distDir, ...segments, 'index.html') : path.join(distDir, 'index.html')
  await mkdir(path.dirname(target), { recursive: true })
  await writeFile(target, layout(data.title, data.description, data.image, data.schema || [], { ...data, route: normalized }, Boolean(data.noIndex)), 'utf8')
  renderedPaths.add(normalized)
  if (!data.noIndex) addSitemap(normalized, data.lastmod)
}

async function fetchJson(apiPath) {
  const url = `${apiRoot}/${apiPath.replace(/^\/+/, '')}`
  const response = await fetch(url, { headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(20000) })
  if (!response.ok) throw new Error(`SEO prerender API request failed (${response.status}): ${new URL(url).pathname}`)
  return response.json()
}

async function collectPages(apiPath) {
  const first = await fetchJson(`${apiPath}${apiPath.includes('?') ? '&' : '?'}page=1&page_size=100`)
  if (!Array.isArray(first.results)) throw new Error(`Expected a paginated public result from ${apiPath}.`)
  const results = [...first.results]
  for (let page = 2; page <= (first.pages || 1); page += 1) {
    const next = await fetchJson(`${apiPath}${apiPath.includes('?') ? '&' : '?'}page=${page}&page_size=100`)
    if (!Array.isArray(next.results)) throw new Error(`Expected a paginated public result from ${apiPath}.`)
    results.push(...next.results)
  }
  return results
}

async function mapLimit(items, concurrency, callback) {
  const output = new Array(items.length)
  let next = 0
  await Promise.all(Array.from({ length: Math.min(concurrency, items.length) }, async () => {
    while (next < items.length) {
      const index = next++
      output[index] = await callback(items[index], index)
    }
  }))
  return output
}

function pageBody({ title, image, description, facts = [], breadcrumbs = [], sections = [] }) {
  const crumbMarkup = breadcrumbs.length
    ? `<nav aria-label="Breadcrumb"><ol>${breadcrumbs.map(([label, route]) => `<li><a href="${htmlEscape(route)}">${htmlEscape(label)}</a></li>`).join('')}</ol></nav>`
    : ''
  const imageMarkup = image
    ? `<img src="${htmlEscape(image)}" alt="${htmlEscape(`${title} poster`)}" width="320" height="450" loading="eager" fetchpriority="high" />`
    : ''
  const factsMarkup = facts.length
    ? `<dl>${facts.map(([label, value]) => `<div><dt>${htmlEscape(label)}</dt><dd>${htmlEscape(value)}</dd></div>`).join('')}</dl>`
    : ''
  return `${crumbMarkup}<article><h1>${htmlEscape(title)}</h1>${imageMarkup}<p>${htmlEscape(description)}</p>${factsMarkup}${sections.join('')}</article>`
}

function linkedList(heading, items) {
  if (!items.length) return ''
  return `<section><h2>${htmlEscape(heading)}</h2><ul>${items.map(({ title, route, detail = '' }) => `<li><a href="${htmlEscape(route)}">${htmlEscape(title)}</a>${detail ? ` — ${htmlEscape(detail)}` : ''}</li>`).join('')}</ul></section>`
}

function movieJsonLd(movie, description) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Movie',
    name: movie.title,
    description,
    ...(movie.poster_url ? { image: movie.poster_url } : {}),
    ...(movie.genres?.length ? { genre: movie.genres } : {}),
    ...(movie.duration_minutes ? { duration: `PT${movie.duration_minutes}M` } : {}),
    ...(movie.original_language ? { inLanguage: movie.original_language } : {}),
    ...(movie.director ? { director: { '@type': 'Person', name: movie.director } } : {}),
    ...(movie.cast?.length ? { actor: movie.cast.map((name) => ({ '@type': 'Person', name })) } : {}),
    ...(movie.content_rating ? { contentRating: movie.content_rating } : {}),
  }
}

function episodeJsonLd(episode, series, description) {
  return {
    '@context': 'https://schema.org',
    '@type': 'TVEpisode',
    name: episode.title,
    description,
    ...(episode.poster_media?.secure_url ? { image: episode.poster_media.secure_url } : {}),
    ...(episode.type === 'regular' && episode.episode_number ? { episodeNumber: episode.episode_number } : {}),
    ...(episode.release_date ? { datePublished: episode.release_date } : {}),
    ...(episode.duration ? { duration: `PT${episode.duration}M` } : {}),
    partOfSeries: { '@type': 'TVSeries', name: series.title, url: absoluteUrl(`/series/${series.slug}/`) },
  }
}

async function writeNoIndexRoutes() {
  const routes = [
    ['/login/', 'Sign in | CineSplit'], ['/register/', 'Create an account | CineSplit'], ['/verify-email/', 'Verify your email | CineSplit'],
    ['/profile/', 'Your profile | CineSplit'], ['/favorites/', 'Your favorites | CineSplit'], ['/watch-history/', 'Watch history | CineSplit'], ['/continue-watching/', 'Continue watching | CineSplit'],
    ['/admin/', 'Studio dashboard | CineSplit'], ['/admin/movies/', 'Manage movies | CineSplit'], ['/admin/series/', 'Manage series | CineSplit'], ['/admin/media/', 'Media library | CineSplit'],
  ]
  for (const [route, title] of routes) {
    const segments = route.split('/').filter(Boolean)
    const target = path.join(distDir, ...segments, 'index.html')
    await mkdir(path.dirname(target), { recursive: true })
    let html = baseHtml.replace(/<title>[^<]*<\/title>/i, `<title>${htmlEscape(title)}</title>`)
      .replace(/<meta\s+name="robots"[^>]*>/i, '<meta name="robots" content="noindex, nofollow" />')
      .replace('<div id="root"></div>', '<div id="root"></div>')
    await writeFile(target, html, 'utf8')
  }
}

const baseHtml = await readFile(path.join(distDir, 'index.html'), 'utf8')
await writeFile(path.join(distDir, 'robots.txt'), robotsText(siteUrl ? `${siteUrl}/sitemap.xml` : ''), 'utf8')

if (!siteUrl) {
  await noDomainOutput()
  process.exit(0)
}

const movies = await collectPages('movies/')
const seriesList = await collectPages('series/')
const moviePages = await mapLimit(movies, 4, async (movie) => {
  if (!safeSegment(movie.slug)) return null
  const moviePath = `/movies/${movie.slug}/`
  const description = textDescription(movie.short_description || movie.description, `Explore ${movie.title} on CineSplit.`)
  const chapters = await fetchJson(`movies/${encodeURIComponent(movie.slug)}/chapters/`)
  const chapterLinks = Array.isArray(chapters) ? chapters.filter((chapter) => safeSegment(chapter.slug)).map((chapter) => ({
    title: `Chapter ${chapter.chapter_number}: ${chapter.title}`,
    route: `/movies/${movie.slug}/chapters/${chapter.slug}/`,
    detail: chapter.description,
  })) : []
  const sections = [
    movie.description && movie.description !== description ? `<section><h2>About ${htmlEscape(movie.title)}</h2><p>${htmlEscape(movie.description)}</p></section>` : '',
    linkedList('Chapters', chapterLinks),
  ].filter(Boolean)
  const facts = [
    ...(movie.release_year ? [['Release year', movie.release_year]] : []),
    ...(movie.duration_minutes ? [['Duration', `${movie.duration_minutes} minutes`]] : []),
    ...(movie.content_rating ? [['Content rating', movie.content_rating]] : []),
    ...(movie.genres?.length ? [['Genres', movie.genres.join(', ')]] : []),
    ...(movie.original_language ? [['Language', movie.original_language] ] : []),
  ]
  const movieTitle = `${movie.title}${movie.release_year ? ` (${movie.release_year})` : ''} | CineSplit`
  const schema = [movieJsonLd(movie, description), makeBreadcrumb([['Films', '/'], [movie.title, moviePath]])]
  await writePage(moviePath, {
    title: movieTitle, description, image: movie.poster_url, type: 'video.movie', schema,
    body: pageBody({ title: movie.title, image: movie.poster_url, description, facts, breadcrumbs: [['Films', '/']], sections }),
    lastmod: movie.updated_at,
    noIndex: description.length < 40,
  })
  for (const chapter of chapters || []) {
    if (!safeSegment(chapter.slug)) continue
    const route = `/movies/${movie.slug}/chapters/${chapter.slug}/`
    const chapterDescription = textDescription(chapter.description, `${chapter.title}, chapter ${chapter.chapter_number} of ${movie.title}.`)
    const chapterSchema = {
      '@context': 'https://schema.org', '@type': 'CreativeWork', name: chapter.title, description: chapterDescription,
      ...(chapter.duration ? { timeRequired: `PT${chapter.duration}M` } : {}),
      isPartOf: { '@type': 'Movie', name: movie.title, url: absoluteUrl(moviePath) },
    }
    await writePage(route, {
      title: `Chapter ${chapter.chapter_number}: ${chapter.title} | ${movie.title} | CineSplit`, description: chapterDescription,
      image: chapter.poster_media?.secure_url || movie.poster_url,
      schema: [chapterSchema, makeBreadcrumb([['Films', '/'], [movie.title, moviePath], [chapter.title, route]])],
      body: pageBody({ title: chapter.title, image: chapter.poster_media?.secure_url || movie.poster_url, description: chapterDescription,
        facts: [['Chapter', chapter.chapter_number], ...(chapter.duration ? [['Duration', `${chapter.duration} minutes`]] : [])],
        breadcrumbs: [['Films', '/'], [movie.title, moviePath]],
        sections: [movie.description ? `<section><h2>About ${htmlEscape(movie.title)}</h2><p>${htmlEscape(movie.description)}</p></section>` : ''],
      }),
      lastmod: chapter.updated_at,
      noIndex: String(chapter.description || '').trim().length < 40,
    })
  }
  return movie
})

const seriesPages = await mapLimit(seriesList, 4, async (series) => {
  if (!safeSegment(series.slug)) return null
  const seriesPath = `/series/${series.slug}/`
  const description = textDescription(series.short_description || series.description, `Explore ${series.title} on CineSplit.`)
  const [seasons, specials] = await Promise.all([
    fetchJson(`series/${encodeURIComponent(series.slug)}/seasons/`),
    fetchJson(`series/${encodeURIComponent(series.slug)}/specials/`),
  ])
  const episodeGroups = await mapLimit(seasons || [], 4, async (season) => ({ season, episodes: await fetchJson(`series/${encodeURIComponent(series.slug)}/seasons/${encodeURIComponent(season.slug)}/episodes/`) }))
  const uniqueEpisodes = new Map()
  const ambiguousEpisodeRoutes = new Set()
  const registerEpisode = (route, episode) => {
    if (ambiguousEpisodeRoutes.has(route)) return
    if (uniqueEpisodes.has(route)) {
      uniqueEpisodes.delete(route)
      ambiguousEpisodeRoutes.add(route)
      return
    }
    uniqueEpisodes.set(route, episode)
  }
  for (const group of episodeGroups) {
    for (const episode of group.episodes || []) {
      if (!safeSegment(episode.slug)) continue
      const route = `/series/${series.slug}/episodes/${episode.slug}/`
      registerEpisode(route, { ...episode, season_title: group.season.title || `Season ${group.season.season_number}` })
    }
  }
  for (const episode of specials || []) {
    if (!safeSegment(episode.slug)) continue
    const route = `/series/${series.slug}/episodes/${episode.slug}/`
    registerEpisode(route, episode)
  }
  const allEpisodeLinks = [...uniqueEpisodes.entries()].map(([route, episode]) => ({
    title: `${episode.type === 'special' ? `Special ${episode.special_number}` : `${episode.season_title}: Episode ${episode.episode_number}`} — ${episode.title}`,
    route,
    detail: episode.description,
  }))
  const groupedEpisodeLinks = new Map()
  for (const [route, episode] of uniqueEpisodes) {
    const heading = episode.type === 'special' ? 'Specials' : episode.season_title
    if (!groupedEpisodeLinks.has(heading)) groupedEpisodeLinks.set(heading, [])
    groupedEpisodeLinks.get(heading).push({
      title: episode.type === 'special' ? `Special ${episode.special_number}: ${episode.title}` : `Episode ${episode.episode_number}: ${episode.title}`,
      route,
      detail: episode.description,
    })
  }
  const sections = [
    series.description && series.description !== description ? `<section><h2>About ${htmlEscape(series.title)}</h2><p>${htmlEscape(series.description)}</p></section>` : '',
    ...[...groupedEpisodeLinks.entries()].map(([heading, links]) => linkedList(heading, links)),
  ].filter(Boolean)
  const facts = [
    ...(series.release_year ? [['Release year', series.release_year]] : []),
    ...(series.content_rating ? [['Content rating', series.content_rating]] : []),
    ...(series.genres?.length ? [['Genres', series.genres.join(', ')]] : []),
    ...(series.language ? [['Language', series.language]] : []),
    ...(seasons?.length ? [['Published seasons', seasons.length]] : []),
    ...(allEpisodeLinks.length ? [['Published episodes and specials', allEpisodeLinks.length]] : []),
  ]
  const seriesSchema = {
    '@context': 'https://schema.org', '@type': 'TVSeries', name: series.title, description,
    ...(series.poster_url ? { image: series.poster_url } : {}),
    ...(series.genres?.length ? { genre: series.genres } : {}),
    ...(series.release_year ? { startDate: String(series.release_year) } : {}),
    ...(series.language ? { inLanguage: series.language } : {}),
    ...(series.cast?.length ? { actor: series.cast.map((name) => ({ '@type': 'Person', name })) } : {}),
    ...(series.director ? { director: { '@type': 'Person', name: series.director } } : {}),
    ...(seasons?.length ? { numberOfSeasons: seasons.length, containsSeason: seasons.map((season) => ({ '@type': 'TVSeason', name: season.title || `Season ${season.season_number}`, seasonNumber: season.season_number })) } : {}),
  }
  await writePage(seriesPath, {
    title: `${series.title}${series.release_year ? ` (${series.release_year})` : ''} | CineSplit`, description,
    image: series.poster_url,
    schema: [seriesSchema, makeBreadcrumb([['Series', '/series/'], [series.title, seriesPath]])],
    body: pageBody({ title: series.title, image: series.poster_url, description, facts, breadcrumbs: [['Series', '/series/']], sections }),
    lastmod: series.updated_at,
    noIndex: description.length < 40,
  })
  for (const [route, episode] of uniqueEpisodes) {
    const episodeDescription = textDescription(episode.description, `${episode.title} from ${series.title}.`)
    const episodeLabel = episode.type === 'special'
      ? `Special ${episode.special_number}: ${episode.title}`
      : `${episode.season_title}, Episode ${episode.episode_number}: ${episode.title}`
    await writePage(route, {
      title: `${episodeLabel} | ${series.title} | CineSplit`, description: episodeDescription,
      image: episode.poster_media?.secure_url || series.poster_url,
      schema: [episodeJsonLd(episode, series, episodeDescription), makeBreadcrumb([['Series', '/series/'], [series.title, seriesPath], [episode.title, route]])],
      body: pageBody({ title: episode.title, image: episode.poster_media?.secure_url || series.poster_url, description: episodeDescription,
        facts: [
          ...(episode.type === 'special' ? [['Special number', episode.special_number]] : [['Season', episode.season_title], ['Episode', episode.episode_number]]),
          ...(episode.duration ? [['Duration', `${episode.duration} minutes`]] : []),
          ...(episode.release_date ? [['Release date', episode.release_date]] : []),
        ],
        breadcrumbs: [['Series', '/series/'], [series.title, seriesPath]],
      }),
      lastmod: episode.updated_at,
      noIndex: String(episode.description || '').trim().length < 40,
    })
  }
  return series
})

const validMovies = moviePages.filter(Boolean)
const validSeries = seriesPages.filter(Boolean)
const homeDescription = 'Discover films and series on CineSplit, with chapters, episodes, and stories to follow.'
const homeSections = [
  linkedList('Films', validMovies.slice(0, 12).map((movie) => ({ title: movie.title, route: `/movies/${movie.slug}/`, detail: movie.short_description }))),
  linkedList('Series', validSeries.slice(0, 12).map((series) => ({ title: series.title, route: `/series/${series.slug}/`, detail: series.short_description }))),
].filter(Boolean)
await writePage('/', {
  title: 'Films and series to follow | CineSplit', description: homeDescription, image: null, type: 'website',
  schema: [],
  body: pageBody({ title: 'Films and series to follow', description: homeDescription, sections: homeSections }),
})
const landingLinksMovies = validMovies.map((movie) => ({ title: movie.title, route: `/movies/${movie.slug}/`, detail: movie.short_description }))
const landingLinksSeries = validSeries.map((series) => ({ title: series.title, route: `/series/${series.slug}/`, detail: series.short_description }))
await writePage('/discover/', {
  title: 'Search films and series | CineSplit', description: 'Search CineSplit published films and series by title, genre, type, and release year.',
  schema: [], body: pageBody({ title: 'Search and discover', description: 'Search and explore published film and series listings on CineSplit.', sections: [linkedList('Films', landingLinksMovies), linkedList('Series', landingLinksSeries)] }),
})
await writePage('/series/', {
  title: 'Series to discover | CineSplit', description: 'Explore published CineSplit series, with seasons, episodes, and specials to follow.',
  schema: [], body: pageBody({ title: 'Discover series', description: 'Browse published series and explore their seasons, episodes, and specials.', sections: [linkedList('Published series', landingLinksSeries)] }),
})

await writeNoIndexRoutes()
const notFoundHtml = baseHtml
  .replace(/<title>[^<]*<\/title>/i, '<title>Page not found | CineSplit</title>')
  .replace(/<meta\s+name="robots"[^>]*>/i, '<meta name="robots" content="noindex, nofollow" />')
  .replace('<div id="root"></div>', '<main id="seo-prerender" class="seo-prerender"><h1>Page not found</h1><p>This page is not available on CineSplit.</p><a href="/">Return to CineSplit</a></main><div id="root"></div>')
await writeFile(path.join(distDir, '404.html'), notFoundHtml, 'utf8')

const sitemapUrls = [...sitemapEntries.entries()]
const chunks = []
for (let index = 0; index < sitemapUrls.length; index += requiredSitemapUrlLimit) chunks.push(sitemapUrls.slice(index, index + requiredSitemapUrlLimit))
if (chunks.length > 50000) throw new Error('Sitemap index count exceeds the protocol limit; generation stopped.')
if (chunks.length <= 1) {
  const rows = sitemapUrls.map(([loc, lastmod]) => `  <url><loc>${htmlEscape(loc)}</loc>${lastmod ? `<lastmod>${lastmod}</lastmod>` : ''}</url>`).join('\n')
  await writeFile(path.join(distDir, 'sitemap.xml'), `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${rows}\n</urlset>\n`, 'utf8')
} else {
  const indexes = []
  for (let index = 0; index < chunks.length; index += 1) {
    const name = `sitemap-${index + 1}.xml`
    const rows = chunks[index].map(([loc, lastmod]) => `  <url><loc>${htmlEscape(loc)}</loc>${lastmod ? `<lastmod>${lastmod}</lastmod>` : ''}</url>`).join('\n')
    await writeFile(path.join(distDir, name), `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${rows}\n</urlset>\n`, 'utf8')
    indexes.push(`  <sitemap><loc>${siteUrl}/${name}</loc></sitemap>`)
  }
  await writeFile(path.join(distDir, 'sitemap.xml'), `<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${indexes.join('\n')}\n</sitemapindex>\n`, 'utf8')
}

console.log(`SEO prerendered ${renderedPaths.size} public HTML routes and ${sitemapUrls.length} sitemap URLs for ${siteUrl}.`)
