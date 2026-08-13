# Text-to-SQL Agent Workflow

The application keeps the existing LangGraph Text-to-SQL workflow and places the guardrail/router layer in front of it.

```mermaid
flowchart TD
    U[User] --> G[Input Gateway\nInputGuardrail]
    G -->|Injection or secret detected| B[Block request]
    G --> R[GuardrailRouter]

    R -->|Blocked or out of scope| B2[Return safe rejection]
    R -->|Ambiguous database request| C[Ask clarification]
    R -->|General conversation| N[chat_node]
    R -->|Database question| L[Existing LangGraph workflow]

    N --> O1[Sanitize answer]
    L --> S[Discover database schema]
    S --> Q[Generate SQLQuery\nPydantic JSON validation]
    Q --> V[SQL Security Gateway]
    V -->|Invalid, write, unknown table/column| E1[Safe SQL error]
    V --> A[Query risk analysis]
    A -->|High risk| H[Human approval required]
    A -->|Approved / low risk| X[Execute read-only SQL]
    X --> D[Sanitize database rows]
    D --> AN[Generate concise answer]
    AN --> O2[Sanitize answer]

    O1 --> P[Save conversation]
    O2 --> P
    C --> P
    B2 --> P
    E1 --> P
    H --> P

    P --> F[FastAPI response or SSE stream]

    G -. safe tags and metadata .-> T[LangSmith tracing]
    R -. decision tag .-> T
    V -. SQL validation / approval tag .-> T

    DB[(MySQL database)] --> S
    X --> DB
    P --> DB
```

## Request routes

| Decision | Route | Result |
|---|---|---|
| Prompt injection, credentials, secrets, dangerous request | Blocked | Safe rejection before the LLM |
| Ambiguous database request | Clarification | User is asked for more context |
| General conversation | `chat_node` | LLM answer without schema or database credentials |
| Database question | Existing LangGraph | Schema discovery, SQL generation, validation, risk analysis, execution, answer |

## Security boundaries

- `DATABASE_URL`, API keys, tokens, passwords, and environment variables are never included in LLM prompts.
- User secrets are redacted before persistence or LLM invocation.
- Generated SQL must be a single read-only query.
- Tables and columns are checked against discovered schema.
- Risky queries can require approval before execution.
- Database rows and generated answers are sanitized before returning to the user.
- LangSmith metadata contains only safe identifiers and categorical decisions, never raw secrets.

## Current storage

- MySQL stores conversations, profile data, and discovered application data.
- With MySQL, LangGraph uses the in-memory checkpoint saver because the installed PostgreSQL checkpoint saver is PostgreSQL-specific.
- PostgreSQL deployments can use the existing PostgreSQL checkpoint path.
