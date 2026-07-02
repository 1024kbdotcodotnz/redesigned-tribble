# Task 4 Review Fix Report

## Findings Addressed

### 1. Deterministic Unit Test (Important)
- Refactored `IssueSpotter.__init__` to accept an optional `llm_client` dependency via a new `LLMClient` protocol.
- Updated `tests/test_issue_spotter.py` to inject a `FakeLLMClient` returning controlled JSON, validating parsing and ranking without calling Ollama.
- The real `OllamaLLMClient` remains the default when no client is supplied.

### 2. Source Anchors / Supporting Facts (Important)
- `Issue.supporting_facts` was already present in the dataclass.
- Added `_extract_supporting_facts()` in `IssueSpotter` to pull concrete facts from the fact sheet (timeline events, admissions, warrant items-not-found, gaps).
- The fallback issue now uses these concrete supporting facts instead of the previous generic string.

### 3. Validate `strength` / `disposition` Values (Minor)
- Added `VALID_STRENGTHS = {"STRONG", "MODERATE", "WEAK"}` and `VALID_DISPOSITIONS = {"PRIMARY", "SECONDARY", "BACKUP"}`.
- Added `_valid_strength()` and `_valid_disposition()` helpers that normalise valid strings to uppercase and default to `MODERATE` / `SECONDARY` when invalid.

### 4. Full-Suite Warning (Minor)
- The single remaining warning is unrelated to issue-spotter:

```
.venv\Lib\site-packages\fastapi\testclient.py:1
  StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

It is a third-party dependency warning in the API test client and has not been changed by these fixes.

## Test Results

### `pytest tests/test_issue_spotter.py -v`
```
============================== test session starts ==============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\megab\aegis\.venv\Scripts\python.exe
collecting ... collected 3 items

tests/test_issue_spotter.py::test_spots_unlawful_search_from_warrantless_facts PASSED [ 33%]
tests/test_issue_spotter.py::test_fallback_populates_concrete_supporting_facts PASSED [ 66%]
tests/test_issue_spotter.py::test_invalid_strength_and_disposition_default_to_safe_values PASSED [100%]

============================== 3 passed in 0.07s ==============================
```

### `pytest tests/ -q`
```
============================== test session starts ==============================
........................................................................ [ 71%]
.............................                                            [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\megab\aegis\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture.html
101 passed, 1 warning in 6.32s
```
