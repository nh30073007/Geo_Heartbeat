// frontend/app/hooks/useCountry.ts
import { useState, useCallback, useEffect, useRef } from 'react';
import { CountryDashboardData, CountryResponse } from '@/app/types/country';

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');

const POLL_INTERVAL_MS = 2000;

export const useCountry = () => {
  const [data, setData] = useState<CountryDashboardData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState<string | null>(null);
  const [round, setRound] = useState<number | null>(null);

  const activeCountryRef = useRef<string | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchOnce = useCallback(async (countryId: string, silent = false) => {
    if (!countryId) return;

    if (!silent) setLoading(true);
    setError(null);

    try {
      const url = `${API_BASE}/api/country/${countryId.toLowerCase()}`;
      const response = await fetch(url, { cache: 'no-store' });

      if (!response.ok) {
        if (response.status === 404) throw new Error(`Country '${countryId}' not found`);
        throw new Error(`HTTP ${response.status}`);
      }

      const result: CountryResponse = await response.json();
      if (result.success && result.data) {
        setData(result.data);
        setSource((result.data as any)._source ?? null);
        setRound((result.data as any)._round ?? null);
      } else {
        setError('Failed to fetch country data');
      }
    } catch (err) {
      if (!silent) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      }
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  const fetchCountry = useCallback(async (countryId: string) => {
    if (!countryId) return;
    activeCountryRef.current = countryId;

    await fetchOnce(countryId, false);

    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }

    pollTimerRef.current = setInterval(() => {
      if (activeCountryRef.current) {
        fetchOnce(activeCountryRef.current, true);
      }
    }, POLL_INTERVAL_MS);
  }, [fetchOnce]);

  /** Force an immediate refresh (used by WebSocket state_update) */
  const refresh = useCallback(() => {
    if (activeCountryRef.current) {
      fetchOnce(activeCountryRef.current, true);
    }
  }, [fetchOnce]);

  const reset = useCallback(() => {
    activeCountryRef.current = null;
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    setData(null);
    setError(null);
    setLoading(false);
    setSource(null);
    setRound(null);
  }, []);

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, []);

  return { data, loading, error, fetchCountry, reset, refresh, source, round };
};