// Shared by the browser worker and scripts/parity.mjs (Node): boots Pyodide from
// local files only, installs the vendored wheels and returns a JSON call helper.
// No micropip, no network.

/**
 * @typedef {Object} BootOptions
 * @property {(options: {indexURL: string}) => Promise<any>} loadPyodide
 * @property {string} indexURL            where pyodide.asm.wasm, the lock and packages live
 * @property {(relPath: string) => Promise<Uint8Array>} readFile   path relative to the py/ directory
 * @property {(stage: string, loaded: number, total: number) => void} [onProgress]
 */

const PYTHON_SETUP = `
import importlib, json
importlib.invalidate_caches()
import matplotlib
matplotlib.use("Agg")
import pumpflow.webapi as _w

_ALLOWED = {
    "catalog", "evaluate", "default_settings", "export_report",
    "decode_settings", "encode_settings", "unit_options", "convert", "explain",
    "standards", "clients", "standard_label", "water_density", "water_properties",
    "pump_types", "pump_type_hint", "atmosphere", "parse_paste",
    "next_time", "mrt_options", "parse_mrt_paste", "mrt_standard_channels",
}

def _call(fn, args_json):
    if fn not in _ALLOWED:
        raise ValueError("unknown function: " + fn)
    return json.dumps(getattr(_w, fn)(*json.loads(args_json)), allow_nan=False)
`;

/**
 * @param {BootOptions} options
 * @returns {Promise<{version: string, call: (fn: string, args: unknown[]) => string}>}
 */
export async function boot({ loadPyodide, indexURL, readFile, onProgress }) {
  const manifest = JSON.parse(new TextDecoder().decode(await readFile("manifest.json")));
  const total = manifest.wheels.length + 3;
  let loaded = 0;
  /** @param {string} stage */
  const step = (stage) => {
    loaded += 1;
    if (onProgress) onProgress(stage, loaded, total);
  };
  if (onProgress) onProgress("runtime", 0, total);

  const pyodide = await loadPyodide({ indexURL });
  step("runtime");

  await pyodide.loadPackage(manifest.packages);
  step("packages");

  for (const wheel of manifest.wheels) {
    const bytes = await readFile("wheels/" + wheel);
    pyodide.unpackArchive(bytes, "wheel");
    step("wheels");
  }

  pyodide.runPython(PYTHON_SETUP);
  const pyCall = pyodide.globals.get("_call");
  step("engine");

  return {
    version: pyodide.version,
    /** @param {string} fn @param {unknown[]} args */
    call: (fn, args) => pyCall(fn, JSON.stringify(args)),
  };
}
