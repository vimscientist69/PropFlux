import { useEffect, useMemo, useState } from 'react';
import type { Listing } from '../../types/listing';
import { fetchListingsQuery } from '../../lib/api';
import type { JobSummary } from '../../lib/api';
import { Play } from 'lucide-react';

type Scope = 'job' | 'site' | 'all';

export default function DataExplorer({
  selectedSite,
  activeJob,
}: {
  selectedSite: string;
  activeJob: JobSummary | null | undefined;
}) {
  const [scope, setScope] = useState<Scope>(activeJob?.job_id ? 'job' : 'site');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [total, setTotal] = useState(0);
  const [items, setItems] = useState<Listing[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (activeJob?.job_id) setScope('job');
  }, [activeJob?.job_id]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setIsLoading(true);
        const offset = (page - 1) * pageSize;
        const res = await fetchListingsQuery({
          limit: pageSize,
          offset,
          q: query || undefined,
          site: scope === 'site' ? selectedSite : undefined,
          job_id: scope === 'job' ? activeJob?.job_id ?? undefined : undefined,
        });
        if (cancelled) return;
        setItems(res.items);
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
  }, [scope, query, page, pageSize, selectedSite, activeJob?.job_id]);

  const pageCount = useMemo(() => {
    return Math.max(1, Math.ceil(total / pageSize));
  }, [total, pageSize]);

  return (
    <section className="rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-950 to-slate-900/60 overflow-hidden">
      <div className="px-4 pt-4 pb-3 border-b border-slate-800/80 flex items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-50">Data Explorer</h2>
          <p className="text-xs text-slate-400">Search + paginate all scraped listings</p>
        </div>

        <div className="flex items-center gap-2">
          <select
            className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1 text-[11px] text-slate-200 outline-none focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500/30"
            value={scope}
            onChange={(e) => {
              setScope(e.target.value as Scope);
              setPage(1);
            }}
          >
            <option value="job">Selected job</option>
            <option value="site">Selected site</option>
            <option value="all">All listings</option>
          </select>

          <select
            className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1 text-[11px] text-slate-200 outline-none focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500/30"
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPage(1);
            }}
          >
            <option value={15}>15 / page</option>
            <option value={25}>25 / page</option>
            <option value={50}>50 / page</option>
          </select>
        </div>
      </div>

      <div className="px-4 py-4 space-y-3">
        <div className="flex items-center gap-2 flex-wrap">
          <input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(1);
            }}
            placeholder="Search title / location / property type…"
            className="w-full md:w-96 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-[11px] text-slate-200 outline-none focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500/30"
          />
          <div className="text-[11px] text-slate-500 font-mono">
            {isLoading ? 'Loading…' : `${total.toLocaleString()} results`}
          </div>
        </div>

        <div className="rounded-xl border border-slate-800/80 bg-slate-950/30 overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-y-1 text-xs">
            <thead className="text-[11px] uppercase tracking-wide text-slate-500">
              <tr>
                <th className="text-left px-3 py-2 font-medium">Title</th>
                <th className="text-left px-3 py-2 font-medium">Price</th>
                <th className="hidden lg:table-cell text-left px-3 py-2 font-medium">Location</th>
                <th className="hidden xl:table-cell text-left px-3 py-2 font-medium">Type</th>
                <th className="text-right px-3 py-2 font-medium">Link</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && !isLoading && (
                <tr>
                  <td colSpan={5} className="px-3 py-10 text-center text-xs text-slate-500">
                    No listings matched your search.
                  </td>
                </tr>
              )}
              {items.map((l, index: number) => (
                <tr key={`${l.id ?? l.listing_url ?? String(index)}`} className="align-top">
                  <td className="px-3 py-2">
                    <div className="text-[11px] text-slate-100 font-medium line-clamp-1">
                      {l.title ?? 'Untitled'}
                    </div>
                    <div className="mt-0.5 text-[10px] text-slate-500 line-clamp-1">
                      {l.suburb ?? l.city ?? l.location ?? '—'} · {l.source_site ?? '—'}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-[11px] text-indigo-400 font-semibold whitespace-nowrap">
                    {l.price ?? '—'}
                  </td>
                  <td className="px-3 py-2 text-[11px] text-slate-400 hidden lg:table-cell whitespace-nowrap">
                    {l.location ?? '—'}
                  </td>
                  <td className="px-3 py-2 text-[11px] text-slate-400 hidden xl:table-cell whitespace-nowrap">
                    {l.property_type ?? '—'}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {l.listing_url ? (
                      <a
                        href={l.listing_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-slate-800 bg-slate-900/60 text-slate-300 hover:text-indigo-400 hover:border-indigo-500/50 transition-colors"
                      >
                        <Play className="h-3 w-3" />
                      </a>
                    ) : (
                      <span className="text-[11px] text-slate-500">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between gap-3 pt-1">
          <button
            className="rounded-lg border border-slate-800 bg-slate-900/50 px-3 py-2 text-[11px] text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1 || isLoading}
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
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}

