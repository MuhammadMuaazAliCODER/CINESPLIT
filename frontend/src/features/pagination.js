export function clampPage(page, pages) {
  if (!Number.isInteger(pages) || pages < 1) return 1
  return Math.min(Math.max(1, page), pages)
}

export function nextPage(page, pages) {
  return clampPage(page + 1, pages)
}

export function previousPage(page, pages) {
  return clampPage(page - 1, pages)
}
