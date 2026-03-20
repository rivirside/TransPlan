import React from 'react';

interface HeatmapTableProps {
  /** Row labels (e.g., city names) */
  rows: string[];
  /** Column labels (e.g., metric names) */
  columns: string[];
  /** 2D data array [row][col] — values between 0 and 1 for probability, or any number */
  data: number[][];
  /** Title */
  title?: string;
  /** Format function for cell display */
  formatCell?: (value: number) => string;
  /** Color scale: 'green' (higher=better) or 'red' (higher=worse) */
  colorScale?: 'green' | 'red' | 'diverging';
  /** Min/max for color scaling */
  domain?: [number, number];
}

function getColor(value: number, min: number, max: number, scale: string): string {
  const range = max - min || 1;
  const norm = Math.max(0, Math.min(1, (value - min) / range));

  if (scale === 'green') {
    const r = Math.round(255 - norm * 120);
    const g = Math.round(255 - norm * 30);
    const b = Math.round(255 - norm * 120);
    return `rgb(${r}, ${g}, ${b})`;
  } else if (scale === 'red') {
    const r = Math.round(255 - norm * 30);
    const g = Math.round(255 - norm * 120);
    const b = Math.round(255 - norm * 120);
    return `rgb(${r}, ${g}, ${b})`;
  } else {
    // Diverging: blue (low) → white (mid) → red (high)
    const mid = (min + max) / 2;
    if (value <= mid) {
      const t = (value - min) / (mid - min || 1);
      return `rgb(${Math.round(59 + t * 196)}, ${Math.round(130 + t * 125)}, ${Math.round(246 - t * 16)})`;
    } else {
      const t = (value - mid) / (max - mid || 1);
      return `rgb(${Math.round(255)}, ${Math.round(255 - t * 155)}, ${Math.round(230 - t * 130)})`;
    }
  }
}

export default function HeatmapTable({
  rows,
  columns,
  data,
  title,
  formatCell = (v) => v.toFixed(3),
  colorScale = 'green',
  domain,
}: HeatmapTableProps) {
  const allValues = data.flat().filter((v) => !isNaN(v));
  const min = domain?.[0] ?? Math.min(...allValues);
  const max = domain?.[1] ?? Math.max(...allValues);

  return (
    <div style={{ marginTop: '1rem', marginBottom: '2rem' }}>
      {title && <h4 style={{ marginBottom: '0.75rem' }}>{title}</h4>}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ borderCollapse: 'collapse', fontSize: '0.85rem' }}>
          <thead>
            <tr>
              <th style={headerStyle}></th>
              {columns.map((col) => (
                <th key={col} style={{ ...headerStyle, textAlign: 'center', minWidth: 80 }}>
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, ri) => (
              <tr key={row}>
                <td style={{ ...cellStyle, fontWeight: 600, backgroundColor: '#f9fafb' }}>
                  {row}
                </td>
                {columns.map((col, ci) => {
                  const value = data[ri]?.[ci];
                  const bg = value != null && !isNaN(value)
                    ? getColor(value, min, max, colorScale)
                    : '#f9fafb';
                  return (
                    <td
                      key={col}
                      style={{
                        ...cellStyle,
                        textAlign: 'center',
                        backgroundColor: bg,
                        fontFamily: 'monospace',
                      }}
                    >
                      {value != null && !isNaN(value) ? formatCell(value) : '—'}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const headerStyle: React.CSSProperties = {
  padding: '6px 10px',
  borderBottom: '2px solid #e5e7eb',
  fontWeight: 600,
  fontSize: '0.8rem',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  color: '#6b7280',
};

const cellStyle: React.CSSProperties = {
  padding: '6px 10px',
  border: '1px solid #e5e7eb',
};
