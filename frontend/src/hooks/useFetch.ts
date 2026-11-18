import { useEffect, useState } from 'react';
import type { DependencyList } from 'react';
import { api } from '@/api/client';
import type { Paginated } from '@/types';
import { parseError } from '@/utils/errors';

export function useFetch<T>(fetcher: () => Promise<T>, deps: DependencyList = []) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    fetcher()
      .then((result) => {
        if (active) setData(result);
      })
      .catch((err) => {
        if (active) setError(parseError(err).message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  return { data, loading, error, reload: () => setTick((t) => t + 1) };
}

export type Params = Record<string, string | number | boolean | null | undefined>;

export function cleanParams(params: Params): Record<string, string | number | boolean> {
  const out: Record<string, string | number | boolean> = {};
  for (const [k, v] of Object.entries(params)) {
    if (v !== '' && v !== null && v !== undefined && v !== false) out[k] = v;
  }
  return out;
}

/** Paginated list API-এর জন্য: filter বদলালে page স্বয়ংক্রিয়ভাবে ১-এ ফিরে যায় */
export function usePagedList<T>(endpoint: string, params: Params = {}) {
  const key = JSON.stringify(params);
  const [state, setState] = useState({ key, page: 1 });
  const page = state.key === key ? state.page : 1;
  const setPage = (p: number) => setState({ key, page: p });

  const result = useFetch<Paginated<T>>(async () => {
    const { data } = await api.get<Paginated<T>>(endpoint, {
      params: cleanParams({ ...params, page }),
    });
    return data;
  }, [endpoint, key, page]);

  return { ...result, page, setPage };
}
