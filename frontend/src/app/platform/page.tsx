"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useAuth } from "../lib/auth-context";
import {
  AgentExecutionLog,
  apiRequest,
  CredentialReference,
  Organization,
  ScanProfile,
  ToolInventory,
  WebhookIntegration,
  shortId,
} from "../lib/api";
import { EmptyState, GreenButton, LoadingState, Panel, StatusBadge } from "../components/ui";

const profileEmpty = { organization_id: "", name: "", description: "", scan_type: "url", policy_tier: "passive", is_default: false };
const credentialEmpty = { organization_id: "", name: "", credential_type: "api_key", vault_provider: "external", vault_reference: "" };
const webhookEmpty = { organization_id: "", name: "", target_url: "", event_types: "scan.completed,scan.failed", secret_reference: "", is_active: true };
const toolEmpty = { name: "", category: "scanner", version: "", status: "unknown", capabilities: "" };

export default function PlatformPage() {
  const { token, isLoaded } = useAuth();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [profiles, setProfiles] = useState<ScanProfile[]>([]);
  const [credentials, setCredentials] = useState<CredentialReference[]>([]);
  const [webhooks, setWebhooks] = useState<WebhookIntegration[]>([]);
  const [tools, setTools] = useState<ToolInventory[]>([]);
  const [logs, setLogs] = useState<AgentExecutionLog[]>([]);
  const [profileForm, setProfileForm] = useState(profileEmpty);
  const [credentialForm, setCredentialForm] = useState(credentialEmpty);
  const [webhookForm, setWebhookForm] = useState(webhookEmpty);
  const [toolForm, setToolForm] = useState(toolEmpty);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const [orgs, p, c, w, t, l] = await Promise.all([
        apiRequest<Organization[]>(token, "/organizations/"),
        apiRequest<ScanProfile[]>(token, "/platform/scan-profiles"),
        apiRequest<CredentialReference[]>(token, "/platform/credentials"),
        apiRequest<WebhookIntegration[]>(token, "/platform/webhooks"),
        apiRequest<ToolInventory[]>(token, "/platform/tools"),
        apiRequest<AgentExecutionLog[]>(token, "/platform/agent-logs?limit=50"),
      ]);
      setOrganizations(orgs);
      setProfiles(p);
      setCredentials(c);
      setWebhooks(w);
      setTools(t);
      setLogs(l);
      const firstOrg = orgs[0]?.id || "";
      setProfileForm(prev => prev.organization_id ? prev : { ...prev, organization_id: firstOrg });
      setCredentialForm(prev => prev.organization_id ? prev : { ...prev, organization_id: firstOrg });
      setWebhookForm(prev => prev.organization_id ? prev : { ...prev, organization_id: firstOrg });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load platform data");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { if (!isLoaded) return; load().catch(e => setError(e.message)); }, [load, isLoaded]);

  async function submitProfile(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy("profile"); setError(""); setMessage("");
    try {
      await apiRequest<ScanProfile>(token, "/platform/scan-profiles", {
        method: "POST",
        body: JSON.stringify({ ...profileForm, organization_id: profileForm.organization_id || null, description: profileForm.description || null }),
      });
      setProfileForm(profileEmpty);
      await load();
      setMessage("Scan profile created.");
    } catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setBusy(""); }
  }

  async function submitCredential(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy("credential"); setError(""); setMessage("");
    try {
      await apiRequest<CredentialReference>(token, "/platform/credentials", {
        method: "POST",
        body: JSON.stringify({ ...credentialForm, organization_id: credentialForm.organization_id || null, metadata_json: {} }),
      });
      setCredentialForm(credentialEmpty);
      await load();
      setMessage("Credential reference created.");
    } catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setBusy(""); }
  }

  async function submitWebhook(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy("webhook"); setError(""); setMessage("");
    try {
      await apiRequest<WebhookIntegration>(token, "/platform/webhooks", {
        method: "POST",
        body: JSON.stringify({
          ...webhookForm,
          organization_id: webhookForm.organization_id || null,
          event_types: webhookForm.event_types.split(",").map(item => item.trim()).filter(Boolean),
          secret_reference: webhookForm.secret_reference || null,
        }),
      });
      setWebhookForm(webhookEmpty);
      await load();
      setMessage("Webhook integration created.");
    } catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setBusy(""); }
  }

  async function submitTool(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy("tool"); setError(""); setMessage("");
    try {
      await apiRequest<ToolInventory>(token, `/platform/tools/${encodeURIComponent(toolForm.name)}`, {
        method: "PUT",
        body: JSON.stringify({
          name: toolForm.name,
          category: toolForm.category,
          version: toolForm.version || null,
          status: toolForm.status,
          capabilities: toolForm.capabilities.split(",").map(item => item.trim()).filter(Boolean),
          metadata_json: {},
        }),
      });
      setToolForm(toolEmpty);
      await load();
      setMessage("Tool inventory updated.");
    } catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setBusy(""); }
  }

  return (
    <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-[1500px] space-y-5">
        <header className="rounded-2xl border border-white/7 bg-[#080f18] p-6">
          <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-[#a8ff3e]/60">Operations</p>
          <h1 className="mt-2 font-mono text-3xl font-bold text-white">Platform Control</h1>
          <p className="mt-2 font-mono text-xs text-white/35">Configure scan profiles, credential references, webhooks, tool inventory, and inspect agent logs.</p>
          {(message || error) && (
            <div className="mt-4 space-y-2">
              {message && <p className="rounded-xl border border-[#a8ff3e]/15 bg-[#a8ff3e]/6 px-4 py-2 font-mono text-xs text-[#a8ff3e]/80">{message}</p>}
              {error && <p className="rounded-xl border border-[#ff7c70]/20 bg-[#ff7c70]/6 px-4 py-2 font-mono text-xs text-[#ffb3ad]">{error}</p>}
            </div>
          )}
        </header>

        {loading ? <LoadingState text="Loading platform endpoints..." /> : (
          <div className="grid gap-5 xl:grid-cols-2">
            <Panel title="Scan profiles" eyebrow="GET/POST /platform/scan-profiles">
              <form onSubmit={submitProfile} className="mb-4 grid gap-2 md:grid-cols-2">
                <select className="field" value={profileForm.organization_id} onChange={e => setProfileForm({ ...profileForm, organization_id: e.target.value })}>
                  <option value="">No organization</option>
                  {organizations.map(org => <option key={org.id} value={org.id}>{org.name}</option>)}
                </select>
                <input className="field" placeholder="Profile name" value={profileForm.name} onChange={e => setProfileForm({ ...profileForm, name: e.target.value })} />
                <select className="field" value={profileForm.scan_type} onChange={e => setProfileForm({ ...profileForm, scan_type: e.target.value })}>
                  <option value="url">url</option><option value="api">api</option><option value="github">github</option>
                </select>
                <select className="field" value={profileForm.policy_tier} onChange={e => setProfileForm({ ...profileForm, policy_tier: e.target.value })}>
                  <option value="passive">passive</option><option value="safe_active">safe active</option><option value="advanced_validated">advanced validated</option>
                </select>
                <input className="field md:col-span-2" placeholder="Description" value={profileForm.description} onChange={e => setProfileForm({ ...profileForm, description: e.target.value })} />
                <GreenButton type="submit" disabled={busy === "profile" || !profileForm.name} className="md:col-span-2">{busy === "profile" ? "Creating..." : "Create profile"}</GreenButton>
              </form>
              {profiles.length === 0 ? <EmptyState text="No scan profiles configured." /> : <div className="space-y-2">{profiles.map(profile => (
                <div key={profile.id} className="rounded-xl border border-white/7 bg-[#05090f] p-3">
                  <p className="font-mono text-sm text-white">{profile.name}</p>
                  <p className="font-mono text-[10px] text-white/35">{profile.scan_type} · {profile.policy_tier} · {shortId(profile.id)}</p>
                </div>
              ))}</div>}
            </Panel>

            <Panel title="Credentials" eyebrow="GET/POST /platform/credentials">
              <form onSubmit={submitCredential} className="mb-4 grid gap-2 md:grid-cols-2">
                <select className="field" value={credentialForm.organization_id} onChange={e => setCredentialForm({ ...credentialForm, organization_id: e.target.value })}>
                  <option value="">No organization</option>{organizations.map(org => <option key={org.id} value={org.id}>{org.name}</option>)}
                </select>
                <input className="field" placeholder="Credential name" value={credentialForm.name} onChange={e => setCredentialForm({ ...credentialForm, name: e.target.value })} />
                <input className="field" placeholder="Type" value={credentialForm.credential_type} onChange={e => setCredentialForm({ ...credentialForm, credential_type: e.target.value })} />
                <input className="field" placeholder="Vault provider" value={credentialForm.vault_provider} onChange={e => setCredentialForm({ ...credentialForm, vault_provider: e.target.value })} />
                <input className="field md:col-span-2" placeholder="Vault reference" value={credentialForm.vault_reference} onChange={e => setCredentialForm({ ...credentialForm, vault_reference: e.target.value })} />
                <GreenButton type="submit" disabled={busy === "credential" || !credentialForm.name || !credentialForm.vault_reference} className="md:col-span-2">{busy === "credential" ? "Creating..." : "Create credential"}</GreenButton>
              </form>
              {credentials.length === 0 ? <EmptyState text="No credential references." /> : <div className="space-y-2">{credentials.map(item => (
                <div key={item.id} className="rounded-xl border border-white/7 bg-[#05090f] p-3">
                  <p className="font-mono text-sm text-white">{item.name}</p>
                  <p className="font-mono text-[10px] text-white/35">{item.credential_type} · {item.vault_provider}</p>
                </div>
              ))}</div>}
            </Panel>

            <Panel title="Webhooks" eyebrow="GET/POST /platform/webhooks">
              <form onSubmit={submitWebhook} className="mb-4 grid gap-2 md:grid-cols-2">
                <select className="field" value={webhookForm.organization_id} onChange={e => setWebhookForm({ ...webhookForm, organization_id: e.target.value })}>
                  <option value="">No organization</option>{organizations.map(org => <option key={org.id} value={org.id}>{org.name}</option>)}
                </select>
                <input className="field" placeholder="Webhook name" value={webhookForm.name} onChange={e => setWebhookForm({ ...webhookForm, name: e.target.value })} />
                <input className="field md:col-span-2" placeholder="Target URL" value={webhookForm.target_url} onChange={e => setWebhookForm({ ...webhookForm, target_url: e.target.value })} />
                <input className="field" placeholder="Events, comma-separated" value={webhookForm.event_types} onChange={e => setWebhookForm({ ...webhookForm, event_types: e.target.value })} />
                <input className="field" placeholder="Secret reference" value={webhookForm.secret_reference} onChange={e => setWebhookForm({ ...webhookForm, secret_reference: e.target.value })} />
                <GreenButton type="submit" disabled={busy === "webhook" || !webhookForm.name || !webhookForm.target_url} className="md:col-span-2">{busy === "webhook" ? "Creating..." : "Create webhook"}</GreenButton>
              </form>
              {webhooks.length === 0 ? <EmptyState text="No webhook integrations." /> : <div className="space-y-2">{webhooks.map(item => (
                <div key={item.id} className="rounded-xl border border-white/7 bg-[#05090f] p-3">
                  <div className="flex items-center justify-between gap-2"><p className="font-mono text-sm text-white">{item.name}</p><StatusBadge value={item.is_active ? "active" : "disabled"} /></div>
                  <p className="mt-1 truncate font-mono text-[10px] text-white/35">{item.target_url}</p>
                </div>
              ))}</div>}
            </Panel>

            <Panel title="Tools and agent logs" eyebrow="GET/PUT /platform/tools · GET /platform/agent-logs">
              <form onSubmit={submitTool} className="mb-4 grid gap-2 md:grid-cols-2">
                <input className="field" placeholder="Tool name" value={toolForm.name} onChange={e => setToolForm({ ...toolForm, name: e.target.value })} />
                <input className="field" placeholder="Category" value={toolForm.category} onChange={e => setToolForm({ ...toolForm, category: e.target.value })} />
                <input className="field" placeholder="Version" value={toolForm.version} onChange={e => setToolForm({ ...toolForm, version: e.target.value })} />
                <select className="field" value={toolForm.status} onChange={e => setToolForm({ ...toolForm, status: e.target.value })}>
                  <option value="available">available</option><option value="missing">missing</option><option value="unknown">unknown</option><option value="disabled">disabled</option>
                </select>
                <input className="field md:col-span-2" placeholder="Capabilities, comma-separated" value={toolForm.capabilities} onChange={e => setToolForm({ ...toolForm, capabilities: e.target.value })} />
                <GreenButton type="submit" disabled={busy === "tool" || !toolForm.name} className="md:col-span-2">{busy === "tool" ? "Updating..." : "Upsert tool"}</GreenButton>
              </form>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  {tools.length === 0 ? <EmptyState text="No tools inventoried." /> : tools.map(tool => (
                    <div key={tool.id} className="rounded-xl border border-white/7 bg-[#05090f] p-3">
                      <div className="flex items-center justify-between gap-2"><p className="font-mono text-xs text-white">{tool.name}</p><StatusBadge value={tool.status} /></div>
                      <p className="font-mono text-[10px] text-white/30">{tool.category} · {tool.version || "unknown version"}</p>
                    </div>
                  ))}
                </div>
                <div className="space-y-2">
                  {logs.length === 0 ? <EmptyState text="No agent logs yet." /> : logs.slice(0, 8).map(log => (
                    <div key={log.id} className="rounded-xl border border-white/7 bg-[#05090f] p-3">
                      <div className="flex items-center justify-between gap-2"><p className="font-mono text-xs text-white">{log.agent_name}</p><StatusBadge value={log.status} /></div>
                      <p className="mt-1 font-mono text-[10px] text-white/35">{log.stage} · {log.message || "No message"}</p>
                    </div>
                  ))}
                </div>
              </div>
            </Panel>
          </div>
        )}
      </div>
    </main>
  );
}
