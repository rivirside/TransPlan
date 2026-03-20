import React, { useMemo, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';

interface DistributionCurveProps {
  /** National median wait in months */
  median: number;
  /** Log-normal sigma parameter */
  sigma: number;
  /** Title for the chart */
  title?: string;
  /** Max months to show on x-axis */
  maxMonths?: number;
  /** Blood type multipliers to show as separate curves */
  bloodTypeMultipliers?: Record<string, number>;
  /** Whether to show CDF (true) or PDF (false) */
  showCDF?: boolean;
}

function lognormalPDF(x: number, mu: number, sigma: number): number {
  if (x <= 0) return 0;
  const logx = Math.log(x);
  return (
    (1 / (x * sigma * Math.sqrt(2 * Math.PI))) *
    Math.exp(-((logx - mu) ** 2) / (2 * sigma ** 2))
  );
}

function lognormalCDF(x: number, mu: number, sigma: number): number {
  if (x <= 0) return 0;
  // Approximation of the normal CDF
  const z = (Math.log(x) - mu) / sigma;
  return 0.5 * (1 + erf(z / Math.sqrt(2)));
}

function erf(x: number): number {
  const a1 = 0.254829592;
  const a2 = -0.284496736;
  const a3 = 1.421413741;
  const a4 = -1.453152027;
  const a5 = 1.061405429;
  const p = 0.3275911;
  const sign = x >= 0 ? 1 : -1;
  const t = 1 / (1 + p * Math.abs(x));
  const y = 1 - ((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
  return sign * y;
}

const COLORS = ['#5B6FE6', '#f97316', '#10b981', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#eab308'];

export default function DistributionCurve({
  median,
  sigma,
  title = 'Wait Time Distribution',
  maxMonths = 60,
  bloodTypeMultipliers,
  showCDF: initialShowCDF = false,
}: DistributionCurveProps) {
  const [showCDF, setShowCDF] = useState(initialShowCDF);

  const curves = useMemo(() => {
    const multipliers = bloodTypeMultipliers ?? { 'All patients': 1.0 };
    const points: Array<Record<string, number>> = [];
    const step = maxMonths / 200;

    for (let x = step; x <= maxMonths; x += step) {
      const point: Record<string, number> = { month: +x.toFixed(1) };
      for (const [label, mult] of Object.entries(multipliers)) {
        const adjMedian = median * mult;
        const mu = Math.log(adjMedian);
        point[label] = showCDF
          ? +lognormalCDF(x, mu, sigma).toFixed(4)
          : +lognormalPDF(x, mu, sigma).toFixed(6);
      }
      points.push(point);
    }
    return { points, labels: Object.keys(multipliers) };
  }, [median, sigma, maxMonths, bloodTypeMultipliers, showCDF]);

  return (
    <div style={{ width: '100%', marginTop: '1rem', marginBottom: '2rem' }}>
      {title && <h4 style={{ textAlign: 'center', marginBottom: '0.5rem' }}>{title}</h4>}
      <div style={{ textAlign: 'center', marginBottom: '0.5rem' }}>
        <button
          onClick={() => setShowCDF(false)}
          style={btnStyle(!showCDF)}
        >
          PDF (density)
        </button>
        <button
          onClick={() => setShowCDF(true)}
          style={btnStyle(showCDF)}
        >
          CDF (cumulative)
        </button>
      </div>
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={curves.points} margin={{ top: 5, right: 30, left: 20, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis
            dataKey="month"
            label={{ value: 'Months', position: 'bottom', offset: 10 }}
            tick={{ fontSize: 12 }}
          />
          <YAxis
            label={{
              value: showCDF ? 'Cumulative Probability' : 'Probability Density',
              angle: -90,
              position: 'insideLeft',
              offset: -5,
              style: { fontSize: 12 },
            }}
            tick={{ fontSize: 12 }}
            domain={showCDF ? [0, 1] : ['auto', 'auto']}
          />
          <Tooltip
            formatter={(value: number) =>
              showCDF ? `${(value * 100).toFixed(1)}%` : value.toFixed(6)
            }
            labelFormatter={(label: number) => `${label} months`}
          />
          <Legend
            verticalAlign="bottom"
            wrapperStyle={{ paddingTop: 16, fontSize: '0.8rem', lineHeight: '1.8' }}
          />
          {curves.labels.map((label, i) => (
            <Line
              key={label}
              type="monotone"
              dataKey={label}
              stroke={COLORS[i % COLORS.length]}
              dot={false}
              strokeWidth={2}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      <p style={{ textAlign: 'center', fontSize: '0.8rem', color: '#666' }}>
        National median: {median} months | Log-normal sigma: {sigma}
      </p>
    </div>
  );
}

function btnStyle(active: boolean): React.CSSProperties {
  return {
    padding: '4px 12px',
    margin: '0 4px',
    border: '1px solid #d1d5db',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.8rem',
    backgroundColor: active ? '#5B6FE6' : '#fff',
    color: active ? '#fff' : '#374151',
  };
}
