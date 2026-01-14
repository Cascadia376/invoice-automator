import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number | string | undefined | null): string {
  const num = Number(value);
  if (isNaN(num)) return "$ 0.00";

  // User specifically requested "$ 0.00" format (with space)
  // Standard en-US/en-CA is usually "$0.00" (no space)
  // We will manually format to ensure exact compliance with request if standard doesn't match,
  // OR use Intl and Replace.
  // Let's stick to standard Intl for reliability, but checking if we can add space.

  return new Intl.NumberFormat('en-CA', {
    style: 'currency',
    currency: 'CAD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(num).replace('CA$', '$').replace('$', '$ ');
}
