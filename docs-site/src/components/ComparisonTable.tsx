import React from 'react';

interface Metric {
  name: string;
  observed: number;
  predicted: number;
  pct_diff: number | null;
  flag: string;
  observed_note?: string;
  predicted_note?: string;
}

interface SpotCheck {
  city: string;
  organ: string;
  metrics: Metric[];
}

interface ComparisonTableProps {
  data: SpotCheck[];
  title?: string;
}

const flagColors: Record<string, { bg: string; text: string }> = {
  OK: { bg: '#dcfce7', text: '#166534' },
  WARN: { bg: '#fef9c3', text: '#854d0e' },
  FLAG: { bg: '#fee2e2', text: '#991b1b' },
};

export default function ComparisonTable({ data, title }: ComparisonTableProps) {
  return (
    <div style={{ marginTop: '1rem', marginBottom: '2rem' }}>
      {title && <h4 style={{ marginBottom: '0.75rem' }}>{title}</h4>}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
              <th style={thStyle}>City / Organ</th>
              <th style={thStyle}>Metric</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Observed</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Predicted</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Diff %</th>
              <th style={{ ...thStyle, textAlign: 'center' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.map((check) =>
              check.metrics.map((metric, i) => (
                <tr
                  key={`${check.city}-${check.organ}-${metric.name}`}
                  style={{
                    borderBottom: '1px solid #e5e7eb',
                    backgroundColor: i % 2 === 0 ? 'transparent' : '#f9fafb',
                  }}
                >
                  {i === 0 ? (
                    <td
                      style={{ ...tdStyle, fontWeight: 600 }}
                      rowSpan={check.metrics.length}
                    >
                      {check.city}
                      <br />
                      <span style={{ fontWeight: 400, fontSize: '0.8rem', color: '#6b7280' }}>
                        {check.organ}
                      </span>
                    </td>
                  ) : null}
                  <td style={tdStyle}>{metric.name}</td>
                  <td style={{ ...tdStyle, textAlign: 'right', fontFamily: 'monospace' }}>
                    {formatValue(metric.observed)}
                  </td>
                  <td style={{ ...tdStyle, textAlign: 'right', fontFamily: 'monospace' }}>
                    {formatValue(metric.predicted)}
                  </td>
                  <td style={{ ...tdStyle, textAlign: 'right', fontFamily: 'monospace' }}>
                    {metric.pct_diff != null ? `${metric.pct_diff}%` : '—'}
                  </td>
                  <td style={{ ...tdStyle, textAlign: 'center' }}>
                    <span
                      style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        backgroundColor: flagColors[metric.flag]?.bg ?? '#f3f4f6',
                        color: flagColors[metric.flag]?.text ?? '#374151',
                      }}
                    >
                      {metric.flag}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatValue(v: number | null | undefined): string {
  if (v == null) return '—';
  if (v >= 1) return v.toFixed(1);
  return v.toFixed(4);
}

const thStyle: React.CSSProperties = {
  padding: '8px 12px',
  textAlign: 'left',
  fontWeight: 600,
  fontSize: '0.85rem',
};

const tdStyle: React.CSSProperties = {
  padding: '6px 12px',
  verticalAlign: 'top',
};
