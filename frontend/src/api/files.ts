import { api } from './client';

/** Backend থেকে ফাইল (PDF/CSV) blob হিসেবে আনে — JWT header লাগে, তাই সরাসরি link খোলা যায় না */
async function fetchBlob(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<Blob> {
  const { data } = await api.get<Blob>(path, { responseType: 'blob', params });
  return data;
}

/** PDF নতুন ট্যাবে খোলে (সেখান থেকে print / save করা যায়) */
export async function openPdf(path: string): Promise<void> {
  // popup blocker এড়াতে ক্লিকের সাথে সাথেই ট্যাব খুলি, পরে URL বসাই
  const tab = window.open('', '_blank');
  try {
    const blob = await fetchBlob(path);
    const url = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
    if (tab) tab.location.href = url;
    else window.location.href = url;
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch (err) {
    tab?.close();
    throw err;
  }
}

/** ফাইল ডাউনলোড করে */
export async function downloadFile(
  path: string,
  filename: string,
  params?: Record<string, string | number | boolean | undefined>,
): Promise<void> {
  const blob = await fetchBlob(path, params);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 10_000);
}
