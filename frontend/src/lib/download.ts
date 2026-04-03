type SaveFilePickerOptions = {
  suggestedName?: string;
  types?: Array<{
    description?: string;
    accept: Record<string, string[]>;
  }>;
  excludeAcceptAllOption?: boolean;
};

export function getFilenameFromContentDisposition(
  header: string | null,
  fallback: string
): string {
  if (!header) return fallback;

  const utf8Match = header.match(/filename\*=(?:UTF-8''|utf-8'')([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1].replace(/["']/g, ""));
    } catch {
      return utf8Match[1].replace(/["']/g, "");
    }
  }

  const asciiMatch = header.match(/filename="?([^"]+)"?/i);
  return asciiMatch?.[1] || fallback;
}

export async function downloadBlob(blob: Blob, filename: string): Promise<void> {
  const savePicker = (window as Window & {
    showSaveFilePicker?: (options?: SaveFilePickerOptions) => Promise<any>;
  }).showSaveFilePicker;

  if (savePicker) {
    try {
      const handle = await savePicker({
        suggestedName: filename,
      });
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      return;
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      console.warn("Falling back to browser download", error);
    }
  }

  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(objectUrl);
}
