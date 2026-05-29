"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useAuth } from "../lib/auth-context";
import { apiRequest, Membership, Organization, shortId, Team } from "../lib/api";
import { EmptyState, GreenButton, GhostButton, LoadingState, Panel } from "../components/ui";

const orgEmpty = { name: "", slug: "" };
const memberEmpty = { user_email: "", role: "viewer" };
const teamEmpty = { name: "", slug: "" };

export default function OrganizationsPage() {
  const { token, isLoaded } = useAuth();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [members, setMembers] = useState<Membership[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [orgForm, setOrgForm] = useState(orgEmpty);
  const [memberForm, setMemberForm] = useState(memberEmpty);
  const [teamForm, setTeamForm] = useState(teamEmpty);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const load = useCallback(async (preferredId = selectedId) => {
    if (!token) { setIsLoading(false); return; }
    setLoading(true);
    setError("");
    try {
      const orgs = await apiRequest<Organization[]>(token, "/organizations/");
      const nextId = preferredId || orgs[0]?.id || "";
      setOrganizations(orgs);
      setSelectedId(nextId);
      if (nextId) {
        const [m, t] = await Promise.all([
          apiRequest<Membership[]>(token, `/organizations/${nextId}/members`),
          apiRequest<Team[]>(token, `/organizations/${nextId}/teams`),
        ]);
        setMembers(m);
        setTeams(t);
      } else {
        setMembers([]);
        setTeams([]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load organizations");
    } finally {
      setLoading(false); setIsLoading(false);
    }
  }, [selectedId, token]);

  useEffect(() => { if (!isLoaded) return; load().catch(e => setError(e.message)); }, [load, isLoaded]);

  async function createOrganization(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy("organization"); setError(""); setMessage("");
    try {
      const org = await apiRequest<Organization>(token, "/organizations/", {
        method: "POST",
        body: JSON.stringify({ name: orgForm.name.trim(), slug: orgForm.slug.trim() || undefined }),
      });
      setOrgForm(orgEmpty);
      await load(org.id);
      setMessage("Organization created.");
    } catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
    finally { setBusy(""); }
  }

  async function deleteOrganization(id: string) {
    if (!token || !confirm("Delete this organization?")) return;
    setBusy(`delete-${id}`); setError(""); setMessage("");
    try {
      await apiRequest<void>(token, `/organizations/${id}`, { method: "DELETE" });
      await load("");
      setMessage("Organization deleted.");
    } catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
    finally { setBusy(""); }
  }

  async function addMember(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedId) return;
    setBusy("member"); setError(""); setMessage("");
    try {
      await apiRequest<Membership>(token, `/organizations/${selectedId}/members`, {
        method: "POST",
        body: JSON.stringify(memberForm),
      });
      setMemberForm(memberEmpty);
      await load(selectedId);
      setMessage("Member added or updated.");
    } catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
    finally { setBusy(""); }
  }

  async function createTeam(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedId) return;
    setBusy("team"); setError(""); setMessage("");
    try {
      await apiRequest<Team>(token, `/organizations/${selectedId}/teams`, {
        method: "POST",
        body: JSON.stringify({ name: teamForm.name.trim(), slug: teamForm.slug.trim() || undefined }),
      });
      setTeamForm(teamEmpty);
      await load(selectedId);
      setMessage("Team created.");
    } catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
    finally { setBusy(""); }
  }

  if (isLoading) return <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6"><div className="mx-auto max-w-[1400px] space-y-5"><div className="h-[120px] rounded-2xl bg-[#080f18] animate-pulse"></div><div className="h-[400px] rounded-2xl bg-[#080f18] animate-pulse"></div></div></main>;

  return (
    <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-[1400px] space-y-5">
        <header className="rounded-2xl border border-white/7 bg-[#080f18] p-6">
          <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-[#a8ff3e]/60">Admin Panel</p>
          <h1 className="mt-2 font-mono text-3xl font-bold text-white">Organizations</h1>
          <p className="mt-2 font-mono text-xs text-white/35">Manage organizations, members, and teams from the backend organization API.</p>
          {(message || error) && (
            <div className="mt-4 space-y-2">
              {message && <p className="rounded-xl border border-[#a8ff3e]/15 bg-[#a8ff3e]/6 px-4 py-2 font-mono text-xs text-[#a8ff3e]/80">{message}</p>}
              {error && <p className="rounded-xl border border-[#ff7c70]/20 bg-[#ff7c70]/6 px-4 py-2 font-mono text-xs text-[#ffb3ad]">{error}</p>}
            </div>
          )}
        </header>

        <div className="grid gap-5 lg:grid-cols-[380px_1fr]">
          <form onSubmit={createOrganization} className="h-fit rounded-2xl border border-white/7 bg-[#080f18] p-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/60">POST /organizations</p>
            <h2 className="mt-2 font-mono text-lg font-semibold text-white">Create organization</h2>
            <div className="mt-5 space-y-3">
              <input className="field" placeholder="Organization name" value={orgForm.name} onChange={e => setOrgForm({ ...orgForm, name: e.target.value })} />
              <input className="field" placeholder="Slug optional" value={orgForm.slug} onChange={e => setOrgForm({ ...orgForm, slug: e.target.value })} />
              <GreenButton type="submit" disabled={busy === "organization" || !orgForm.name} className="w-full justify-center">
                {busy === "organization" ? "Creating..." : "Create organization"}
              </GreenButton>
            </div>
          </form>

          <Panel title="Your organizations" eyebrow={`GET /organizations - ${organizations.length} total`}>
            {loading ? <LoadingState text="Loading organizations..." /> : organizations.length === 0 ? (
              <EmptyState text="No organizations yet. Create one to begin." />
            ) : (
              <div className="space-y-3">
                {organizations.map(org => (
                  <div key={org.id} onClick={() => load(org.id)} className={`cursor-pointer rounded-xl border p-4 transition ${selectedId === org.id ? "border-[#a8ff3e]/30 bg-[#a8ff3e]/6" : "border-white/7 bg-[#05090f] hover:bg-[#0b1520]"}`}>
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="font-mono text-sm font-semibold text-white">{org.name}</p>
                        <p className="mt-1 font-mono text-xs text-white/40">{org.slug}</p>
                        <p className="mt-2 font-mono text-[10px] text-white/20">{shortId(org.id)}</p>
                      </div>
                      <GhostButton disabled={busy === `delete-${org.id}`} onClick={() => deleteOrganization(org.id)}>
                        {busy === `delete-${org.id}` ? "Deleting..." : "Delete"}
                      </GhostButton>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>

        {selectedId && (
          <div className="grid gap-5 lg:grid-cols-2">
            <Panel title="Members" eyebrow="GET/POST /organizations/{id}/members">
              <form onSubmit={addMember} className="mb-4 grid gap-2 sm:grid-cols-[1fr_150px_auto]">
                <input className="field" placeholder="user@example.com" value={memberForm.user_email} onChange={e => setMemberForm({ ...memberForm, user_email: e.target.value })} />
                <select className="field" value={memberForm.role} onChange={e => setMemberForm({ ...memberForm, role: e.target.value })}>
                  <option value="viewer">viewer</option><option value="analyst">analyst</option><option value="admin">admin</option><option value="owner">owner</option>
                </select>
                <GreenButton type="submit" disabled={busy === "member" || !memberForm.user_email}>{busy === "member" ? "Saving..." : "Add"}</GreenButton>
              </form>
              {members.length === 0 ? <EmptyState text="No members returned for this organization." /> : (
                <div className="space-y-2">{members.map(member => (
                  <div key={member.id} className="rounded-xl border border-white/7 bg-[#05090f] p-3">
                    <p className="font-mono text-xs text-white">{shortId(member.user_id)} - {member.role}</p>
                    <p className="font-mono text-[10px] text-white/30">{new Date(member.created_at).toLocaleString()}</p>
                  </div>
                ))}</div>
              )}
            </Panel>

            <Panel title="Teams" eyebrow="GET/POST /organizations/{id}/teams">
              <form onSubmit={createTeam} className="mb-4 grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
                <input className="field" placeholder="Team name" value={teamForm.name} onChange={e => setTeamForm({ ...teamForm, name: e.target.value })} />
                <input className="field" placeholder="Slug optional" value={teamForm.slug} onChange={e => setTeamForm({ ...teamForm, slug: e.target.value })} />
                <GreenButton type="submit" disabled={busy === "team" || !teamForm.name}>{busy === "team" ? "Creating..." : "Create"}</GreenButton>
              </form>
              {teams.length === 0 ? <EmptyState text="No teams yet." /> : (
                <div className="space-y-2">{teams.map(team => (
                  <div key={team.id} className="rounded-xl border border-white/7 bg-[#05090f] p-3">
                    <p className="font-mono text-xs text-white">{team.name}</p>
                    <p className="font-mono text-[10px] text-white/30">{team.slug} - {shortId(team.id)}</p>
                  </div>
                ))}</div>
              )}
            </Panel>
          </div>
        )}
      </div>
    </main>
  );
}
