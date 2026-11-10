// frontend/app/hooks/useNews.ts
'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { LiveNewsData, LiveNewsResponse } from '@/app/types/country';

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');

// Backend caches news for 5 minutes — we refetch every 5 minutes + on demand
const REFRESH_INTERVAL_MS = 5 * 60 * 1000;
const FETCH_TIMEOUT_MS = 20_000; // 20s hard cap

interface UseNewsResult {
  news: LiveNewsData | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Fetch live news for a country from /api/news/country/{id}.
 *
 * Behaviour:
 * - Fetches when countryId changes (non-null)
 * - Silent background refresh every 5 minutes
 * - Manual `refresh()` for user-triggered reload
 * - Aborts in-flight request on unmount / id change
 * - Never throws — errors go into `error` state
 */
export const useNews = (countryId: string | null | undefined): UseNewsResult => {
  const [news, setNews] = useState<LiveNewsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  const fetchNews = useCallback(
    async (id: string, silent = false) => {
      if (!id) return;

      // Cancel previous in-flight request
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

      if (!silent && mountedRef.current) {
        setLoading(true);
        setError(null);
      }

      try {
        const url = `${API_BASE}/api/news/country/${encodeURIComponent(id.toLowerCase())}`;
        const response = await fetch(url, {
          signal: controller.signal,
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        });

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error(`No news available for '${id}'`);
          }
          throw new Error(`HTTP ${response.status}`);
        }

        const result: LiveNewsResponse = await response.json();

        if (!mountedRef.current) return;

        if (result.success && result.data) {
          setNews(result.data);
          setError(null);
        } else {
          setError(result.error || 'Failed to parse news response');
        }
      } catch (err) {
        if (!mountedRef.current) return;

        // AbortError is expected during cleanup — don't show as user error
        if (err instanceof DOMException && err.name === 'AbortError') {
          return;
        }

        if (!silent) {
          setError(err instanceof Error ? err.message : 'Unknown error');
        }
      } finally {
        clearTimeout(timeoutId);
        if (!silent && mountedRef.current) {
          setLoading(false);
        }
      }
    },
    []
  );

  // Main effect: fetch on id change + set up polling
  useEffect(() => {
    mountedRef.current = true;

    if (!countryId) {
      setNews(null);
      setError(null);
      setLoading(false);
      return;
    }

    // Initial fetch
    fetchNews(countryId, false);

    // Periodic background refresh
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = setInterval(() => {
      if (countryId) fetchNews(countryId, true);
    }, REFRESH_INTERVAL_MS);

    return () => {
      mountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      abortRef.current?.abort();
      abortRef.current = null;
    };
  }, [countryId, fetchNews]);

  const refresh = useCallback(() => {
    if (countryId) fetchNews(countryId, false);
  }, [countryId, fetchNews]);

  return { news, loading, error, refresh };
};