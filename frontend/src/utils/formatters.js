/**
 * Format seconds to human readable duration
 */
export function formatDuration(seconds) {
    if (!seconds || seconds === 0) return '0s'

    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)

    if (mins === 0) return `${secs}s`
    return `${mins}m ${secs}s`
}

/**
 * Format date to relative time
 */
export function formatRelativeTime(dateString) {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`

    return date.toLocaleDateString()
}

/**
 * Format date to standard format
 */
export function formatDate(dateString) {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    })
}

/**
 * Format phone number
 */
export function formatPhoneNumber(phone) {
    if (!phone) return '-'
    // Remove all non-digits
    const cleaned = phone.replace(/\D/g, '')

    // Format based on length
    if (cleaned.length === 10) {
        return `(${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`
    }
    return phone
}

/**
 * Format percentage
 */
export function formatPercentage(value, decimals = 1) {
    if (value === null || value === undefined) return '0%'
    return `${Number(value).toFixed(decimals)}%`
}

/**
 * Format large numbers with K/M suffix
 */
export function formatNumber(num) {
    if (num === null || num === undefined) return '0'
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toString()
}

/**
 * Get qualification badge color class
 */
export function getQualificationBadge(qualification) {
    switch (qualification?.toLowerCase()) {
        case 'hot':
            return 'badge badge-hot'
        case 'warm':
            return 'badge badge-warm'
        case 'cold':
            return 'badge badge-cold'
        default:
            return 'badge badge-inactive'
    }
}

/**
 * Get status badge color class
 */
export function getStatusBadge(status) {
    switch (status?.toLowerCase()) {
        case 'completed':
            return 'badge badge-active'
        case 'in_progress':
        case 'ringing':
            return 'badge badge-warm'
        case 'failed':
        case 'no_answer':
            return 'badge badge-hot'
        default:
            return 'badge badge-inactive'
    }
}

/**
 * Get language display name
 */
export function getLanguageDisplay(language) {
    const names = {
        english: 'English',
        tamil: 'தமிழ்',
        tanglish: 'Tanglish',
    }
    return names[language?.toLowerCase()] || language || 'Unknown'
}

/**
 * Truncate text with ellipsis
 */
export function truncateText(text, maxLength = 50) {
    if (!text) return ''
    if (text.length <= maxLength) return text
    return text.slice(0, maxLength) + '...'
}
