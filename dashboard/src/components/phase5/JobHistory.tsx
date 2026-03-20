import { useEffect, useMemo, useState } from 'react';
import type { JobSummary } from '../../lib/api';
import { exportJobData, fetchJobsQuery } from '../../lib/api';

type SiteOption = { label: string; value: string };

export default function JobHistory({
  siteOptions,
  initialSite,
}: {
  siteOptions: SiteOption[];
  initialSite: string;
}) {
  const statusOptions = useMemo(
    () => ['RUNNING', 'COMPLETED', 'FAILED', 'TERMINATED'],
    [],
  );

  const [site, setSite] = useState<string>('ALL');
  const [status, setStatus] = useState<string>('ALL');
  const [q, setQ] = useState<string>('');
  const debouncedQ = useDebouncedValue(q, 400);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [exportingJobId, setExportingJobId] = useState<string | null>(null);

  useEffect(() => {
    setSite(initialSite);
  }, [initialSite]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setIsLoading(true);
        const res = await fetchJobsQuery({
          limit: pageSize,
          offset: (page - 1) * pageSize,
          site: site === 'ALL' ? undefined : site,
          status: status === 'ALL' ? undefined : status,
          q: debouncedQ || undefined,
        });
        if (cancelled) return;
        setJobs(res.items);
        setTotal(res.total);
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
  }, [site, status, debouncedQ, page, pageSize]);

  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  async function download(jobId: string, format: 'csv' | 'json') {
    try {
      setExportingJobId(`${jobId}:${format}`);
      const blob = await exportJobData(jobId, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${jobId}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExportingJobId(null);
    }
  }

  function formatTs(ts: string | null | undefined) {
    if (!ts) return '—';
    return ts.replace('T', ' ').split('.')[0];
  }

  return (
    <section className="rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-950 to-slate-900/60 overflow-hidden">
      <div className="px-4 pt-4 pb-3 border-b border-slate-800/80 flex items-center justify-between gap-2 overflow-hidden">
        <div>
          <h2 className="text-sm font-semibold text-slate-50">Job History</h2>
          <p className="text-xs text-slate-400">
            Filter past runs and export results by `job_id`.
          </p>
        </div>

        <div className="text-[11px] text-slate-500 font-mono whitespace-nowrap">
          {isLoading ? 'Loading…' : `${total.toLocaleString()} jobs`}
        </div>
      </div>

      <div className="px-4 py-4 space-y-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1.5">
            <div className="text-[11px] text-slate-400">Site</div>
            <select
              className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-[11px] text-slate-200 outline-none focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500/30"
              value={site}
              onChange={(e) => {
                setPage(1);
                setSite(e.target.value);
              }}
            >
              <option value="ALL">All</option>
              {siteOptions.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <div className="text-[11px] text-slate-400">Status</div>
            <select
              className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-[11px] text-slate-200 outline-none focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500/30"
              value={status}
              onChange={(e) => {
                setPage(1);
                setStatus(e.target.value);
              }}
            >
              <option value="ALL">All</option>
              {statusOptions.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5 flex-1 min-w-[220px]">
            <div className="text-[11px] text-slate-400">Search</div>
            <input
              value={q}
              onChange={(e) => {
                setPage(1);
                setQ(e.target.value);
              }}
              placeholder="job_id / status / site…"
              className="w-full rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-[11px] text-slate-200 outline-none focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500/30"
            />
          </div>

          <div className="space-y-1.5">
            <div className="text-[11px] text-slate-400">Rows</div>
            <select
              className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-[11px] text-slate-200 outline-none focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500/30"
              value={pageSize}
              onChange={(e) => {
                setPage(1);
                setPageSize(Number(e.target.value));
              }}
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </div>
        </div>
      </div>

      <div className="px-4 pb-4">
        <div className="rounded-xl border border-slate-800/80 bg-slate-950/30 overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-y-1 text-xs">
            <thead className="text-[11px] uppercase tracking-wide text-slate-500">
              <tr>
                <th className="text-left px-3 py-2 font-medium">Started</th>
                <th className="text-left px-3 py-2 font-medium">Ended</th>
                <th className="text-left px-3 py-2 font-medium">Site</th>
                <th className="text-left px-3 py-2 font-medium">Status</th>
                <th className="text-left px-3 py-2 font-medium">Items</th>
                <th className="text-left px-3 py-2 font-medium">Job ID</th>
                <th className="text-right px-3 py-2 font-medium">Export</th>
              </tr>
            </thead>
            <tbody>
              {jobs.length === 0 && !isLoading && (
                <tr>
                  <td colSpan={7} className="px-3 py-10 text-center text-xs text-slate-500">
                    No jobs matched your filters.
                  </td>
                </tr>
              )}
              {jobs.map((job) => {
                const ended = job.ended_at ?? job.terminated_at ?? null;
                const endedText = formatTs(ended);
                const startedText = formatTs(job.started_at);
                const jobExportingCsv =
                  exportingJobId === `${job.job_id}:csv`;
                const jobExportingJson =
                  exportingJobId === `${job.job_id}:json`;
                return (
                  <tr key={job.job_id} className="align-top">
                    <td className="px-3 py-2 text-slate-300 whitespace-nowrap">{startedText}</td>
                    <td className="px-3 py-2 text-slate-300 whitespace-nowrap">{endedText}</td>
                    <td className="px-3 py-2 text-slate-300 whitespace-nowrap">{job.site}</td>
                    <td className="px-3 py-2 text-slate-300 whitespace-nowrap">{job.status}</td>
                    <td className="px-3 py-2 text-slate-300 whitespace-nowrap">{job.items_scraped ?? 0}</td>
                    <td className="px-3 py-2 font-mono text-slate-400 max-w-[160px] truncate">
                      {job.job_id}
                    </td>
                    <td className="px-3 py-2 text-right whitespace-nowrap">
                      <div className="inline-flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => void download(job.job_id, 'csv')}
                          disabled={!!exportingJobId}
                          className="rounded-lg border border-slate-800 bg-slate-900/60 px-2 py-1 text-[11px] text-slate-200 hover:border-indigo-500/50 hover:text-indigo-300 disabled:opacity-40"
                        >
                          {jobExportingCsv ? 'CSV…' : 'CSV'}
                        </button>
                        <button
                          type="button"
                          onClick={() => void download(job.job_id, 'json')}
                          disabled={!!exportingJobId}
                          className="rounded-lg border border-slate-800 bg-slate-900/60 px-2 py-1 text-[11px] text-slate-200 hover:border-indigo-500/50 hover:text-indigo-300 disabled:opacity-40"
                        >
                          {jobExportingJson ? 'JSON…' : 'JSON'}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between gap-3 pt-3">
          <button
            className="rounded-lg border border-slate-800 bg-slate-900/50 px-3 py-2 text-[11px] text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1 || isLoading}
            type="button"
          >
            Prev
          </button>
          <div className="text-[11px] text-slate-500 font-mono">
            Page {page} / {pageCount}
          </div>
          <button
            className="rounded-lg border border-slate-800 bg-slate-900/50 px-3 py-2 text-[11px] text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed"
            onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
            disabled={page >= pageCount || isLoading}
            type="button"
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}

function useDebouncedValue<T>(value: T, delayMs: number) {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedValue(value), delayMs);
    return () => {
      window.clearTimeout(t);
    };
  }, [value, delayMs]);

  return debouncedValue;
}

