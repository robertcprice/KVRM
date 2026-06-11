# KVRM Registry Schema

A registry is a finite audited action space.

## Top-level fields
```json
{
  "registry_name": "toy-risk-router",
  "version": "1.0.0",
  "actions": []
}
```

## Action schema
```json
{
  "action_id": "request_human_review",
  "name": "Request Human Review",
  "description": "Escalate the case to a human operator.",
  "parameters_schema": {
    "type": "object",
    "properties": {
      "reason": {"type": "string"}
    },
    "required": ["reason"]
  },
  "tags": ["fallback", "safe"]
}
```

## Rules
- `action_id` must be unique and stable.
- `version` is a human-readable registry version.
- digest is computed from canonical serialized content, not stored as source truth.
- append-only changes are compatible if all old action IDs preserve semantics.
- reorder-only changes are compatible but should be detectable.
- incompatible changes include removed actions, reused IDs with changed semantics, or incompatible parameter schemas.
