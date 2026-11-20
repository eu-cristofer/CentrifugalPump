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

const g = globalThis as Record<string, unknown>;
if (!g.ResizeObserver) g.ResizeObserver = ResizeObserverStub;
if (!g.DOMMatrixReadOnly) g.DOMMatrixReadOnly = DOMMatrixReadOnlyStub;
