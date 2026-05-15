# AgentCore Migration — Process, Metrics & Reproducible Pattern

## Executive Summary

**20 agents migrated to AgentCore** across two phases using Kiro CLI, totaling ~2.5 hours of wall-clock time. Phase 1 migrated 4 agents individually (~29 min/agent). Phase 2 mass-migrated 16 agents in parallel (42 min total). All agents include automated tests, deploy scripts, and pass security scans with 0 high/critical findings.

## Key Metrics

| Metric | Value |
|--------|-------|
| Agents migrated | 20 (Phase 1: 4, Phase 2: 16) |
| Total wall-clock time | ~2.5 hrs |
| Automated tests | 230+ |
| Security findings (High/Critical) | 0 |
| Security fixes applied | 48 medium-severity issues remediated |
| Deploy script | Added to all 20 agents |
| Old v1 code removed | CFN templates + Lambda action-groups |
| PRs consolidated | 4 individual → 1 combined (#275) |
| Models validated | 2 (Claude Sonnet 4.5, Claude Haiku 4.5) |
| UI verification | Streamlit (auto-discovers all agents) |

## Prework: Analysis & Planning

Before any code was written, Kiro CLI was used to analyze the repo and create a structured plan:

### Step 1: Repository Analysis
- Analyzed all 38 agents to understand current patterns (CFN/Lambda vs Strands vs notebook-only)
- Identified which agents were candidates for migration vs deprecation
- Mapped dependencies, data files, and tool complexity per agent

### Step 2: Epic Creation (GitHub Issue #248)
- Created a phased epic with all agents categorized by effort level:
  - Phase 1 (Low effort): 4 agents already on Strands, just needed AgentCore runtime
  - Phase 2 (High effort): 16 agents requiring full rewrite from CFN/Lambda
  - Phase 3 (Triage): 9 notebook/legacy agents to evaluate
- Defined acceptance criteria for each migration

### Step 3: Individual Issues
- Created 20 individual GitHub issues (#250-#269), one per agent
- Each issue linked to the epic with specific scope and context
- Enabled tracking progress and parallelizing work

### Step 4: Template Selection
- Evaluated `agentcore_template/` and Agent 28 as reference patterns
- Chose the standardized structure before starting any migration

**Total planning time:** ~30 min (Kiro analyzed the repo, created epic + issues, identified phases)

## Phase 2 Mass Migration

| Metric | Value |
|--------|-------|
| Agents migrated | 16 |
| Code generation | 23 min (parallel Kiro subagents) |
| Deployment | 19 min (batch script) |
| Total | 42 minutes |
| Unit tests | 170+ |

## Phase 1 Per-Agent Breakdown

| Agent | Time | Tools | Unit Tests | Integration | System (E2E) | Total |
|-------|------|-------|-----------|-------------|--------------|-------|
| 29 - Clinical Prior Auth | ~45 min* | 5 | 10 | 3 | 3 | 16 |
| 27 - Enrollment Pulse | ~30 min | 40+ | 12 | 1 | 3 | 16 |
| 30 - Clinical PreVisit | ~25 min | 12 | 10 | 2 | 3 | 15 |
| 26 - Medical Device | ~15 min | 4 | 11 | 2 | 3 | 16 |

*Agent 29 took longest as the first migration — established the pattern, discovered container packaging issues, and identified EOL models.

## Requirements Provided to Kiro

### Input
1. **GitHub Issue #248** — Epic describing the migration scope and phases
2. **Template reference** — `agentcore_template/` (Template 1) and Agent 28 as canonical pattern
3. **Acceptance criteria**:
   - Agent runs on AgentCore runtime with Strands SDK
   - Passes linting: ruff, bandit (security)
   - Deployed and tested in AWS account with live invocations
   - README updated with deployment instructions
   - All tests automated (no manual steps)
   - System tests based on scenarios from agent documentation

### No custom steering files or MCP servers were needed
Kiro used its built-in AWS MCP servers (documentation, CloudWatch, ECS) plus standard tools (file read/write, shell, grep, AWS CLI, GitHub CLI).

## Standardized Template Pattern

Based on `agentcore_template/` (Template 1) — reference: Agent 28.

```
agentcore/
├── main.py                          # BedrockAgentCoreApp entrypoint
├── agent/
│   ├── agent_config/
│   │   ├── agent.py                 # Agent task, model config, system prompt, tools
│   │   └── tools/                   # @tool decorated functions (if separate)
│   ├── data/ or resources/          # Data files (CSVs, JSON configs)
│   └── analysis/                    # Analysis modules (if needed)
├── tests/
│   ├── test_agent.py               # Unit + integration tests
│   └── test_system.py              # End-to-end system tests
├── pyproject.toml
└── pytest.ini
```

## Test Framework (Common Across All Agents)

### Three automated test levels

```bash
# Unit tests — no AWS needed, tests data loading, tool outputs, model config
pytest tests/ -m "not integration and not system"

# Integration tests — validates live Bedrock model access
AWS_PROFILE=your-profile pytest tests/ -m integration

# System tests — end-to-end against deployed AgentCore agent
AWS_PROFILE=your-profile pytest tests/ -m system

# Everything
AWS_PROFILE=your-profile pytest tests/ -v
```

### System test pattern (reusable for any agent)

```python
@pytest.mark.system
def test_scenario_from_docs():
    """Scenario described in agent README/docs."""
    response = _invoke_agent("user query from documentation")
    assert any(expected_term in response for expected_term in ["term1", "term2"])
```

System tests invoke the deployed agent via `invoke_agent_runtime` API and assert responses contain expected content using flexible matching (accounts for LLM non-determinism).

### Linting & Security (every agent)

| Tool | Purpose | Command |
|------|---------|---------|
| ruff | Python linting | `ruff check .` |
| bandit | Security scanning | `bandit -r agent/` |

### UI Verification

The `agentcore_template/app.py` Streamlit app auto-discovers all deployed AgentCore agents in the account. Manual smoke test confirms each agent responds correctly through the chat interface.

## Reproducible Process (for other team members)

### Step 1: Read existing agent code
- Understand tools, data dependencies, model usage

### Step 2: Create branch + agentcore/ directory
- Follow the template structure above

### Step 3: Port code
- Copy tools/data into `agent/agent_config/`
- Replace `sys.path` hacks with absolute imports
- Update model IDs to current versions
- Co-locate data files with modules (for container packaging)

### Step 4: Write tests
- Unit: test data loading, tool outputs, model config
- Integration: test model responds
- System: test scenarios from agent docs against deployed agent

### Step 5: Lint
- `ruff check --fix .`
- `bandit -r agent/`

### Step 6: Deploy + verify
```bash
aws ecr create-repository --repository-name <agent_name> --region us-east-1
agentcore configure --entrypoint main.py --name <agent_name> \
  --ecr <ACCOUNT>.dkr.ecr.us-east-1.amazonaws.com/<agent_name> \
  --execution-role <ROLE_ARN> --disable-memory --disable-otel
agentcore deploy
agentcore invoke '{"prompt": "test query"}'
```

### Step 7: UI smoke test
```bash
cd agentcore_template
streamlit run app.py  # Select agent from dropdown, send test message
```

## Key Findings

1. **Amazon Titan Text Express is EOL** — replaced with Claude Haiku 4.5
2. **Container data packaging** — data files must be co-located with Python modules for AgentCore container builds
3. **ECR configuration** — must use full URI in `agentcore configure`
4. **Model compatibility** — Claude Sonnet 4.5 does not allow `temperature` + `top_p` simultaneously
5. **Import patterns** — replace `sys.path.append` hacks with absolute imports
6. **Auth mismatch** — agents deployed with IAM auth work with Streamlit; FAST frontend requires OAuth (separate config)

## Tools Used

| Tool | Purpose |
|------|---------|
| Kiro CLI | AI development agent (code generation, testing, deployment) |
| agentcore CLI | Agent configuration and deployment |
| AWS CLI | ECR, IAM, Bedrock operations |
| GitHub CLI (gh) | PR creation, issue management |
| pytest | Automated test execution |
| ruff | Python linting |
| bandit | Security scanning |
| cfn-lint | CloudFormation template validation |
| Streamlit | UI verification |

## Kiro CLI Setup & Workflow

### MCP Servers (built-in, no custom config needed)

| MCP Server | What it provided |
|------------|-----------------|
| `awslabs.aws-documentation-mcp-server` | AWS docs lookup (AgentCore, Strands, Bedrock APIs) |
| `awslabs.cloudwatch-mcp-server` | Log analysis, metric queries for deployed agents |
| `awslabs.ecs-mcp-server` | Container troubleshooting |
| `aws-knowledge-mcp-server` | Regional availability, service features |

### Tools Used by Kiro During Migration

| Tool | Usage |
|------|-------|
| File read/write | Read existing agent code, write new agentcore/ files |
| Shell | Run agentcore CLI, pytest, ruff, bandit, git, gh |
| Grep/Glob | Search patterns across agents, find files |
| AWS CLI (`use_aws`) | ECR operations, IAM role checks, Bedrock invocations |
| Code intelligence | Symbol search, AST parsing for understanding agent structure |
| Subagents | Parallel code generation for Phase 2 mass migration |

### Workflow: How Context Was Maintained Across Sessions

1. **Chat history persistence** — Kiro CLI maintains conversation context between sessions. Each agent migration built on learnings from the previous one.
2. **Task lists** — Active task tracking carried across sessions (what's done, what's next, key decisions made).
3. **Template-first approach** — Phase 1 established the pattern in context. Phase 2 referenced it without re-explaining.
4. **Knowledge base** — Key findings (EOL models, container packaging issues, import patterns) accumulated in context and informed later agents.

### Subagent Pattern (Phase 2)

For the mass migration, Kiro spawned parallel subagents — each responsible for one agent's migration:

```
Main agent (orchestrator):
  ├── Subagent 1: Migrate agent 10 (SEC 10-K)
  ├── Subagent 2: Migrate agent 11 (Tavily)
  ├── Subagent 3: Migrate agent 12 (JSL Reports)
  ├── ...
  └── Subagent 16: Migrate competitive_intelligence
```

Each subagent received:
- The template pattern (from Phase 1)
- The specific agent's existing code to port
- Acceptance criteria (tests, linting, structure)

All 16 ran concurrently → 23 min for code generation (vs ~8 hrs sequential).

### Key Workflow Decisions

| Decision | Rationale |
|----------|-----------|
| No custom steering files | Built-in MCP servers + template reference was sufficient |
| Phase 1 before Phase 2 | Needed to validate pattern and discover edge cases first |
| Chat history over docs | Faster iteration — context stayed in conversation, documented after |
| Subagents for parallelism | Each migration is independent — perfect for parallel execution |
| Single PR consolidation | 4 individual PRs merged into 1 for cleaner review |

## Post-Migration Hardening

| Task | Time | Details |
|------|------|---------|
| Security remediation | ~20 min | Fixed 48 medium-severity issues (B113: request timeouts, B314: unsafe XML, B615: HuggingFace pinning, B608: SQL injection) |
| PCSR scan + packaging | ~10 min | Bandit + cfn-lint + ruff, results zipped for security review |
| Deploy script | ~15 min | Created `deploy.py` using `agentcore CLI (@aws/agentcore)`, added to all 20 agents |
| Old v1 code removal | ~10 min | Removed CFN templates, Lambda action-groups, old deploy.sh from all migrated agents |
| README updates | ~5 min | Added deploy instructions to agentcore/ READMEs, deprecation notice on old READMEs |
| PR reviews (276, 279) | ~10 min | Reviewed positioning docs and framework scaffold |
| **Total** | **~65 min** | |

## Security Scan Results (Post-Remediation)

| Tool | High/Critical | Medium | Notes |
|------|--------------|--------|-------|
| Bandit | 0 | 86 | Remaining: /tmp in Lambda (28), pickle for ML (23), urllib to known APIs (22), validated SQL (7), bind 0.0.0.0 in containers (6) |
| Ruff (S-rules) | 0 | 0 | All deploy scripts pass; other findings are S101 (assert in tests) |
| cfn-lint | 0 new | 67 pre-existing | E3006: cfn-lint doesn't recognize AWS::BedrockAgentCore::* types yet |
