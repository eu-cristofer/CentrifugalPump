import { useState } from "react";
import type { CatalogEntry } from "../engine/types";

/** Catalog entries grouped by `group`, keeping the catalog order (UI_SPEC §12). */
export function groupCatalog(catalog: CatalogEntry[]): Array<[string, CatalogEntry[]]> {
  const groups: Array<[string, CatalogEntry[]]> = [];
  for (const entry of catalog) {
    const last = groups.find(([name]) => name === entry.group);
    if (last) last[1].push(entry);
    else groups.push([entry.group, [entry]]);
  }
  return groups;
}

export default function Toolbox({
  catalog,
  onAdd,
}: {
  catalog: CatalogEntry[];
  onAdd: (kind: string) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <aside className="toolbox-wrap">
      <button
        type="button"
        className="toolbox-toggle"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        Nodes
      </button>
      <nav className={`toolbox${open ? " open" : ""}`} aria-label="Nodes">
        {groupCatalog(catalog).map(([group, entries]) => (
          <section key={group}>
            <h2 className="toolbox-group">{group.toUpperCase()}</h2>
            {entries.map((e) => (
              <button
                type="button"
                key={e.kind}
                className="toolbox-item"
                onClick={() => {
                  onAdd(e.kind);
                  setOpen(false);
                }}
              >
                <span className="toolbox-glyph">{e.glyph}</span>
                <span>{e.title}</span>
              </button>
            ))}
          </section>
        ))}
      </nav>
    </aside>
  );
}
