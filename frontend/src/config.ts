/**
 * Runtime URLs and contact details, configurable via Vite env vars.
 * Defaults work for local development.
 */
const stripTrailingSlash = (url: string) => url.replace(/\/+$/, '')

/** Base URL where generated sites are served, e.g. https://sites.example.com */
export const SITES_BASE_URL = stripTrailingSlash(
  import.meta.env.VITE_SITES_BASE_URL || 'http://localhost:8000'
)

/** SITES_BASE_URL without the scheme, for display (e.g. sites.example.com) */
export const SITES_HOST = SITES_BASE_URL.replace(/^https?:\/\//, '')

/** Base URL of this web app (admin + customer portal) */
export const PORTAL_URL = stripTrailingSlash(
  import.meta.env.VITE_PORTAL_URL || window.location.origin
)

/** Public contact / support email address */
export const CONTACT_EMAIL = import.meta.env.VITE_CONTACT_EMAIL || 'hello@example.com'
