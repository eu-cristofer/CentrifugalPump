// @vitest-environment node
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { expect, it } from "vitest";
import type { PumpflowDoc } from "../engine/types";
import { docNodes } from "./model";
import { INITIAL_STATE, reduce, serializeDocument } from "./store";

const repo = path.resolve(import.meta.dirname, "../../../");

// Writes the file tests/test_web_saved_fixture.py loads with the desktop engine.
it("saves P-9001A through the store and writes the Python-side fixture", () => {
  const source = path.join(repo, "examples", "user", "P-9001A_MRT_reference.pumpflow");
  const input = JSON.parse(readFileSync(source, "utf8")) as PumpflowDoc;
  const first = docNodes(input)[0]!;

  let state = reduce(INITIAL_STATE, { type: "open", doc: input, name: "P-9001A" });
  state = reduce(state, {
    type: "move",
    moves: [{ id: first.id, x: first.x + 10, y: first.y + 5 }],
  });
  const text = serializeDocument(state.doc!);

  const out = path.join(repo, "tests", "fixtures", "web", "saved_p9001a.pumpflow");
  mkdirSync(path.dirname(out), { recursive: true });
  writeFileSync(out, text, "utf8");

  const saved = JSON.parse(text) as PumpflowDoc;
  expect(docNodes(saved)[0]).toMatchObject({ id: first.id, x: first.x + 10, y: first.y + 5 });
  expect(saved.edges).toEqual(input.edges);
  expect(saved.view).toEqual(input.view);
});
