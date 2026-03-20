# Contributing to TransPlan

Thank you for your interest in TransPlan. This project is a clinical decision support tool for transplant patients, so accuracy and data quality are paramount.

## Getting Started

```bash
git clone https://github.com/rivirside/TransPlan.git
cd TransPlan
npm ci
pip install -r backend/requirements.txt

# Run tests
cd backend && python -m pytest tests/ -v
cd .. && npx jest

# Start the app
cd backend && uvicorn main:app --reload --port 8002
```

## Development Workflow

1. **Read `docs/status.md`** first — it has the current project state and file map
2. Create a feature branch from `main`
3. Make your changes
4. Run both test suites (pytest + Jest)
5. Update relevant docs if needed (`status.md`, `limitations.md`)
6. Open a pull request

## Code Style

- **Python**: Follow existing patterns. Type hints on function signatures. Docstrings on public functions.
- **JavaScript**: ES5-compatible for frontend (no modules, no `import`). Node.js scripts use CommonJS (`require`).
- **Tests**: Every new feature needs tests. Backend: pytest in `backend/tests/`. Frontend: Jest in `tests/`.

## Architecture Decisions

Non-obvious decisions are documented in `docs/adr-log.md` as Architecture Decision Records. If you're making a choice that future contributors might question, add an entry.

## Data Quality

This project deals with real clinical data. When modifying data files or fetch scripts:

- Always validate after changes: `node scripts/validate-data.js`
- Document data sources and provenance
- Never fabricate clinical data — use national averages as fallbacks when data is missing
- Add a note to `docs/limitations.md` if a data gap is discovered

## Areas for Contribution

- **L-049**: Cross-validate organ recovery rates against newer OPTN data
- **L-050**: OPO boundary mapping (high impact, requires GIS work)
- **#25**: Client SDKs (Python, TypeScript)
- **#26**: Scenario builder UI
- **Phase 6C**: Kriging uncertainty bands, spatial econometric models
- See `docs/roadmap.md` for the full list

## Reporting Issues

Use GitHub Issues. Include:
- What you expected vs what happened
- Browser/OS version for frontend issues
- Steps to reproduce
- Relevant organ/blood type/city if it's a data issue

## Contact

Questions: tomer@arizona.edu
