import { useEffect, useMemo, useRef, useState } from 'react';
import { Play, Square, Database, Radar, Settings2 } from 'lucide-react';
import './App.css';
import type { JobRequest } from './types/job';
import type { Listing } from './types/listing';
import {
  runJob,
  fetchJobsHistory,
  fetchRecentListings,
  terminateJob,
  fetchJobTelemetry,
  fetchJobLogs,
} from './lib/api';
import type { JobSummary, JobTelemetry } from './lib/api';
import { Button } from './components/ui/button';

const SITES = [
  { label: 'Property24', value: 'property24' },
  { label: 'PrivateProperty', value: 'privateproperty' },
];

function App() {
  const [form, setForm] = useState<JobRequest>({
    site: SITES[0]?.value ?? 'property24',
  });
  const [isRunning, setIsRunning] = useState(false);
  const [isTerminating, setIsTerminating] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [isLoadingJobs, setIsLoadingJobs] = useState(false);
  const [isLoadingListings, setIsLoadingListings] = useState(false);

  const [useLimit, setUseLimit] = useState(false);
  const [useMaxPages, setUseMaxPages] = useState(false);

  const [telemetry, setTelemetry] = useState<JobTelemetry | null>(null);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [isLoadingTelemetry, setIsLoadingTelemetry] = useState(false);
  const [isLoadingLogs, setIsLoadingLogs] = useState(false);
  const logBottomRef = useRef<HTMLDivElement | null>(null);
  const logContainerRef = useRef<HTMLDivElement | null>(null);
  const prevItemsScrapedRef = useRef<number>(0);

  const activeJob = useMemo(
    () => jobs.find((j) => j.job_id === selectedJobId) ?? jobs[0],
    [jobs, selectedJobId],
  );

  // Phase 3: polling loop for telemetry + logs while job is active
  useEffect(() => {
    let interval: number | undefined;
    const jobId = activeJob?.job_id;
    if (!jobId) return;

    // Reset tracking for new job selection
    prevItemsScrapedRef.current = 0;

    // A job is considered "running" if its status is 'RUNNING' or 'starting'
    const isRunning =
      activeJob?.status === 'RUNNING' || activeJob?.status === 'starting';

    const tick = async () => {
      try {
        setIsLoadingTelemetry(true);
        const t = await fetchJobTelemetry(jobId);
        setTelemetry(t);

        // Conditional auto-refresh: if items_scraped increased, reload listings
        const currentCount = (t.job?.items_scraped as number) || 0;
        if (currentCount > prevItemsScrapedRef.current) {
          void reloadListings(jobId);
          prevItemsScrapedRef.current = currentCount;
        }

        // Keep jobs list fresh (status transitions)
        void reloadJobs();
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoadingTelemetry(false);
      }

      try {
        setIsLoadingLogs(true);
        const logs = await fetchJobLogs(jobId, 200);
        setLogLines(logs.lines);
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoadingLogs(false);
      }
    };

    // Always poll once when the effect runs (e.g. on manual selection)
    void tick();
    // Also reload listings for this specific job when selection changes
    void reloadListings(jobId);

    // Only start interval if the job is currently running
    if (isRunning) {
      interval = window.setInterval(tick, 2000);
    }

    return () => {
      if (interval) window.clearInterval(interval);
    };
  }, [activeJob?.job_id, activeJob?.status]);

  useEffect(() => {
    void reloadJobs();
    void reloadListings();
  }, []);

  // Auto-scroll logs to bottom when new lines arrive
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logLines]);

  async function reloadJobs() {
    try {
      setIsLoadingJobs(true);
      const data = await fetchJobsHistory();
      setJobs(data);
    } catch (err) {
      console.error(err);
      setStatusMessage('Failed to load jobs history.');
    } finally {
      setIsLoadingJobs(false);
    }
  }

  async function reloadListings(jobId?: string | null) {
    try {
      setIsLoadingListings(true);
      const data = await fetchRecentListings({
        limit: 25,
        site: jobId ? undefined : form.site, // If we have a specific job, don't over-filter by currently selected site
        job_id: jobId ?? undefined,
      });
      setListings(data);
    } catch (err) {
      console.error(err);
      setStatusMessage('Failed to load recent listings.');
    } finally {
      setIsLoadingListings(false);
    }
  }

  async function handleRunJob() {
    try {
      setIsRunning(true);
      setStatusMessage('Launching job...');
      const payload: JobRequest = {
        site: form.site,
        url: form.url || undefined,
        skip_dynamic_fields: form.skip_dynamic_fields ?? false,
        settings_overrides: form.settings_overrides,
      };

      if (useLimit && form.limit) {
        payload.limit = form.limit;
      }

      if (useMaxPages && form.max_pages) {
        payload.max_pages = form.max_pages;
      }

      const res = await runJob(payload);
      setStatusMessage(`Job ${res.job_id} started for ${res.site}.`);
      
      // Optimistic update: add the new job to the top of the list immediately
      const optimisticJob: JobSummary = {
        job_id: res.job_id,
        site: res.site,
        status: res.status, // typically "starting"
        started_at: new Date().toISOString().replace('T', ' ').split('.')[0], // roughly match DB format
        items_scraped: 0,
      };
      
      setJobs((prev) => [optimisticJob, ...prev]);
      setSelectedJobId(res.job_id);
      
      // Load initial listings for the new job
      await reloadListings(res.job_id);
    } catch (err) {
      console.error(err);
      setStatusMessage(
        err instanceof Error ? err.message : 'Failed to start job.',
      );
    } finally {
      setIsRunning(false);
    }
  }

  async function handleTerminateJob() {
    if (!activeJob?.job_id) return;
    try {
      setIsTerminating(true);
      setStatusMessage(`Terminating job ${activeJob.job_id}…`);
      const res = await terminateJob(activeJob.job_id);
      setStatusMessage(`Job ${res.job_id} ${res.status}.`);
      
      // Optimistic update: update the status in the list immediately
      setJobs((prev) =>
        prev.map((j) =>
          j.job_id === activeJob.job_id ? { ...j, status: res.status } : j,
        ),
      );
      
      await reloadListings(activeJob.job_id);
    } catch (err) {
      console.error(err);
      setStatusMessage(
        err instanceof Error ? err.message : 'Failed to terminate job.',
      );
    } finally {
      setIsTerminating(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      <aside className="hidden md:flex w-64 flex-col border-r border-slate-800/80 bg-gradient-to-b from-slate-950 to-slate-900/60 px-6 py-5">
        <div className="flex items-center gap-3 mb-8">
          <div className="h-9 w-9 rounded-2xl bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center shadow-lg shadow-indigo-500/30">
            <Radar className="h-5 w-5 text-indigo-300" />
          </div>
          <div>
            <div className="text-sm font-semibold tracking-tight">
              PropFlux
            </div>
            <div className="text-xs text-slate-400">Scraper Control Center</div>
          </div>
        </div>

        <nav className="space-y-1 text-sm">
          <div className="px-2 py-1 text-xs font-semibold text-slate-500 uppercase tracking-wide">
            Overview
          </div>
          <button className="w-full flex items-center gap-2 rounded-lg px-2 py-1.5 bg-slate-800/70 text-slate-50 text-sm shadow-sm shadow-slate-900/40">
            <Play className="h-4 w-4 text-indigo-300" />
            Control Panel
          </button>
          <button className="w-full flex items-center gap-2 rounded-lg px-2 py-1.5 text-slate-400 hover:bg-slate-900/80 hover:text-slate-100 transition-colors">
            <Database className="h-4 w-4" />
            Data & Listings
          </button>
          <button className="w-full flex items-center gap-2 rounded-lg px-2 py-1.5 text-slate-400 hover:bg-slate-900/80 hover:text-slate-100 transition-colors">
            <Settings2 className="h-4 w-4" />
            Engine Settings
          </button>
        </nav>

        <div className="mt-auto pt-6 border-t border-slate-800/80 text-xs text-slate-500">
          FastAPI at{' '}
          <span className="font-mono text-[11px] text-slate-300">
            {import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}
          </span>
        </div>
      </aside>

      <main className="flex-1 flex flex-col">
        <header className="border-b border-slate-800/80 bg-slate-950/70 backdrop-blur-md">
          <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-slate-800/80 bg-slate-900/80 px-3 py-1 text-xs text-slate-400 mb-2">
                <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(74,222,128,0.8)]" />
                Live scraper environment
              </div>
              <h1 className="text-lg md:text-xl font-semibold tracking-tight text-slate-50">
                Dashboard Control Center
              </h1>
              <p className="text-xs md:text-sm text-slate-400">
                Configure targets, launch jobs, and inspect fresh listings from
                your multi-site real-estate scraper.
              </p>
            </div>
            <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400">
              <span className="h-8 w-px bg-slate-800" />
              <span className="font-mono text-[11px] tracking-tight">
                Phase 2 · UI Foundation
              </span>
            </div>
          </div>
        </header>

        <div className="flex-1 max-w-6xl mx-auto w-full px-3 md:px-4 py-4 md:py-6 space-y-4 md:space-y-6">
          <section className="grid gap-3 md:gap-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
            <div className="rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900/80 shadow-[0_18px_60px_rgba(15,23,42,0.9)]">
              <div className="px-4 pt-4 pb-3 border-b border-slate-800/80 flex items-center justify-between gap-2">
                <div>
                  <h2 className="text-sm font-semibold text-slate-50">
                    Main Control Panel
                  </h2>
                  <p className="text-xs text-slate-400">
                    Choose a target site, tune scope, and dispatch a new job.
                  </p>
                </div>
              </div>
              <div className="px-4 pb-4 pt-3 space-y-3">
                <ProgressStrip telemetry={telemetry} isLoading={isLoadingTelemetry} />
                <div className="grid gap-3 md:grid-cols-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-slate-300">
                      Target site
                    </label>
                    <select
                      className="w-full rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-100 outline-none ring-0 focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500/40"
                      value={form.site}
                      onChange={(e) =>
                        setForm((prev) => ({ ...prev, site: e.target.value }))
                      }
                    >
                      {SITES.map((site) => (
                        <option key={site.value} value={site.value}>
                          {site.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-1.5 md:col-span-2">
                    <label className="text-xs font-medium text-slate-300 flex items-center justify-between">
                      Start URL / Search query
                      <span className="text-[11px] font-normal text-slate-500">
                        Optional – falls back to site defaults
                      </span>
                    </label>
                    <input
                      className="w-full rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-100 outline-none ring-0 placeholder:text-slate-600 focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500/40"
                      placeholder="https://www.property24.com/for-sale/..."
                      value={form.url ?? ''}
                      onChange={(e) =>
                        setForm((prev) => ({ ...prev, url: e.target.value }))
                      }
                    />
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <SliderField
                    label="Hard item limit"
                    hint="Optional safety cap on total listings saved."
                    min={20}
                    max={500}
                    step={10}
                    value={form.limit ?? 100}
                    onChange={(value) =>
                      setForm((prev) => ({ ...prev, limit: value }))
                    }
                    enabled={useLimit}
                    onToggleEnabled={setUseLimit}
                  />
                  <SliderField
                    label="Max pages"
                    hint="Optional cap on pagination depth."
                    min={1}
                    max={25}
                    step={1}
                    value={form.max_pages ?? 5}
                    onChange={(value) =>
                      setForm((prev) => ({ ...prev, max_pages: value }))
                    }
                    enabled={useMaxPages}
                    onToggleEnabled={setUseMaxPages}
                  />
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                  <div className="flex flex-col gap-2 text-xs text-slate-400">
                    <label className="inline-flex items-center gap-2">
                      <input
                        type="checkbox"
                        className="h-3.5 w-3.5 rounded border-slate-700 bg-slate-900 text-indigo-400 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-indigo-500"
                        checked={form.skip_dynamic_fields ?? false}
                        onChange={(e) =>
                          setForm((prev) => ({
                            ...prev,
                            skip_dynamic_fields: e.target.checked,
                          }))
                        }
                      />
                      <span>
                        Skip dynamic fields{' '}
                        <span className="text-slate-500">
                          (bypass Selenium / phone extraction)
                        </span>
                      </span>
                    </label>
                    <div className="inline-flex items-center gap-2 rounded-full border border-slate-800/80 bg-slate-900/80 px-2 py-1">
                      <span className="inline-flex h-1.5 w-5 rounded-full bg-gradient-to-r from-emerald-400 via-indigo-400 to-sky-400 shadow-[0_0_12px_rgba(129,140,248,0.9)]" />
                      <span>Multi-site ready</span>
                    </div>
                    <span className="hidden sm:inline text-slate-600">
                      · Phase 2 control surface
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={!activeJob?.job_id || isTerminating}
                      onClick={() => void handleTerminateJob()}
                    >
                      <Square className="h-3.5 w-3.5" />
                      {isTerminating ? 'Terminating…' : 'Terminate'}
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      onClick={() => void handleRunJob()}
                      disabled={isRunning}
                    >
                      <Play className="h-3.5 w-3.5" />
                      {isRunning ? 'Launching…' : 'Run job'}
                    </Button>
                  </div>
                </div>

                {statusMessage && (
                  <div className="rounded-xl border border-slate-800/80 bg-slate-900/80 px-3 py-2 text-xs text-slate-300">
                    {statusMessage}
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-950 to-slate-900/80">
              <div className="px-4 pt-4 pb-3 border-b border-slate-800/80 flex items-center justify-between gap-2">
                <div>
                  <h2 className="text-sm font-semibold text-slate-50">
                    Recent Jobs
                  </h2>
                  <p className="text-xs text-slate-400">
                    Lightweight snapshot of your latest scraper runs.
                  </p>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    void reloadJobs();
                    void reloadListings(selectedJobId);
                  }}
                  aria-label="Refresh jobs"
                >
                  <Radar className="h-4 w-4 text-indigo-300" />
                </Button>
              </div>
              <div className="px-4 pb-4 pt-2">
                <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1 custom-scroll">
                  {isLoadingJobs && (
                    <div className="text-xs text-slate-500 py-2">
                      Loading jobs…
                    </div>
                  )}
                  {!isLoadingJobs && jobs.length === 0 && (
                    <div className="text-xs text-slate-500 py-2">
                      No jobs recorded yet. Launch your first scrape from the
                      control panel.
                    </div>
                  )}
                  {jobs.map((job) => {
                    const isSelected = job.job_id === activeJob?.job_id;
                    return (
                      <button
                        key={job.job_id}
                        type="button"
                        onClick={() => {
                          setSelectedJobId(job.job_id);
                          void reloadListings(job.job_id);
                        }}
                        className={[
                          'w-full text-left rounded-xl border px-3 py-2.5 transition-colors',
                          isSelected
                            ? 'border-indigo-500/70 bg-slate-900/90 shadow-sm shadow-indigo-500/20'
                            : 'border-slate-800 bg-slate-950/60 hover:bg-slate-900/80',
                        ].join(' ')}
                      >
                        <div className="flex items-center justify-between gap-2 mb-0.5">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-slate-100">
                              {job.site}
                            </span>
                            <span className="h-1 w-1 rounded-full bg-slate-700" />
                            <span className="text-[11px] uppercase tracking-wide text-slate-500">
                              {job.status}
                            </span>
                          </div>
                          {job.items_scraped != null && (
                            <span className="text-[11px] text-slate-400">
                              {job.items_scraped} items
                            </span>
                          )}
                        </div>
                        <div className="flex items-center justify-between gap-2 text-[11px] text-slate-500">
                          <span className="font-mono">
                            {job.started_at ?? '—'}
                          </span>
                          <span className="font-mono text-slate-600">
                            {job.job_id}
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </section>

          <section className="rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900/80">
            <div className="px-4 pt-4 pb-3 border-b border-slate-800/80 flex items-center justify-between gap-2">
              <div>
                <h2 className="text-sm font-semibold text-slate-50">
                  Latest Listings
                  {activeJob?.job_id && (
                    <span className="ml-2 text-[11px] font-mono text-indigo-400 font-normal">
                      ({activeJob.job_id})
                    </span>
                  )}
                </h2>
                <p className="text-xs text-slate-400">
                  {activeJob?.job_id
                    ? `Showing results for job ${activeJob.job_id} on ${activeJob.site}.`
                    : "A compact data grid of the most recent records across all jobs."}
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span className="hidden sm:inline">
                  Showing up to 25 items
                </span>
                <span className="inline-flex items-center gap-1 rounded-full border border-slate-800/80 bg-slate-900/80 px-2 py-0.5 font-mono text-[10px] text-slate-400">
                  {isLoadingListings
                    ? 'Loading…'
                    : `${listings.length.toString().padStart(2, '0')} rows`}
                </span>
              </div>
            </div>
            <div className="px-3 pb-4 pt-2 overflow-x-auto">
              <table className="min-w-full border-separate border-spacing-y-1 text-xs">
                <thead className="text-[11px] uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="text-left px-3 py-1.5 font-medium">Title</th>
                    <th className="text-left px-3 py-1.5 font-medium">
                      Price
                    </th>
                    <th className="text-left px-3 py-1.5 font-medium">
                      Location
                    </th>
                    <th className="hidden md:table-cell text-left px-3 py-1.5 font-medium">
                      Beds / Baths
                    </th>
                    <th className="hidden lg:table-cell text-left px-3 py-1.5 font-medium">
                      Type
                    </th>
                    <th className="text-left px-3 py-1.5 font-medium">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {listings.length === 0 && !isLoadingListings && (
                    <tr>
                      <td
                        colSpan={6}
                        className="px-3 py-4 text-center text-xs text-slate-500"
                      >
                        No listings available yet. Once a job completes, its
                        freshest rows will appear here.
                      </td>
                    </tr>
                  )}
                  {listings.map((listing) => (
                    <tr key={`${listing.id}-${listing.listing_url ?? ''}`}>
                      <td className="align-top">
                        <div className="rounded-xl bg-slate-950/80 border border-slate-800/80 px-3 py-2 shadow-sm shadow-slate-950/60">
                          <div className="text-xs font-medium text-slate-50 line-clamp-2">
                            {listing.title || 'Untitled listing'}
                          </div>
                          <div className="mt-1 flex items-center justify-between gap-2 text-[11px] text-slate-500">
                            <span className="line-clamp-1">
                              {listing.location || '—'}
                            </span>
                            {listing.listing_url && (
                              <a
                                href={listing.listing_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-indigo-300 hover:text-indigo-200"
                              >
                                View
                              </a>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="align-top px-3 py-1.5 text-[11px] text-slate-200 whitespace-nowrap">
                        {listing.price || '—'}
                      </td>
                      <td className="align-top px-3 py-1.5 text-[11px] text-slate-300 whitespace-nowrap">
                        {listing.location || '—'}
                      </td>
                      <td className="align-top px-3 py-1.5 text-[11px] text-slate-300 hidden md:table-cell whitespace-nowrap">
                        {listing.bedrooms ?? '—'} / {listing.bathrooms ?? '—'}
                      </td>
                      <td className="align-top px-3 py-1.5 text-[11px] text-slate-400 hidden lg:table-cell whitespace-nowrap">
                        {listing.property_type || '—'}
                      </td>
                      <td className="align-top px-3 py-1.5 text-[11px] text-slate-400 whitespace-nowrap">
                        {listing.source_site || form.site}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900/80">
            <div className="px-4 pt-4 pb-3 border-b border-slate-800/80 flex items-center justify-between gap-2">
              <div>
                <h2 className="text-sm font-semibold text-slate-50">
                  Live Console
                </h2>
                <p className="text-xs text-slate-400">
                  Streaming tail of the active job log (polling).
                </p>
              </div>
              <div className="text-[11px] text-slate-500 font-mono">
                {isLoadingLogs ? 'Loading…' : activeJob?.job_id ?? '—'}
              </div>
            </div>
            <div className="px-4 py-3">
              <div 
                ref={logContainerRef}
                className="rounded-xl border border-slate-800/80 bg-black/40 px-3 py-2 font-mono text-[11px] leading-relaxed text-slate-200 max-h-[280px] overflow-y-auto"
              >
                {logLines.length === 0 ? (
                  <div className="text-slate-500">
                    No logs yet. Start a job to stream output here.
                  </div>
                ) : (
                  <>
                    {logLines.map((l, idx) => (
                      <div key={`${idx}-${l.slice(0, 12)}`} className="whitespace-pre-wrap">
                        {l}
                      </div>
                    ))}
                    <div ref={logBottomRef} />
                  </>
                )}
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

function ProgressStrip({
  telemetry,
  isLoading,
}: {
  telemetry: JobTelemetry | null;
  isLoading: boolean;
}) {
  const progress = telemetry?.runtime?.progress;
  const mode = telemetry?.runtime?.progress_mode;
  const isAlive = telemetry?.runtime?.is_alive;

  const pct =
    typeof progress === 'number' && Number.isFinite(progress)
      ? Math.round(progress * 100)
      : null;

  const itemsScraped = telemetry?.job?.items_scraped as number | undefined;
  const limit = telemetry?.stats?.limit as number | undefined;
  const itemsDiscovered = telemetry?.stats?.items_discovered as number | undefined;
  const itemsProcessed = telemetry?.stats?.items_processed as number | undefined;

  let label = 'Progress unavailable';
  if (mode === 'items' && typeof itemsScraped === 'number' && typeof limit === 'number') {
    label = `${itemsScraped} / ${limit} items`;
  } else if (mode === 'dynamic' && typeof itemsProcessed === 'number' && typeof itemsDiscovered === 'number') {
    label = `${itemsProcessed} / ${itemsDiscovered} links processed`;
  } else if (typeof itemsScraped === 'number') {
    label = `${itemsScraped} items scraped`;
  }

  return (
    <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="text-xs text-slate-300">
          <span className="font-medium text-slate-100">Telemetry</span>{' '}
          <span className="text-slate-500">·</span>{' '}
          <span className="text-slate-400">
            {isLoading ? 'Updating…' : isAlive ? 'Running' : 'Idle'}
          </span>
        </div>
        <div className="text-[11px] text-slate-400 font-mono">
          {pct != null ? `${pct}%` : '—'}
        </div>
      </div>
      <div className="h-2 rounded-full bg-slate-900 border border-slate-800/70 overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-indigo-500 via-sky-400 to-emerald-400"
          style={{ width: pct != null ? `${pct}%` : '6%' }}
        />
      </div>
      <div className="mt-2 text-[11px] text-slate-400">{label}</div>
    </div>
  );
}

interface SliderFieldProps {
  label: string;
  hint?: string;
  min: number;
  max: number;
  step?: number;
  value: number;
  onChange: (value: number) => void;
  enabled?: boolean;
  onToggleEnabled?: (enabled: boolean) => void;
}

function SliderField({
  label,
  hint,
  min,
  max,
  step = 1,
  value,
  onChange,
  enabled = true,
  onToggleEnabled,
}: SliderFieldProps) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <label className="text-xs font-medium text-slate-300 flex items-center gap-2">
          {onToggleEnabled && (
            <input
              type="checkbox"
              className="h-3 w-3 rounded border-slate-700 bg-slate-900 text-indigo-400 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-indigo-500"
              checked={enabled}
              onChange={(e) => onToggleEnabled(e.target.checked)}
            />
          )}
          <span>{label}</span>
        </label>
        <span className="text-[11px] text-slate-400">
          {enabled
            ? `${value} ${label.toLowerCase().includes('pages') ? 'pages' : 'items'
            }`
            : 'Off (use defaults)'}
        </span>
      </div>
      {hint && (
        <p className="text-[11px] text-slate-500 mb-1.5 line-clamp-1">
          {hint}
        </p>
      )}
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-indigo-400 disabled:opacity-40"
        disabled={!enabled}
      />
      <div className="flex justify-between text-[10px] text-slate-600">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}

export default App;
