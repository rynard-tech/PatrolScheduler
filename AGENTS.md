# Codex Instructions

Read `PROJECT_SPEC.md` before making architectural or scheduling decisions.

## Mission
Build a constraint-based ski patrol schedule template generator. Workday remains the system of record. This application determines what schedule should be entered into Workday, allows management to review/edit/lock/re-solve it, and exports a clean template.

## Implementation priorities
1. Correct data model and import layer.
2. OR-Tools CP-SAT scheduling engine with hard constraints separated from soft objectives.
3. Validation and infeasibility reporting.
4. Manual locks, overrides, and re-solving.
5. Basic admin UI.
6. Excel/CSV exports.

## Non-negotiable engineering rules
- Do not hard-code employee names, yearly dates, roster size, wave sizes, station staffing numbers, or preference weights in solver logic.
- Do not put scheduling rules in React components.
- Do not silently violate hard constraints. Return an explicit infeasibility/conflict report.
- Do not silently convert free-text employee notes into hard constraints.
- Do not silently fuzzy-merge employee identities during imports.
- Do not treat First Tracks or Night Ski as duty stations. They are shift types.
- Do not treat supervisor families as crews that must remain together.
- Preserve season-to-date history for duty-station fairness and relationship exposure.
- Keep the app runnable after each phase and add tests with each solver rule.

## Preferred stack
- Frontend: Next.js / React
- Backend: Python / FastAPI
- Database: SQLite for MVP, with a clean path to PostgreSQL
- Optimizer: Google OR-Tools CP-SAT
- Spreadsheet import/export: openpyxl and/or pandas

## First task
Do not start with a polished frontend. First implement the normalized models, import/mapping interfaces, synthetic fixture data, constraint engine, validation, and a CLI or structured JSON demonstration that produces one complete valid week.
