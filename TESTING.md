# Testing Guide

## Quick Start

1. Activate virtual environment:
```powershell
.venv\Scripts\Activate.ps1
```

2. Install dev dependencies:
```powershell
pip install -r requirements-dev.txt
```

3. Run all tests:
```powershell
pytest -q
```

## Test Groups

- `tests/unit/`  
  Fast tests for isolated logic (utils, services, API wrappers, desktop controller, bot FSM handlers).

- `tests/integration/`  
  Tests for repository and DB migration behavior with temporary SQLite DB.

- `tests/smoke/`  
  Entry-point checks for `run_web.py` and `run_bot.py` (without starting real server/bot).

## Useful Commands

Run only unit tests:
```powershell
pytest -q tests/unit
```

Run only integration tests:
```powershell
pytest -q tests/integration
```

Run only smoke tests:
```powershell
pytest -q tests/smoke
```

Run one file:
```powershell
pytest -q tests/unit/core/services/test_salary_service_add_salary.py
```

## Notes

- Tests use temporary DB paths via `tests/conftest.py`, so they do not require manual DB cleanup.
- If imports fail (for example, `No module named core`), run tests from the project root
  (the directory that contains `version.txt` and the `core/` package).
