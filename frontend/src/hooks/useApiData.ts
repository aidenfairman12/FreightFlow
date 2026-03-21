import { useState, useEffect, useCallback, useRef } from 'react'
import type { ApiResponse } from '@/types'

interface UseApiDataOptions {
  refreshInterval?: number
}

interface UseApiDataResult<T> {
  data: T | null
  error: string | null
  loading: boolean
  refresh: () => void
}

export function useApiData<T>(
  fetcher: () => Promise<ApiResponse<T>>,
  options?: UseApiDataOptions,
): UseApiDataResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const doFetch = useCallback(async (isInitial = false) => {
    if (isInitial) setLoading(true)
    try {
      const res = await fetcherRef.current()
      if (res.error) {
        setError(res.error)
      } else {
        setData(res.data)
        setError(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      if (isInitial) setLoading(false)
    }
  }, [])

  useEffect(() => {
    doFetch(true)

    if (options?.refreshInterval) {
      const id = setInterval(() => doFetch(false), options.refreshInterval)
      return () => clearInterval(id)
    }
  }, [doFetch, options?.refreshInterval])

  const refresh = useCallback(() => doFetch(true), [doFetch])

  return { data, error, loading, refresh }
}
