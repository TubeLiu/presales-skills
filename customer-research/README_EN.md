# customer-research plugin — Multi-source Customer Research

[中文](./README.md) | **English**

Systematic multi-source research on customer questions, product topics, or account-related inquiries with source attribution and confidence scoring.

Ideal for pre-proposal customer profiling, competitive analysis, technical feasibility verification, and reviewing past communications.

## Slash Entry

| Trigger | Form |
|---|---|
| Claude Code canonical | `/customer-research:research` |
| Codex / Cursor / OpenCode short alias | `/research` |
| Natural language auto-trigger | "research customer" / "look up XX company" / "customer background check" / "industry research" / "competitive analysis" |

## Use Cases

- Quickly generate a structured customer profile from a company name
- Knowledge preparation before proposal writing (use with `/solution-master:go`)
- Competitive analysis and technical feasibility verification
- Review past communications (what did we propose to this customer before?)
- Industry trends and best practices research

## Workflow (6 Steps)

1. **Parse Request** — Identify research type (customer profile / issue investigation / account context / topic research)
2. **Search Sources** — 5-tier search (internal docs → business context → communications → web → inference)
3. **Synthesize** — Structured research brief with conclusion, findings, source attribution, confidence scoring
4. **Handle Gaps** — Web research fallback + ask user for internal context
5. **Customer-facing Notes** — Flag sensitive topics, suggest caveats, draft responses
6. **Knowledge Capture** — Suggest saving to KB / FAQ / runbook

## Output Format

```
## Research: [Topic]

### Answer
[Clear answer]

**Confidence:** High
[Rationale]

### Key Findings
**From [Source]:**
- [Finding]

### Sources
1. [Source] — [Contribution]

### Gaps & Unknowns
- [Items needing verification]

### Recommended Next Steps
- [Action items]
```

## Configuration

Auto-triggers on first run, or say "configure customer-research" manually.

| Config Key | Description | Config File |
|---|---|---|
| `customer_research.user_company` | User's own company — research is framed from this company's perspective | `~/.config/presales-skills/config.yaml` |

```bash
# View config
python3 <SKILL_DIR>/scripts/cr_config.py show

# Set manually
python3 <SKILL_DIR>/scripts/cr_config.py set user_company "XX Tech"

# Interactive setup
python3 <SKILL_DIR>/scripts/cr_config.py setup
```

## Relationship with solution-master

customer-research handles the **research preparation phase**, solution-master handles the **proposal writing phase**. Typical workflow:

```
/customer-research "XX company smart transportation needs"   → Research brief
/solution-master:go                                         → Write proposal based on research
```

## Installation

**Claude Code:**

```
/plugin marketplace add Alauda-io/presales-skills
/plugin install customer-research@presales-skills
/reload-plugins
```

**Other agents (Cursor / Codex / OpenCode, etc.):**

```bash
npx skills add Alauda-io/presales-skills -a <agent>
```
