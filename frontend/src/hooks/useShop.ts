import { useEffect, useState } from 'react';
import { api } from '@/api/client';
import type { ShopInfo } from '@/types';

const FALLBACK: ShopInfo = { name: 'Inventory POS', address: '', phone: '', footer: 'Thank you for your purchase!' };
let cached: ShopInfo | null = null;

/** দোকানের নাম/ঠিকানা/ফোন (backend .env থেকে) — একবার আনলে cache হয় */
export function useShop(): ShopInfo {
  const [shop, setShop] = useState<ShopInfo>(cached ?? FALLBACK);
  useEffect(() => {
    if (cached) return;
    api
      .get<ShopInfo>('/shop/')
      .then(({ data }) => {
        cached = data;
        setShop(data);
      })
      .catch(() => undefined);
  }, []);
  return shop;
}
