import type { ExportResult } from "../engine/types";

/** Decode the base64 of an `export_report` result. */
export function base64ToBytes(b64: string): Uint8Array<ArrayBuffer> {
  const bin = atob(b64);
  const bytes = new Uint8Array(new ArrayBuffer(bin.length));
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

/** The exported file as a Blob of its MIME type. */
export function fileBlob(file: ExportResult): Blob {
  return new Blob([base64ToBytes(file.base64)], { type: file.mime });
}

/** Save an exported file through the browser's download (a Blob URL and a temporary link). */
export function downloadFile(file: ExportResult): void {
  const url = URL.createObjectURL(fileBlob(file));
  const link = document.createElement("a");
  link.href = url;
  link.download = file.filename;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Script that opens the print dialog once the report page has loaded. */
const PRINT_SCRIPT = '<script>addEventListener("load",function(){print();});</script>';

/** The report HTML with a script that calls `print()` after load (before `</body>`). */
export function withPrintScript(html: string): string {
  const at = html.toLowerCase().lastIndexOf("</body>");
  return at < 0 ? html + PRINT_SCRIPT : html.slice(0, at) + PRINT_SCRIPT + html.slice(at);
}

/**
 * Show the exported HTML report in `win` (a window opened inside the click, so the
 * browser does not block it) from a Blob URL; the page calls `print()` after load.
 */
export function printReport(win: Pick<Window, "location">, file: ExportResult): void {
  const html = new TextDecoder().decode(base64ToBytes(file.base64));
  const blob = new Blob([withPrintScript(html)], { type: "text/html" });
  win.location.replace(URL.createObjectURL(blob));
}
