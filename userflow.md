The backend user flow is:

1. User registers or logs in
`POST /api/v1/auth/register`
`POST /api/v1/auth/login`

2. User creates an organization/team if needed
`POST /api/v1/organizations/`
`POST /api/v1/organizations/{id}/teams`

3. User creates a target
`POST /api/v1/targets/`

4. User verifies target ownership
`POST /api/v1/targets/{id}/proofs/challenge`
Then verify with:
`POST /api/v1/targets/{id}/authorize`

Supported proof types:
`dns_txt`, `http_file`, `meta_tag`, `github_file`

Manual attestation only marks target as `attested`, not fully `verified`.

5. User optionally creates scan profile/config
`POST /api/v1/platform/scan-profiles`

6. User starts a scan
`POST /api/v1/scans/`

Backend policy checks:
- target belongs to user/org
- user has permission
- target is `verified`
- scan is inside allowed scope

7. Worker/agent runs scan
It performs:
- planning
- recon
- browser workflow discovery
- API discovery
- repo/dependency/IaC discovery
- scanner engine execution
- evidence normalization
- finding correlation
- retest plan
- report generation

8. User watches scan progress
`GET /api/v1/scans/`
`GET /api/v1/scans/{id}`
WebSocket:
`/api/v1/ws/scans/{id}/stream?token=...`

9. User reviews findings
`GET /api/v1/findings/`
`GET /api/v1/findings/{id}`

Then user can:
- change status
- add evidence
- add comments
- suppress finding
- view remediation history

10. User exports reports
`GET /api/v1/reports/{scan_id}/json`
`GET /api/v1/reports/{scan_id}/markdown`
`GET /api/v1/reports/{scan_id}/pdf`
`GET /api/v1/reports/{scan_id}/sarif`

11. User can retry/retest scan
`POST /api/v1/scans/{id}/retry`
`POST /api/v1/scans/{id}/duplicate`
`POST /api/v1/scans/{id}/pause`
`POST /api/v1/scans/{id}/resume`
`POST /api/v1/scans/{id}/cancel`

So simple flow is:

`Login -> Create org -> Create target -> Verify target -> Configure scan -> Run scan -> Watch progress -> Review findings -> Triage/remediate -> Export report -> Retest`