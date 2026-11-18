import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api';

const ACCESS_KEY = 'ips_access_token';
const REFRESH_KEY = 'ips_refresh_token';

export const tokenStore = {
  getAccess: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

let unauthorizedHandler: (() => void) | null = null;
export function setUnauthorizedHandler(fn: (() => void) | null) {
  unauthorizedHandler = fn;
}

export const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  const token = tokenStore.getAccess();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const refresh = tokenStore.getRefresh();
  if (!refresh) throw new Error('No refresh token');
  const { data } = await axios.post(`${API_URL}/auth/refresh/`, { refresh });
  // Backend refresh token rotate করে, তাই নতুন refresh token-ও সংরক্ষণ করতে হবে
  tokenStore.set(data.access, data.refresh);
  return data.access as string;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    const url = original?.url ?? '';
    const isAuthCall = url.includes('/auth/login') || url.includes('/auth/refresh');

    if (error.response?.status === 401 && original && !original._retry && !isAuthCall) {
      if (tokenStore.getRefresh()) {
        original._retry = true;
        try {
          if (!refreshPromise) {
            refreshPromise = refreshAccessToken().finally(() => {
              refreshPromise = null;
            });
          }
          const access = await refreshPromise;
          original.headers.Authorization = `Bearer ${access}`;
          return api(original);
        } catch {
          // refresh ব্যর্থ — session শেষ
        }
      }
      tokenStore.clear();
      unauthorizedHandler?.();
    }
    return Promise.reject(error);
  },
);
