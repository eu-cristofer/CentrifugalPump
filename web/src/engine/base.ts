// Where the Pyodide bundle lives, relative to the Vite `base` the app was
// built with ("/" for local serving, "/<repo>/app/" on GitHub Pages).
export function pyBase(baseUrl: string = import.meta.env.BASE_URL): string {
  const withSlash = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  return `${withSlash}py/`;
}
