export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000/api/v1";

export type ApiError = { detail?: string };

export type User = {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
};

export type Target = {
  id: string;
  name: string;
  target_type: "url" | "github" | "api" | string;
  target_url: string;
  scope: string[];
  authorization_status: string;
  authorization_proof_type: string | null;
  created_at: string;
};

export type Scan = {
  id: string;
  target_id: string;
  requested_by_id: string;
  scan_type: string;
  status: string;
  scope: string[];
  celery_task_id: string | null;
  summary: string | null;
  agent_trace: Array<Record<string, unknown>>;
  report_json: Record<string, unknown> | null;
  armoriq_token: string | null;
  intent_plan: Record<string, unknown> | null;
  policy_decisions: Array<Record<string, unknown>>;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};

export type Finding = {
  id: string;
  scan_id: string;
  severity: string;
  title: string;
  location: string;
  confidence: number;
  risk_score: number;
  risk_rating: string;
  status: string;
  summary: string;
  business_impact: string | null;
  remediation: string | null;
  risk_factors: Record<string, unknown>;
  reproduction_steps: string[];
  created_at: string;
};

export type AuditEvent = {
  id: string;
  user_id: string | null;
  target_id: string | null;
  scan_id: string | null;
  event_type: string;
  message: string;
  details: Record<string, unknown> | null;
  created_at: string;
};

export type ScanCreateResponse = { scan: Scan; target: Target };

export function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` };
}

export function splitScope(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export async function readError(response: Response) {
  try {
    const body = (await response.json()) as ApiError;
    return body.detail || `${response.status} ${response.statusText}`;
  } catch {
    return `${response.status} ${response.statusText}`;
  }
}

export function shortId(value: string) {
  return value.slice(0, 8);
}

export function severityStyle(value: string) {
  switch (value.toLowerCase()) {
    case "critical":
      return "border-[#ff7c70]/40 bg-[#5f1919] text-[#ffb3ad]";
    case "high":
      return "border-[#ffb15f]/40 bg-[#5e3512] text-[#ffd8ad]";
    case "medium":
      return "border-[#e2eb72]/40 bg-[#3f4216] text-[#eef5a3]";
    case "low":
      return "border-[#8bd8ff]/35 bg-[#16364a] text-[#b9e7ff]";
    default:
      return "border-white/10 bg-white/8 text-white/70";
  }
}

export function statusStyle(value: string) {
  switch (value.toLowerCase()) {
    case "completed":
    case "verified":
      return "text-[#a8ff3e]";
    case "queued":
    case "planning":
    case "executing":
    case "observing":
    case "reflecting":
      return "text-[#ffd38f]";
    case "failed":
    case "cancelled":
    case "pending":
      return "text-[#ffaaa4]";
    default:
      return "text-white/60";
  }
}