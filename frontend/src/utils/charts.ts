import type { MonthlyReport, YearlyReport } from '@/types';
import { MONTHS_SHORT } from './format';

export function daysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate();
}

/** যেসব দিনে বিক্রি নেই সেগুলোও 0 দিয়ে ভরে chart-এর জন্য পূর্ণ মাসের data বানায় */
export function fillDaily(year: number, month: number, daily: MonthlyReport['daily']) {
  const map = new Map(daily.map((d) => [d.day, Number(d.grand_total)]));
  return Array.from({ length: daysInMonth(year, month) }, (_, i) => ({
    label: String(i + 1),
    total: map.get(i + 1) ?? 0,
  }));
}

export function fillMonthly(monthly: YearlyReport['monthly']) {
  const map = new Map(monthly.map((m) => [m.month, Number(m.grand_total)]));
  return MONTHS_SHORT.map((label, i) => ({ label, total: map.get(i + 1) ?? 0 }));
}

export const CHART_COLORS = ['#4f46e5', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444'];
