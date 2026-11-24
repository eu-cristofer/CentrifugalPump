// jsdom lacks the browser APIs React Flow measures with; stub them.
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

class DOMMatrixReadOnlyStub {
  m22 = 1;
  constructor(_transform?: string) {
    void _transform;
  }
}

// uPlot reads the pixel ratio through matchMedia when it is imported.
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}

const g = globalThis as Record<string, unknown>;
if (!g.ResizeObserver) g.ResizeObserver = ResizeObserverStub;
if (!g.DOMMatrixReadOnly) g.DOMMatrixReadOnly = DOMMatrixReadOnlyStub;
