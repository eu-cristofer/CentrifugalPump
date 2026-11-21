import { vi } from "vitest";

/** Test double for the `uplot` module (jsdom has no canvas): records what it is given. */
export interface MockOptions {
  width: number;
  height: number;
  series: Array<{ label?: string; stroke?: string; dash?: number[]; paths?: unknown }>;
  scales?: { y?: { auto?: boolean; range?: unknown } };
  axes?: Array<{ show?: boolean; label?: string }>;
  cursor?: { sync?: { key: string } };
  hooks?: { draw?: Array<(u: unknown) => void> };
}

export const plots: FakePlot[] = [];
export const failure = { next: false };

export class FakePlot {
  data: unknown;
  width: number;
  setData = vi.fn((d: unknown) => {
    this.data = d;
  });
  setSize = vi.fn();
  redraw = vi.fn();
  destroy = vi.fn();

  constructor(
    readonly opts: MockOptions,
    data: unknown,
    readonly target: HTMLElement,
  ) {
    if (failure.next) {
      failure.next = false;
      throw new Error("no canvas");
    }
    this.data = data;
    this.width = opts.width;
    plots.push(this);
  }
}

export function resetPlots(): void {
  plots.length = 0;
  failure.next = false;
}
