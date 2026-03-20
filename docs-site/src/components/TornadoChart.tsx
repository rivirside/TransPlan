import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface TornadoData {
  parameter: string;
  label: string;
  p24_at_low: number;
  p24_at_high: number;
  p24_baseline: number;
  swing: number;
}

interface TornadoChartProps {
  data: TornadoData[];
  title?: string;
  baselineLabel?: string;
}

export default function TornadoChart({
  data,
  title = 'Parameter Sensitivity',
  baselineLabel = 'Baseline',
}: TornadoChartProps) {
  // Transform data for horizontal tornado chart
  const chartData = data
    .sort((a, b) => b.swing - a.swing)
    .map((d) => ({
      name: d.label,
      favorable: +(d.p24_at_low - d.p24_baseline).toFixed(4),
      unfavorable: +(d.p24_at_high - d.p24_baseline).toFixed(4),
      baseline: d.p24_baseline,
      swing: d.swing,
    }));

  return (
    <div style={{ width: '100%', marginTop: '1rem', marginBottom: '2rem' }}>
      {title && <h4 style={{ textAlign: 'center', marginBottom: '0.5rem' }}>{title}</h4>}
      <ResponsiveContainer width="100%" height={Math.max(200, chartData.length * 80)}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 5, right: 40, left: 160, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis
            type="number"
            tickFormatter={(v: number) => `${v > 0 ? '+' : ''}${(v * 100).toFixed(0)}pp`}
            domain={['dataMin', 'dataMax']}
          />
          <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 13 }} />
          <Tooltip
            formatter={(value: number) =>
              `${value > 0 ? '+' : ''}${(value * 100).toFixed(1)} percentage points`
            }
          />
          <Legend />
          <ReferenceLine x={0} stroke="#666" strokeWidth={2} />
          <Bar dataKey="favorable" name="Favorable extreme" stackId="stack">
            {chartData.map((_, index) => (
              <Cell key={`fav-${index}`} fill="#4ade80" />
            ))}
          </Bar>
          <Bar dataKey="unfavorable" name="Unfavorable extreme" stackId="stack">
            {chartData.map((_, index) => (
              <Cell key={`unfav-${index}`} fill="#f87171" />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p style={{ textAlign: 'center', fontSize: '0.85rem', color: '#666', marginTop: '0.25rem' }}>
        {baselineLabel}: p24 = {chartData[0]?.baseline?.toFixed(4) ?? 'N/A'}. Bars show change from baseline at parameter extremes.
      </p>
    </div>
  );
}
