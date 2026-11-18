const TZ = 'Asia/Dhaka';

export function money(value: string | number | null | undefined): string {
  const n = Number(value ?? 0);
  const safe = Number.isFinite(n) ? n : 0;
  return (
    '৳ ' +
    safe.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  );
}

export function compactMoney(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `৳${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `৳${(value / 1_000).toFixed(1)}k`;
  return `৳${value.toFixed(0)}`;
}

export function fmtDate(iso?: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: TZ,
  });
}

export function fmtDateTime(iso?: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: TZ,
  });
}

/** আজকের তারিখ YYYY-MM-DD (Asia/Dhaka) */
export function todayISO(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: TZ });
}

export function fullName(u: { first_name: string; last_name: string; username: string }): string {
  const name = `${u.first_name} ${u.last_name}`.trim();
  return name || u.username;
}

export const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];
export const MONTHS_SHORT = MONTHS.map((m) => m.slice(0, 3));

export const PAYMENT_LABEL: Record<string, string> = {
  cash: 'Cash',
  card: 'Card',
  mobile_banking: 'Mobile Banking',
};

export function greeting(): string {
  const hour = Number(
    new Date().toLocaleString('en-GB', { hour: '2-digit', hour12: false, timeZone: TZ }),
  );
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}
