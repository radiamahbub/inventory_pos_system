import axios from 'axios';

export interface ParsedError {
  message: string;
  fields: Record<string, string>;
}

function flatten(value: unknown): string {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) {
    return value.map(flatten).filter(Boolean).join(' ');
  }
  if (typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>)
      .map(([k, v]) => {
        const text = flatten(v);
        return text ? `${k.replace(/_/g, ' ')}: ${text}` : '';
      })
      .filter(Boolean)
      .join(' ');
  }
  return String(value);
}

/** DRF error response কে ইউজার-বান্ধব message ও field-wise error-এ রূপান্তর করে */
export function parseError(err: unknown): ParsedError {
  if (!axios.isAxiosError(err)) {
    return { message: err instanceof Error ? err.message : 'Something went wrong.', fields: {} };
  }
  if (!err.response) {
    return {
      message: 'Cannot reach the server. Please check that the backend is running.',
      fields: {},
    };
  }
  const { status, data } = err.response;
  const fields: Record<string, string> = {};
  let message = '';

  if (data && typeof data === 'object' && !Array.isArray(data)) {
    const obj = data as Record<string, unknown>;
    if (typeof obj.detail === 'string') {
      message = obj.detail;
    } else {
      for (const [key, value] of Object.entries(obj)) {
        const text = flatten(value);
        if (text) fields[key] = text;
      }
      message =
        fields.non_field_errors ??
        fields.items ??
        Object.entries(fields)
          .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`)
          .join(' · ');
    }
  } else if (Array.isArray(data)) {
    message = flatten(data);
  }

  if (!message) {
    if (status === 401) message = 'Your session has expired. Please sign in again.';
    else if (status === 403) message = 'You do not have permission to perform this action.';
    else if (status === 404) message = 'The requested record was not found.';
    else if (status >= 500) message = 'Server error. Please try again later.';
    else message = 'Request failed. Please try again.';
  }
  return { message, fields };
}
