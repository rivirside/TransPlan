import React, {useEffect, useState} from 'react';
import useBaseUrl from '@docusaurus/useBaseUrl';

/**
 * ArtifactStat — one number, read from a published artifact at page load (#328).
 *
 * Companion to ArtifactTable for artifacts that are not organ-keyed (parameter
 * recovery, SBC summaries). Using it instead of typing the figure into the MDX
 * keeps prose honest: re-run the study and the sentence updates, rather than
 * quietly describing a result that no longer holds.
 *
 *   <ArtifactStat artifact="parameter-recovery"
 *                 path="summary.rho_p12_median" digits={2} />
 */
type Props = {
  /** Artifact filename without extension. */
  artifact: string;
  /** Dot path into the document, e.g. "summary.rho_p12_median". */
  path: string;
  format?: 'number' | 'percent';
  digits?: number;
  /** Rendered while loading and when the value cannot be found. */
  fallback?: string;
};

function dig(obj: any, path: string): any {
  return path.split('.').reduce(
    (acc, key) => (acc === null || acc === undefined ? acc : acc[key]),
    obj,
  );
}

export default function ArtifactStat({
  artifact,
  path,
  format = 'number',
  digits = 3,
  fallback = '…',
}: Props): JSX.Element {
  const url = useBaseUrl(`/data/${artifact}.json`);
  const [text, setText] = useState<string>(fallback);

  useEffect(() => {
    let cancelled = false;
    fetch(url)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((doc) => {
        if (cancelled) return;
        const value = dig(doc, path);
        if (typeof value !== 'number' || !isFinite(value)) {
          setText(value === undefined || value === null ? fallback : String(value));
          return;
        }
        setText(
          format === 'percent'
            ? (value * 100).toFixed(digits) + '%'
            : value.toFixed(digits),
        );
      })
      .catch(() => {
        if (!cancelled) setText(fallback);
      });
    return () => {
      cancelled = true;
    };
  }, [url, path, format, digits, fallback]);

  return <strong>{text}</strong>;
}
