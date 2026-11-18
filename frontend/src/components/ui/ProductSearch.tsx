import { useEffect, useState } from 'react';
import { Package, Search } from 'lucide-react';
import { api } from '@/api/client';
import { useDebounce } from '@/hooks/useDebounce';
import type { Paginated, Product } from '@/types';
import { money } from '@/utils/format';

/** নাম বা SKU লিখে product খোঁজার dropdown (server-side search) */
export function ProductSearch({
  onSelect,
  placeholder = 'Search product by name or SKU…',
  autoFocus = false,
}: {
  onSelect: (product: Product) => void;
  placeholder?: string;
  autoFocus?: boolean;
}) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Product[]>([]);
  const debounced = useDebounce(query, 300);

  useEffect(() => {
    if (!open) return;
    let active = true;
    setLoading(true);
    api
      .get<Paginated<Product>>('/products/', {
        params: { search: debounced || undefined, is_active: true, page_size: 8 },
      })
      .then(({ data }) => {
        if (active) setResults(data.results);
      })
      .catch(() => {
        if (active) setResults([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [debounced, open]);

  return (
    <div className="relative">
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
      <input
        className="input pl-9"
        value={query}
        autoFocus={autoFocus}
        placeholder={placeholder}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
      />
      {open && (
        <div className="absolute z-30 mt-1 max-h-72 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg">
          {loading && results.length === 0 && (
            <p className="px-3 py-3 text-sm text-slate-500">Searching…</p>
          )}
          {!loading && results.length === 0 && (
            <p className="px-3 py-3 text-sm text-slate-500">No products found.</p>
          )}
          {results.map((p) => (
            <button
              type="button"
              key={p.id}
              // mousedown preventDefault দিলে input blur হয় না, ফলে click ঠিকমতো কাজ করে
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                onSelect(p);
                setQuery('');
                setOpen(false);
              }}
              className="flex w-full items-center gap-3 px-3 py-2 text-left text-sm hover:bg-brand-50"
            >
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
                <Package className="h-4 w-4" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium text-slate-800">{p.name}</span>
                <span className="block text-xs text-slate-500">
                  {p.sku} · Stock {p.stock_quantity}
                </span>
              </span>
              <span className="text-xs font-medium text-slate-600">{money(p.selling_price)}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
