/**
 * Formatting Utilities
 * 
 * Common formatting functions for numbers, currency, dates, etc.
 */

/**
 * Format a number with thousands separators
 * @example formatNumber(1234567) => "1,234,567"
 */
export function formatNumber(value: number | undefined | null): string {
  if (value === undefined || value === null) return '0'
  return value.toLocaleString()
}

/**
 * Format a value as US currency
 * @example formatCurrency(1234.56) => "$1,234.56"
 */
export function formatCurrency(value: number | undefined | null): string {
  if (value === undefined || value === null) return '$0.00'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value)
}

const CST_TIMEZONE = 'America/Chicago'

/**
 * Format a date as a localized string in CST
 * @example formatDate("2024-01-22T18:30:00Z") => "Jan 22, 2024"
 */
export function formatDate(date: string | Date | undefined | null): string {
  if (!date) return 'N/A'
  
  const dateObj = typeof date === 'string' ? new Date(date) : date
  
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: CST_TIMEZONE,
  }).format(dateObj)
}

/**
 * Format a date with time in CST
 * @example formatDateTime("2024-01-22T18:30:00Z") => "Jan 22, 2024 at 12:30 PM CST"
 */
export function formatDateTime(date: string | Date | undefined | null): string {
  if (!date) return 'N/A'
  
  const dateObj = typeof date === 'string' ? new Date(date) : date
  
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: CST_TIMEZONE,
    timeZoneName: 'short',
  }).format(dateObj)
}

/**
 * Format a date with time in CST (short form, no timezone suffix)
 * @example formatDateTimeShort("2024-01-22T18:30:00Z") => "Jan 22, 2024, 12:30 PM"
 */
export function formatDateTimeShort(date: string | Date | undefined | null): string {
  if (!date) return 'N/A'
  
  const dateObj = typeof date === 'string' ? new Date(date) : date
  
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: CST_TIMEZONE,
  }).format(dateObj)
}

/**
 * Format a percentage value
 * @example formatPercentage(0.8542) => "85.4%"
 */
export function formatPercentage(
  value: number | undefined | null,
  decimals: number = 1
): string {
  if (value === undefined || value === null) return '0%'
  return `${(value * 100).toFixed(decimals)}%`
}

/**
 * Format a large number with abbreviations (K, M, B)
 * @example formatCompact(1234567) => "1.2M"
 */
export function formatCompact(value: number | undefined | null): string {
  if (value === undefined || value === null) return '0'
  
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)}B`
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`
  }
  
  return value.toFixed(0)
}

/**
 * Format a duration in milliseconds to human readable format
 * @example formatDuration(125000) => "2m 5s"
 */
export function formatDuration(ms: number | undefined | null): string {
  if (!ms) return '0s'
  
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`
  }
  return `${seconds}s`
}

/**
 * Truncate text to a maximum length
 * @example truncate("This is a long text", 10) => "This is a..."
 */
export function truncate(
  text: string | undefined | null,
  maxLength: number,
  suffix: string = '...'
): string {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength - suffix.length) + suffix
}

