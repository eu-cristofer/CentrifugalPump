import type { PumpflowDoc } from "../engine/types";

/** Parse the text of a `.pumpflow` file; throws a readable error if it is not one. */
export function parseProject(text: string): PumpflowDoc {
  let doc: unknown;
  try {
    doc = JSON.parse(text);
  } catch {
    throw new Error("This file is not valid JSON.");
  }
  if (
    typeof doc !== "object" ||
    doc === null ||
    Array.isArray(doc) ||
    !Array.isArray((doc as PumpflowDoc).nodes)
  ) {
    throw new Error("This file is not a PumpFlow project (no nodes list).");
  }
  return doc as PumpflowDoc;
}

export async function readProjectFile(file: File): Promise<PumpflowDoc> {
  return parseProject(await file.text());
}

export function projectFileName(name: string): string {
  const base = name.trim() || "project";
  return base.endsWith(".pumpflow") ? base : `${base}.pumpflow`;
}

interface SaveHandle {
  name: string;
  createWritable(): Promise<{ write(data: string): Promise<void>; close(): Promise<void> }>;
}
type SavePicker = (options: {
  suggestedName: string;
  types: Array<{ description: string; accept: Record<string, string[]> }>;
}) => Promise<SaveHandle>;

/**
 * Save `text`: the File System Access picker when available, otherwise a
 * download.  Returns the saved file name, or `null` if the user cancelled.
 */
export async function saveProjectText(text: string, name: string): Promise<string | null> {
  const fileName = projectFileName(name);
  if ("showSaveFilePicker" in window) {
    const picker = (window as unknown as { showSaveFilePicker: SavePicker }).showSaveFilePicker;
    try {
      const handle = await picker.call(window, {
        suggestedName: fileName,
        types: [{ description: "PumpFlow project", accept: { "application/json": [".pumpflow"] } }],
      });
      const writable = await handle.createWritable();
      await writable.write(text);
      await writable.close();
      return handle.name;
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return null;
      throw err;
    }
  }
  const url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return fileName;
}
