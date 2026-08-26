import React, {useEffect, useState} from 'react';
import useBaseUrl from '@docusaurus/useBaseUrl';

/**
 * ArtifactTable — render a validation artifact from the JSON the generating
 * script wrote, at page-load time (#328).
 *
 * The other validation pages paste their numbers into MDX by hand, which is
 * how the docs came to state the opposite of what ships. Reading the artifact
 * at runtime means a re-run study updates this page with it, or the page says
 * plainly that the artifact is missing — it can never quietly show stale
 * figures.
 *
 * `columns` maps a table column to a path inside each organ's record, so one
 * component covers every artifact sharing the {organs: {...}, _meta} envelope.
 */
type Column = {
  header: string;
  /** Dot path within the per-organ record, e.g. "stats.spearman.rho". */
  path: string;
  /** 'number' rounds to `digits`; 'percent' scales by 100. */
  format?: 'number' | 'percent' | 'text';
  digits?: number;
};

type Props = {
  /** Artifact filename without extension, e.g. "coverage-audit". */
  artifact: string;
  columns: Column[];
  /** Optional explicit organ order; defaults to the file's own key order. */
  organs?: string[];
  caption?: string;
};

function dig(obj: any, path: string): any {
  return path.split('.').reduce(
    (acc, key) => (acc === null || acc === undefined ? acc : acc[key]),
    obj,
  );
}

function render(value: any, col: Column): string {
  if (value === null || value === undefined) return '—';
  if (col.format === 'text') return String(value);
  if (typeof value !== 'number' || !isFinite(value)) return String(value);
  const digits = col.digits ?? 3;
  if (col.format === 'percent') return (value * 100).toFixed(digits) + '%';
  return value.toFixed(digits);
}

export default function ArtifactTable({
  artifact,
  columns,
  organs,
  caption,
}: Props): JSX.Element {
  const url = useBaseUrl(`/data/${artifact}.json`);
  const [doc, setDoc] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((json) => {
        if (!cancelled) setDoc(json);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [url]);

  if (error) {
    return (
      <p>
        <em>Could not load {artifact}.json ({error}).</em>
      </p>
    );
  }
  if (!doc) return <p><em>Loading {artifact}.json…</em></p>;

  const keys = organs ?? Object.keys(doc.organs ?? {});
  const generated = doc?._meta?.generated;
  const backfilled = Boolean(doc?._meta?.generated_source);

  return (
    <div>
      <table>
        <thead>
          <tr>
            <th>Organ</th>
            {columns.map((c) => (
              <th key={c.header}>{c.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {keys.map((organ) => {
            const rec = doc.organs?.[organ] ?? {};
            return (
              <tr key={organ}>
                <td>{organ.charAt(0).toUpperCase() + organ.slice(1)}</td>
                {columns.map((c) => (
                  <td key={c.header}>{render(dig(rec, c.path), c)}</td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
      {caption && <p><small>{caption}</small></p>}
      {generated && (
        <p>
          <small>
            Read live from <code>docs-site/static/data/{artifact}.json</code> ·
            last run {generated.slice(0, 10)}
            {backfilled && ' (date from git history, not a recorded run time)'}
          </small>
        </p>
      )}
    </div>
  );
}
