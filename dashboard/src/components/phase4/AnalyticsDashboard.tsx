import { useEffect, useMemo, useState } from 'react';
import type { Listing } from '../../types/listing';
import { fetchListingsQuery } from '../../lib/api';
import type { JobSummary } from '../../lib/api';
import {
  extractSuburb,
  parsePriceToNumber,
  extractCity,
} from '../../lib/analytics';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

type Scope = 'job' | 'site' | 'all';

export default function AnalyticsDashboard({
  selectedSite,
  activeJob,
}: {
  selectedSite: string;
  activeJob: JobSummary | null | undefined;
}) {
  const [scope, setScope] = useState<Scope>(activeJob?.job_id ? 'job' : 'site');
  const [datasetLimit, setDatasetLimit] = useState(800);
  const [data, setData] = useState<Listing[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (activeJob?.job_id) setScope('job');
  }, [activeJob?.job_id]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setIsLoading(true);

        const res = await fetchListingsQuery({
          limit: datasetLimit,
          offset: 0,
          site: scope === 'site' ? selectedSite : undefined,
          job_id: scope === 'job' ? activeJob?.job_id ?? undefined : undefined,
          q: undefined,
        });
        if (cancelled) return;
        setData(res.items);
      } catch (err) {
        console.error(err);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [scope, datasetLimit, selectedSite, activeJob?.job_id]);

  const suburbStats = useMemo(() => {
    const map = new Map<string, { suburb: string; count: number; sumPrice: number; priceCount: number }>();
    for (const l of data) {
      const suburb = extractSuburb(l) ?? 'Unknown';
      const priceNum = parsePriceToNumber(l.price);
      const prev = map.get(suburb) ?? {
        suburb,
        count: 0,
        sumPrice: 0,
        priceCount: 0,
      };
      prev.count += 1;
      if (priceNum != null) {
        prev.sumPrice += priceNum;
        prev.priceCount += 1;
      }
      map.set(suburb, prev);
    }

    const rows = Array.from(map.values()).map((r) => ({
      suburb: r.suburb,
      count: r.count,
      avgPrice: r.priceCount ? Math.round(r.sumPrice / r.priceCount) : null,
    }));

    rows.sort((a, b) => b.count - a.count);
    return rows.slice(0, 10);
  }, [data]);

  const propertyTypeStats = useMemo(() => {
    const map = new Map<string, number>();
    for (const l of data) {
      const t = l.property_type ?? 'Unknown';
      map.set(t, (map.get(t) ?? 0) + 1);
    }

    const rows = Array.from(map.entries())
      .map(([property_type, count]) => ({ property_type, count }))
      .sort((a, b) => b.count - a.count);

    const top = rows.slice(0, 5);
    const restCount = rows.slice(5).reduce((acc, r) => acc + r.count, 0);
    const finalRows = restCount > 0 ? [...top, { property_type: 'Other', count: restCount }] : top;
    return finalRows;
  }, [data]);

  const geoStats = useMemo(() => {
    const map = new Map<string, number>();
    for (const l of data) {
      const key = extractCity(l) ?? 'Unknown';
      map.set(key, (map.get(key) ?? 0) + 1);
    }
    const rows = Array.from(map.entries())
      .map(([city, count]) => ({ city, count }))
      .sort((a, b) => b.count - a.count);
    return rows.slice(0, 8);
  }, [data]);

  const missingFieldStats = useMemo(() => {
    const total = data.length || 1;
    const fields: { key: keyof Listing; label: string }[] = [
      { key: 'title', label: 'title' },
      { key: 'price', label: 'price' },
      { key: 'location', label: 'location' },
      { key: 'bedrooms', label: 'bedrooms' },
      { key: 'bathrooms', label: 'bathrooms' },
      { key: 'property_type', label: 'property_type' },
      { key: 'agent_name', label: 'agent_name' },
      { key: 'agent_phone', label: 'agent_phone' },
      { key: 'erf_size', label: 'erf_size' },
      { key: 'floor_size', label: 'floor_size' },
      { key: 'rates_and_taxes', label: 'rates/taxes' },
      { key: 'levies', label: 'levies' },
    ];

    const rows = fields.map((f) => {
      let missing = 0;
      for (const l of data) {
        const v = l[f.key];
        const empty =
          v == null || (typeof v === 'string' ? v.trim().length === 0 : false);
        if (empty) missing += 1;
      }
      const missingPct = missing / total;
      return { ...f, missingPct, missing, total };
    });

    rows.sort((a, b) => b.missingPct - a.missingPct);
    return rows;
  }, [data]);

  const pieColors = ['#818cf8', '#22c55e', '#38bdf8', '#fb7185', '#f59e0b'];

  return (
    <section className="rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-950 to-slate-900/60 overflow-hidden">
      <div className="px-4 pt-4 pb-3 border-b border-slate-800/80 flex items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-50">Analytics Dashboard</h2>
          <p className="text-xs text-slate-400">Phase 4: charts + data quality heatmap</p>
        </div>

        <div className="flex items-center gap-2">
          <select
            className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1 text-[11px] text-slate-200 outline-none focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500/30"
            value={scope}
            onChange={(e) => setScope(e.target.value as Scope)}
          >
            <option value="job">Selected job</option>
            <option value="site">Selected site</option>
            <option value="all">All listings</option>
          </select>

          <select
            className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1 text-[11px] text-slate-200 outline-none focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500/30"
            value={datasetLimit}
            onChange={(e) => setDatasetLimit(Number(e.target.value))}
          >
            <option value={400}>Last 400</option>
            <option value={800}>Last 800</option>
            <option value={1200}>Last 1200</option>
          </select>
        </div>
      </div>

      <div className="px-4 py-4 space-y-4">
        {isLoading && (
          <div className="text-xs text-slate-500">Loading analytics…</div>
        )}

        {!isLoading && data.length === 0 && (
          <div className="text-xs text-slate-500">
            No data to analyze. Run a job first.
          </div>
        )}

        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-xl border border-slate-800/80 bg-slate-950/30 p-3">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs text-slate-200 font-medium">
                Price vs Suburb (avg)
              </div>
            </div>
            <div className="h-60 w-full min-w-0">
              <ResponsiveContainer
                width="100%"
                height={240}
                minWidth={0}
                minHeight={0}
              >
                <BarChart data={suburbStats} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.35} />
                  {/* Suburb labels can be very long; rely on tooltip instead */}
                  <XAxis dataKey="suburb" tick={false} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{
                      background: '#0b1220',
                      border: '1px solid #1f2937',
                      borderRadius: 10,
                      color: '#e2e8f0',
                    }}
                    formatter={(value: any) => (typeof value === 'number' ? value.toLocaleString() : value)}
                  />
                  <Bar dataKey="avgPrice" name="Avg price" fill="#818cf8" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-xl border border-slate-800/80 bg-slate-950/30 p-3">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs text-slate-200 font-medium">
                Listings by Suburb (top)
              </div>
            </div>
            <div className="h-60 w-full min-w-0">
              <ResponsiveContainer
                width="100%"
                height={240}
                minWidth={0}
                minHeight={0}
              >
                <BarChart data={suburbStats} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.35} />
                  {/* Suburb labels can be very long; rely on tooltip instead */}
                  <XAxis dataKey="suburb" tick={false} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{
                      background: '#0b1220',
                      border: '1px solid #1f2937',
                      borderRadius: 10,
                      color: '#e2e8f0',
                    }}
                  />
                  <Bar dataKey="count" name="Count" fill="#38bdf8" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-xl border border-slate-800/80 bg-slate-950/30 p-3">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs text-slate-200 font-medium">
                Property Type Breakdown
              </div>
            </div>
            <div className="h-64 w-full min-w-0">
              <ResponsiveContainer
                width="100%"
                height={256}
                minWidth={0}
                minHeight={0}
              >
                <PieChart>
                  <Tooltip
                    contentStyle={{
                      background: '#0b1220',
                      border: '1px solid #1f2937',
                      borderRadius: 10,
                      color: '#e2e8f0',
                    }}
                    content={({ active, payload }) => {
                      if (!active || !payload || payload.length === 0) return null;
                      const entry = (payload[0] as any)?.payload as {
                        property_type?: string;
                        count?: number;
                      };
                      const label = entry?.property_type ?? 'Unknown';
                      const count = entry?.count ?? 0;
                      return (
                        <div className="text-[11px]">
                          <div className="font-medium text-slate-100">{label}</div>
                          <div className="text-slate-300">{count} listings</div>
                        </div>
                      );
                    }}
                  />
                  <Pie
                    data={propertyTypeStats}
                    dataKey="count"
                    nameKey="property_type"
                    innerRadius={40}
                    outerRadius={85}
                    paddingAngle={2}
                  >
                    {propertyTypeStats.map((entry, i) => (
                      <Cell
                        key={`${entry.property_type}-${i}`}
                        fill={pieColors[i % pieColors.length]}
                      />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-xl border border-slate-800/80 bg-slate-950/30 p-3">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs text-slate-200 font-medium">
                Geographic Heatmap (City density)
              </div>
            </div>
            <div className="h-64 w-full min-w-0">
              <ResponsiveContainer
                width="100%"
                height={256}
                minWidth={0}
                minHeight={0}
              >
                <BarChart data={geoStats} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.35} />
                  <XAxis dataKey="city" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{
                      background: '#0b1220',
                      border: '1px solid #1f2937',
                      borderRadius: 10,
                      color: '#e2e8f0',
                    }}
                  />
                  <Bar dataKey="count" fill="#22c55e" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-800/80 bg-slate-950/30 p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs text-slate-200 font-medium">
              Missing Fields Heatmap
            </div>
            <div className="text-[11px] text-slate-500 font-mono">
              {data.length} rows
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {missingFieldStats.slice(0, 12).map((f) => {
              const pct = Math.round(f.missingPct * 100);
              const intensity = Math.min(1, Math.max(0, f.missingPct));
              const bg = `rgba(248, 113, 113, ${0.08 + intensity * 0.42})`;
              const border = `rgba(248, 113, 113, ${0.18 + intensity * 0.55})`;
              return (
                <div
                  key={f.key as string}
                  className="rounded-lg border"
                  style={{
                    background: bg,
                    borderColor: border,
                    padding: 10,
                  }}
                >
                  <div className="text-[11px] text-slate-200 font-medium">
                    {f.label}
                  </div>
                  <div className="mt-1 text-[11px] text-slate-300 font-mono">
                    {pct}% missing
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-3 text-xs text-slate-500">
            Higher missing percentage indicates lower data quality for that field.
          </div>
        </div>
      </div>
    </section>
  );
}

