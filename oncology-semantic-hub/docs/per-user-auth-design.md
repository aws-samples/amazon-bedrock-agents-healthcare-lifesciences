# Design — Per-User Auth & SSO for the Oncology Semantic Hub MCP Servers

> **Status:** DESIGN (backlog #21). Goal: let an admin **grant a user SSO access** to the hub MCP
> servers (from Quick or any MCP client) with **per-user identity, audit, and governance** — replacing
> today's single shared machine credential.
> **Scope:** inbound auth to the deployed MCP runtimes (`oncology-hub-data`, `ontology-lookup-service`)
> + per-user AWS data access (Neptune/Athena). KB is a local MCP (separate, uses the user's own creds).

---

## 1. Current state (what we have today)

- **Machine-to-machine (`client_credentials`)**: a SINGLE Cognito app-client (OLS `OLSMachineClient`,
  pool `us-west-2_Jzc5lNuZ2`) with a client secret. Both runtimes use a **CUSTOM_JWT** authorizer with
  `allowedClients=[<that client id>]`.
- **No per-user identity:** every caller presents the same machine identity; the token's `client_id`
  is the only check. No per-user audit at the JWT layer.
- **Shared secret in SSM as plaintext `String`** → anyone with `ssm:GetParameter` can mint a token.
- **Single IAM execution role** runs all queries → no per-user data-access control.
- Acceptable for the demo (auth-gated, read-only, public TCGA), **not** for production/multi-tenant.

## 2. Target: SSO → per-user identity → per-user access

```
User ──SSO login (OIDC/SAML)──▶ Identity Provider ──issues per-user JWT (short-lived)──▶
   MCP client (Quick) ──Authorization: Bearer <user JWT>──▶ AgentCore Runtime (CUSTOM_JWT authorizer)
      └─ runtime reads user claims (sub/email/groups) ─▶ sts:AssumeRole (session name/tags = user)
            └─ per-invocation boto3 session ─▶ Neptune/Athena  ⇒ per-user CloudTrail + data scoping
```

Two independent layers — do them in order:

### Layer A — Authentication (who is the user): SSO via OIDC
Replace `client_credentials` with the **authorization_code** (interactive) flow so each user logs in via
SSO and receives **their own** short-lived JWT (with `sub`, `email`, `groups`/`cognito:groups`). AgentCore
inbound auth already supports this — CUSTOM_JWT validates any token from the configured issuer:
```python
authorizerConfiguration={"customJWTAuthorizer": {
    "discoveryUrl": "<IdP OIDC discovery URL>",
    "allowedClients": ["<app client id>"]}}   # or allowedAudience for audience-based IdPs
```
**IdP options (pick one):**
1. **Cognito User Pool + federated SSO** — federate the pool to the corporate IdP (SAML/OIDC) or **AWS
   IAM Identity Center**; users sign in via SSO, Cognito issues the JWT. Least new infra (reuse the pool),
   admin grants access by adding the user/group in the IdP. **Recommended default.**
2. **AWS IAM Identity Center as the OIDC provider** directly (discoveryUrl = Identity Center issuer).
3. **Third-party IdP** (Okta / Entra ID / Auth0) OIDC — discoveryUrl = the IdP; supports Dynamic Client
   Registration (Auth0) per the AWS MCP OAuth example.

> **Confirm (blocker for Quick):** does Amazon Quick's MCP client perform the **OAuth authorization_code**
> flow (browser login + token refresh) for an HTTP MCP server, or only a static Bearer header? If only
> static, SSO users would paste a short-lived token (poor UX) — then a thin **auth broker/middle tier**
> (below) that exchanges SSO → token is preferable. The AWS docs show an MCP OAuth client (`OAuthClientProvider`,
> Auth0 authorization_code) — verify Quick implements the equivalent.

### Layer B — Authorization (what the user may access): per-user AWS via STS
Today the runtime uses one execution role. For per-user governance, the MCP server extracts the caller's
identity from the inbound JWT and assumes a scoped role per request:
```
user JWT (sub/email/groups) ─▶ sts:AssumeRole(RoleArn=<scoped>, RoleSessionName=<user>,
                                              Tags=[{user},{tenant}]) ─▶ per-request boto3 session
```
- **CloudTrail/Neptune/Athena audit** then shows the actual user (via `RoleSessionName`/session tags).
- **Data scoping:** Lake Formation grants per group/tenant on Athena tables; Neptune query scoping via
  the server (or a middle tier) — e.g. restrict cohorts/tables by the user's `groups` claim.
- Note (from #21): AgentCore Gateway "Caller IAM credentials" (FAS) is Runtime/HTTP-only, **not** MCP
  targets — so per-user credentials are injected **inside the server** (assume-role per call), which is
  why our **custom-tool/server approach** (we control the boto3 session per request) fits production better
  than a drop-in MCP that uses the default boto3 chain.
- **Middle tier option:** most real deployments put an API/auth gateway in front of Neptune/Athena rather
  than letting end-user tokens reach the data plane directly; the broker does SSO exchange + assume-role +
  policy. Consider for multi-tenant.

## 3. Admin flow — "grant a user SSO access"
1. Add the user (or their group) in the IdP / IAM Identity Center and assign the hub app.
2. (Optional) map the user's group → a scoped IAM role + Lake Formation grants for their allowed data.
3. User opens Quick → connects the MCP server → completes SSO login → gets a per-user token automatically.
No shared secret handed out; access is revoked by removing the user in the IdP.

## 4. Migration from today (M2M) — incremental
1. **Harden now (cheap):** move `cognito_secret` to SSM **SecureString**; tighten `ssm:GetParameter`.
2. **Auth (Layer A):** stand up the SSO app-client (authorization_code) on the existing Cognito pool +
   federate to the IdP; add a second CUSTOM_JWT-validated path; keep M2M for CI/benchmarks.
3. **Authz (Layer B):** add assume-role-per-request in the MCP server using the JWT claims; introduce
   scoped roles + Lake Formation per group.
4. **Tenancy:** per-user/session audit + optional data scoping; consider the middle-tier broker.

## 5. Open questions
1. **Quick OAuth support** for MCP servers (authorization_code + refresh) — the gating unknown for a clean SSO UX.
2. IdP of record: reuse Cognito+federation vs IAM Identity Center vs 3rd-party.
3. Tenancy granularity: per-user vs per-group; which data is scoped (cohorts/tables) and how (Lake Formation, Neptune).
4. Where assume-role happens: in-runtime vs a middle-tier broker.

## 6. Security notes
- Prefer short-lived per-user tokens (no shared secret); rotate/revoke via the IdP.
- Least-privilege scoped roles per group; Lake Formation for table/column access.
- SecureString for any secret SSM params; audit via CloudTrail with per-user session names/tags.
- The MCP tools remain **read-only** (server guards + IAM) regardless of identity.
