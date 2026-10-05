# API Versioning

## Strategy

URL-based versioning with `/v1/` prefix.

```
/v1/translation
/v1/speech/translate
/v1/languages
/v1/realtime/translate
```

## Rules

1. **No breaking changes within a version**: Once `/v1/` is published, it must remain backward-compatible
2. **Additive changes are allowed**: New optional fields in requests, new fields in responses
3. **Deprecation before removal**: Features are deprecated for at least one version before removal
4. **Version in URL, not header**: Simplest approach for client consumption

## What Constitutes a Breaking Change

| Change                               | Breaking? |
| ------------------------------------ | --------- |
| Remove a response field              | ✅ Yes    |
| Change a response field type         | ✅ Yes    |
| Rename a response field              | ✅ Yes    |
| Change URL path                      | ✅ Yes    |
| Change error code semantics          | ✅ Yes    |
| Make optional request field required | ✅ Yes    |
| Add new optional request field       | ❌ No     |
| Add new response field               | ❌ No     |
| Add new endpoint                     | ❌ No     |
| Add new error code                   | ❌ No     |
| Improve translation quality          | ❌ No     |

## When to Introduce v2

- Fundamental changes to the request/response contract
- Different authentication model
- Restructured error format
- Renamed or reorganized endpoints

## Implementation

```python
# src/app/api/routes/__init__.py
from fastapi import APIRouter

v1_router = APIRouter(prefix="/v1")
# Future: v2_router = APIRouter(prefix="/v2")
```

## Client Compatibility

KMP clients will be deployed on user devices and cannot be force-updated instantly. The backend must support at minimum the current and previous API versions simultaneously during migration periods.
