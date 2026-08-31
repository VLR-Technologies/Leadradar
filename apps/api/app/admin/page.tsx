"use client";

import { useState } from "react";
import { ApiError } from "@/lib/api/client";
import {
  getAdminCalls,
  purgeAdminCalls,
  type CallLogEntry,
  type CallLogSummary,
} from "@/lib/api/calls";

export default function AdminPage() {
  const [key, setKey] = useState("");
  const [summary, setSummary] = useState<CallLogSummary | null>(null);
  const [recent, setRecent] = useState<CallLogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await getAdminCalls(key);
      setSummary(data.summary);
      setRecent(data.recent);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load call data.");
      setSummary(null);
      setRecent([]);
    } finally {
      setLoading(false);
    }
  }

  async function purge() {
    if (!confirm("Delete all call records older than 4 days?")) return;
    setLoading(true);
    try {
      const result = await purgeAdminCalls(key, 4);
      alert(`Deleted ${result.deleted} record(s).`);
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not purge records.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-5xl p-8">
      <h1 className="text-2xl font-semibold">Call log admin</h1>

      <div className="mt-6 flex gap-2">
        <input
          type="password"
          value={key}
          onChange={(event) => setKey(event.target.value)}
          placeholder="Admin key"
          className="w-72 rounded-lg border border-[#cfdad4] px-3 py-2"
        />
        <button
          onClick={load}
          disabled={!key || loading}
          className="rounded-lg bg-[#177454] px-4 py-2 text-white disabled:opacity-50"
        >
          {loading ? "Loading..." : "Load"}
        </button>
      </div>

      {error ? (
        <p className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-red-700">{error}</p>
      ) : null}

      {summary ? (
        <>
          <div className="mt-8 grid grid-cols-4 gap-4">
            {[
              ["Total calls", summary.total],
              ["Yes", summary.yes],
              ["No", summary.no],
              ["Today", summary.today],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-2xl border border-[#cfdad4] p-4">
                <p className="text-3xl font-semibold">{value}</p>
                <p className="mt-1 text-sm text-[#738078]">{label}</p>
              </div>
            ))}
          </div>

          <button
            onClick={purge}
            disabled={loading}
            className="mt-6 rounded-lg border border-red-300 px-4 py-2 text-red-700 disabled:opacity-50"
          >
            Delete records older than 4 days
          </button>

          <table className="mt-8 w-full text-left text-sm">
            <thead className="border-b border-[#cfdad4]">
              <tr>
                <th className="py-2">Business</th>
                <th className="py-2">Phone</th>
                <th className="py-2">Decision</th>
                <th className="py-2">When</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((entry, index) => (
                <tr key={`${entry.lead_key}-${index}`} className="border-b border-[#eef2f0]">
                  <td className="py-2">{entry.business_name || entry.lead_key}</td>
                  <td className="py-2">{entry.phone || "—"}</td>
                  <td className="py-2">{entry.decision === "yes" ? "✓ Yes" : "✕ No"}</td>
                  <td className="py-2">{new Date(entry.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : null}
    </main>
  );
}