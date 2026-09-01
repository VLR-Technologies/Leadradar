import { apiRequest } from "@/lib/api/client";

export interface CallDecisionPayload {
  lead_key: string;
  business_name: string;
  phone: string;
  decision: "yes" | "no";
}

export interface CallLogSummary {
  total: number;
  yes: number;
  no: number;
  today: number;
}

export interface CallLogEntry {
  lead_key: string;
  business_name: string;
  phone: string;
  decision: "yes" | "no";
  created_at: string;
}

export function recordCallDecision(payload: CallDecisionPayload): Promise<void> {
  return apiRequest<void>("/api/v1/calls", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getAdminCalls(
  adminKey: string,
): Promise<{ summary: CallLogSummary; recent: CallLogEntry[] }> {
  return apiRequest<{ summary: CallLogSummary; recent: CallLogEntry[] }>(
    "/api/v1/admin/calls",
    { headers: { "X-Admin-Key": adminKey } },
  );
}

export function purgeAdminCalls(
  adminKey: string,
  days: number,
): Promise<{ deleted: number }> {
  return apiRequest<{ deleted: number }>(
    `/api/v1/admin/calls/purge?days=${days}`,
    { method: "POST", headers: { "X-Admin-Key": adminKey } },
  );
}
