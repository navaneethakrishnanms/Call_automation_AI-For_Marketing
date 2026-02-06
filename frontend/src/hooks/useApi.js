import { useState, useEffect, useCallback } from 'react'

/**
 * Custom hook for API calls with loading and error states
 */
export function useApi(apiFn, immediate = true) {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(immediate)
    const [error, setError] = useState(null)

    const execute = useCallback(async (...args) => {
        setLoading(true)
        setError(null)
        try {
            const result = await apiFn(...args)
            setData(result)
            return result
        } catch (err) {
            setError(err.response?.data?.detail || err.message || 'An error occurred')
            throw err
        } finally {
            setLoading(false)
        }
    }, [apiFn])

    const reset = useCallback(() => {
        setData(null)
        setError(null)
        setLoading(false)
    }, [])

    return { data, loading, error, execute, reset, setData }
}

/**
 * Hook for fetching with automatic execution on mount
 */
export function useFetch(apiFn, deps = []) {
    const { data, loading, error, execute, setData } = useApi(apiFn, true)

    useEffect(() => {
        execute()
    }, deps)

    const refetch = useCallback(() => execute(), [execute])

    return { data, loading, error, refetch, setData }
}

/**
 * Hook for paginated data
 */
export function usePagination(apiFn, initialPage = 1, initialPageSize = 10) {
    const [page, setPage] = useState(initialPage)
    const [pageSize, setPageSize] = useState(initialPageSize)
    const [filters, setFilters] = useState({})

    const { data, loading, error, execute } = useApi(apiFn, false)

    const fetchPage = useCallback(async (params = {}) => {
        return execute({ page, page_size: pageSize, ...filters, ...params })
    }, [execute, page, pageSize, filters])

    useEffect(() => {
        fetchPage()
    }, [page, pageSize, filters])

    const nextPage = () => setPage(p => p + 1)
    const prevPage = () => setPage(p => Math.max(1, p - 1))
    const goToPage = (n) => setPage(n)

    return {
        data,
        loading,
        error,
        page,
        pageSize,
        setPageSize,
        nextPage,
        prevPage,
        goToPage,
        filters,
        setFilters,
        refetch: fetchPage,
    }
}
