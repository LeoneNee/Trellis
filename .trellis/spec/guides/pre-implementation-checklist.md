# Pre-Implementation Checklist

Answer these questions **before** writing code. Most bugs come from skipping this step.

## Scope

- [ ] What is the change? (one sentence)
- [ ] Which files/packages are affected?
- [ ] Which layers does this touch? (API, service, DB, UI)

## Impact

- [ ] Run `gitnexus_impact({target: "symbol", direction: "upstream"})` — any HIGH/CRITICAL?
- [ ] Any d=1 (WILL BREAK) callers that must be updated?
- [ ] Any API contract changes? (request/response shape)

## Testing

- [ ] What test cases are needed?
- [ ] Existing tests that might break?
- [ ] Need integration test or unit test sufficient?

## Edge Cases

- [ ] What happens with empty/null input?
- [ ] What happens with concurrent access?
- [ ] Error propagation: does each layer handle errors correctly?

## Cross-Check

- [ ] If changing backend: does frontend consume this? Are params matching?
- [ ] If changing a shared type: are all consumers updated?
- [ ] If adding a new file: import paths correct? No circular deps?

---

See also: [Cross-Layer Check](check-cross-layer.md) for post-implementation verification.
