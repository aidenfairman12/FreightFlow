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

    if (!options?.refreshInterval) return

    const interval = options.refreshInterval

    let id: ReturnType<typeof setInterval> | null = null

    const start = () => {
      if (!id) id = setInterval(() => doFetch(false), interval)
    }
    const stop = () => {
      if (id) { clearInterval(id); id = null }
    }

    const onVisibility = () => {
      if (document.hidden) {
        stop()
      } else {
        doFetch(false)
        start()
      }
    }

    start()
    document.addEventListener('visibilitychange', onVisibility)

    return () => {
      stop()
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [doFetch, options?.refreshInterval])

  const refresh = useCallback(() => doFetch(true), [doFetch])

  return { data, error, loading, refresh }
}
