# KVRM-OS Architecture

## System Overview

KVRM-OS (Key-Value Response Mapping Operating System) is a semantic programming paradigm where traditional code is replaced by fine-tuned micro-LLMs that emit only symbolic keys to verified actions.

## Core Principles

### 1. Key-Only Emission
Micro-models are trained to output **only** structured JSON keys:
```json
{"action": "mkdir_secure:/path/to/dir"}
{"write": "encrypted_v1:handle_1234", "integrity_hash": "sha256:abc..."}
{"valid": true}
```

Models never generate arbitrary code or free-form text responses.

### 2. Immutable Registry
The action registry is a pre-populated, immutable mapping:
```
key → verified primitive code
```

Keys emitted by models must exist in the registry to execute.

### 3. Verified Execution
Only code in the registry can run. This guarantees:
- No hallucinated operations
- Full auditability
- Deterministic behavior

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
│                    (CLI / Gradio Web UI / API)                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ORCHESTRATOR                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Orchestrator Model                                │   │
│  │  Input: Natural language goal                                        │   │
│  │  Output: {"next": "model_name", "args": {...}}                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│                    ┌────────────────┼────────────────┐                      │
│                    ▼                ▼                ▼                      │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐            │
│  │  Creator Model   │ │  Writer Model    │ │  Verifier Model  │            │
│  │                  │ │                  │ │                  │            │
│  │  Output:         │ │  Output:         │ │  Output:         │            │
│  │  {"action":...}  │ │  {"write":...}   │ │  {"valid":...}   │            │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ACTION REGISTRY                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  SQLite Database                                                     │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  │ key                  │ action_type │ primitive_code           │  │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  │ mkdir_secure:/data   │ create      │ os.makedirs(..., 0o700)  │  │   │
│  │  │ encrypted_v1:fs_123  │ write       │ crypto.encrypt(...)      │  │   │
│  │  │ verify:fs_123        │ verify      │ hashlib.sha256(...)      │  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VERIFIED EXECUTOR                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  1. Receive key from micro-model                                     │   │
│  │  2. Look up key in registry                                          │   │
│  │  3. If not found: REJECT (cannot hallucinate)                       │   │
│  │  4. If found: Execute verified primitive                             │   │
│  │  5. Log execution result                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  SANDBOX                                                             │   │
│  │  /tmp/kvrm-os-sandbox/                                               │   │
│  │  ├── data/                                                           │   │
│  │  ├── files/                                                          │   │
│  │  └── ...                                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Goal Execution Flow
```
1. User: "Create secure notes at /data/notes"
   │
   ▼
2. Orchestrator Model:
   Input: "Create secure notes at /data/notes"
   Output: {"next": "creator", "args": {"path": "/data/notes", "mode": "secure"}}
   │
   ▼
3. Creator Model:
   Input: {"path": "/data/notes", "mode": "secure"}
   Output: {"action": "mkdir_secure:/data/notes"}
   │
   ▼
4. Registry Lookup:
   Key: "mkdir_secure:/data/notes"
   Found: Yes
   Primitive: os.makedirs("/data/notes", mode=0o700)
   │
   ▼
5. Verified Execution:
   Execute primitive in sandbox
   Log result
   │
   ▼
6. Return: {"success": true, "path": "/tmp/kvrm-os-sandbox/data/notes"}
```

## Micro-Model Specifications

### Orchestrator
- **Purpose**: Route high-level goals to specialized models
- **Input**: Natural language goal
- **Output**: `{"next": "model_name", "args": {...}}`
- **Training**: 5,000 examples of goal → routing pairs

### Creator
- **Purpose**: Handle file/directory creation
- **Input**: Path and mode arguments
- **Output**: `{"action": "operation_mode:path"}`
- **Training**: 3,000 examples of create operations

### Writer
- **Purpose**: Handle encrypted data writing
- **Input**: Handle and content
- **Output**: `{"write": "encrypted_version:handle", "integrity_hash": "..."}`
- **Training**: 3,000 examples of write operations

### Verifier
- **Purpose**: Handle integrity checking
- **Input**: Handle and expected hash
- **Output**: `{"valid": true/false, "error": "..."}`
- **Training**: 2,000 examples of verification operations

## Registry Schema

```sql
CREATE TABLE actions (
    key TEXT PRIMARY KEY,           -- Unique action identifier
    action_type TEXT NOT NULL,      -- Category: create, write, verify, etc.
    description TEXT,               -- Human-readable description
    primitive_code TEXT NOT NULL,   -- Verified code to execute
    created_at TIMESTAMP            -- Registration timestamp
);

CREATE TABLE execution_log (
    id INTEGER PRIMARY KEY,
    action_key TEXT NOT NULL,       -- Executed action
    executed_at TIMESTAMP,          -- Execution time
    success BOOLEAN,                -- Success/failure
    result TEXT,                    -- Result data
    error TEXT,                     -- Error message (if failed)
    FOREIGN KEY (action_key) REFERENCES actions(key)
);
```

## Security Model

### Guarantees
1. **No Arbitrary Code**: Models emit only keys, never code
2. **Registry Immutability**: Actions registered at setup, not runtime
3. **Sandbox Isolation**: All operations in isolated directory
4. **Full Audit Trail**: Every execution logged

### Threat Model
- **Prompt Injection**: Mitigated by key-only output format
- **Hallucinated Actions**: Blocked by registry lookup
- **Privilege Escalation**: Prevented by sandbox boundaries
- **Data Exfiltration**: Controlled by action primitives

## Extension Points

### Adding New Micro-Models
1. Define model purpose and output schema
2. Generate training data
3. Fine-tune model
4. Register action primitives
5. Update orchestrator routing

### Custom Primitives
```python
# Register new action
registry.register(
    key="backup_encrypted:/path",
    action_type="backup",
    description="Create encrypted backup",
    primitive_code="crypto.backup('/path', encryption='aes256')"
)
```

## Performance Characteristics

| Metric | Target | Notes |
|--------|--------|-------|
| Goal → Key Latency | <200ms | Per model inference |
| Registry Lookup | <1ms | SQLite indexed |
| Total Execution | <500ms | Including file ops |
| Memory per Model | ~500MB | 4-bit quantized |

## Comparison with Alternatives

| Aspect | Traditional Code | Agent Frameworks | KVRM-OS |
|--------|------------------|------------------|---------|
| Hallucination Risk | None (human-written) | High (generated) | Zero (key-based) |
| Flexibility | Low | High | Medium |
| Verifiability | Manual review | Difficult | By construction |
| Complexity | Explicit | Emergent+Chaotic | Emergent+Controlled |

## Future Directions

### Self-Registration
Allow models to propose new registry entries (with human approval).

### Meta-Orchestration
Multi-level orchestrators for complex, multi-goal workflows.

### Distributed Execution
Registry synchronization across nodes for scaled deployment.

### Formal Verification
Mathematical proofs of key-to-action mapping correctness.
