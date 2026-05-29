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

export type Organization = {
  id: string;
  name: string;
  slug: string;
  created_by_id: string | null;
  created_at: string;
};

export type Target = {
  id: string;
  name: string;
  organization_id: string | null;
  target_type: "url" | "github" | "api" | string;
  target_url: string;
  scope: string[];
  authorization_status: string;
  authorization_proof_type: string | null;
  authorization_verified_at?: string | null;
  created_at: string;
};

export type AuthorizationProof = {
  id: string;
  target_id: string;
  created_by_id: string | null;
  proof_type: string;
  status: string;
  challenge_token: string;
  verification_target: string;
  expected_value: string;
  submitted_value: string | null;
  instructions: string | null;
  metadata_json: Record<string, unknown>;
  failure_reason: string | null;
  last_checked_at: string | null;
  verified_at: string | null;
  expires_at: string | null;
  created_at: string;
};

export type Scan = {
  id: string;
  target_id: string;
  organization_id: string | null;
  requested_by_id: string;
  scan_profile_id: string | null;
  parent_scan_id: string | null;
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

export type Membership = {
  id: string;
  organization_id: string;
  user_id: string;
  role: string;
  created_at: string;
};

export type Team = {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  created_at: string;
};

export type ScanProfile = {
  id: string;
  organization_id: string | null;
  created_by_id: string | null;
  name: string;
  description: string | null;
  scan_type: string;
  policy_tier: string;
  settings_json: Record<string, unknown>;
  is_default: boolean;
  created_at: string;
};

export type ScanArtifact = {
  id: string;
  scan_id: string;
  artifact_type: string;
  name: string;
  uri: string | null;
  content_type: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
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

export type FindingEvidence = {
  id: string;
  finding_id: string;
  evidence_type: string;
  title: string;
  content: string | null;
  artifact_uri: string | null;
  metadata_json: Record<string, unknown>;
  created_by_id: string | null;
  created_at: string;
};

export type FindingComment = {
  id: string;
  finding_id: string;
  author_id: string | null;
  body: string;
  created_at: string;
};

export type FindingSuppression = {
  id: string;
  finding_id: string;
  created_by_id: string | null;
  reason: string;
  status: string;
  expires_at: string | null;
  created_at: string;
};

export type RemediationHistory = {
  id: string;
  finding_id: string;
  actor_id: string | null;
  from_status: string | null;
  to_status: string;
  note: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type FindingDetail = Finding & {
  evidence: FindingEvidence[];
  comments: FindingComment[];
  suppressions: FindingSuppression[];
  remediation_history: RemediationHistory[];
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

export type CredentialReference = {
  id: string;
  organization_id: string | null;
  created_by_id: string | null;
  name: string;
  credential_type: string;
  vault_provider: string;
  vault_reference: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type WebhookIntegration = {
  id: string;
  organization_id: string | null;
  created_by_id: string | null;
  name: string;
  event_types: string[];
  target_url: string;
  secret_reference: string | null;
  is_active: boolean;
  created_at: string;
};

export type ToolInventory = {
  id: string;
  name: string;
  category: string;
  version: string | null;
  status: string;
  capabilities: string[];
  last_checked_at: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type AgentExecutionLog = {
  id: string;
  scan_id: string | null;
  agent_name: string;
  stage: string;
  status: string;
  message: string | null;
  duration_ms: number | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type ReportExport = {
  id: string;
  scan_id: string;
  requested_by_id: string | null;
  export_type: string;
  status: string;
  artifact_uri: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type ScanCreateResponse = { scan: Scan; target: Target };

export function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` };
}

export async function apiRequest<T>(token: string, path: string, options: RequestInit = {}): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  if (!r.ok) throw new Error(await readError(r));
  if (r.status === 204) return undefined as T;
  return (await r.json()) as T;
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
    case "attested":
      return "text-[#ffd38f]";
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
