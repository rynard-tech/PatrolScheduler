# PatrolScheduler Project Specification

## 1. Purpose
Build an internal ski patrol scheduling and deployment template generator.

This is **not** a replacement for Workday. Workday remains the official scheduler/system of record. This application determines what schedule should be entered into Workday, creates reusable templates, supports weekly exceptions, allows management to review/edit/lock/re-solve assignments, and exports clean schedules.

Primary scale is roughly 100 patrollers, commonly around 75 full-time and 25 part-time, but all counts must be configurable.

The patrol operates 7 days per week.

The system must determine:
- starting/staffing wave for each employee
- normal workdays for each FT employee
- PT assignments from submitted availability
- 10-hour shift type for each working employee
- daily duty station
- operational/special role
- supervisory coverage
- fair/diverse duty-station use
- supervisor-family exposure
- manager-supervisor exposure
- staffing and budget feasibility
- conflict/infeasibility explanations

## 2. Architecture
Preferred stack:
- Frontend: Next.js / React
- Backend: Python / FastAPI
- Database: SQLite MVP, designed to move to PostgreSQL
- Optimization: Google OR-Tools CP-SAT
- Excel: openpyxl and/or pandas

Keep solver logic isolated from UI.

Suggested structure:

```text
/frontend
/backend
  /api
  /models
  /scheduler
    wave_solver.py
    work_pattern_solver.py
    deployment_solver.py
    constraints.py
    objectives.py
    validation.py
    explanations.py
    conflict_analysis.py
  /imports
    requests_importer.py
    starting_waves_importer.py
    families_importer.py
    southside_importer.py
    part_time_importer.py
  /exports
    workday_export.py
    deployment_export.py
    analytics_export.py
```

Do not hard-code employee names, annual dates, roster size, staffing-wave counts, duty-station staffing counts, shift times, or solver weights.

## 3. Hard constraints vs soft objectives
The system must explicitly separate:

### Hard constraints
Cannot be violated automatically. If impossible, return an infeasibility/conflict report.

### Soft objectives
Used to rank valid schedules.

Use lexicographic/multi-stage optimization where practical. Do not let a large pile of minor preferences outweigh an operational requirement.

Manual admin overrides may intentionally break selected hard rules, but every override must be explicit and recorded.

## 4. Employee model
Support at minimum:
- Full-Time Patroller
- Part-Time Patroller
- Supervisor
- Manager

Roles/qualifications should be independent flags, not mutually exclusive types.

Employee fields should include:

### Identity
- id
- employee_number if available
- first_name
- last_name
- display_name
- active

### Employment
- employment_type: FULL_TIME / PART_TIME / MANAGER
- supervisor_flag
- manager_flag

### Seniority
- prior_winter_hours
- calculated_seniority_rank
- optional manual seniority override

Higher worked winter hours = higher scheduling seniority.

### Season status
- active_start_date
- active_end_date
- awarded_start_wave
- start_wave_preferences

### Work schedule preferences
- ranked schedule preferences
- split schedule details
- awarded work pattern
- unavailable weekdays
- date-specific unavailability
- free-text notes

### Night Ski
- eligible boolean
- ranked preferred weekdays
- restrictions

### First Tracks
- eligible boolean
- restrictions

### Qualifications
Flexible qualification system including at least:
- supervisor
- team_lead
- avalanche_route_leader
- prospective_route_leader
- snow_safety / blaster
- forecaster
- weather
- snowmobile_driver
- truck_driver
- skier
- snowboarder
- future custom qualifications

### Development / organization
- rookie_status: ROOKIE / GRADUATED
- graduation_date
- family_id
- family_supervisor_id

### Station restrictions
- required_station
- prohibited_stations
- allowed_stations
- notes

## 5. Full-time rules
For normal FT patrollers and supervisors:
- exactly 4 shifts per standard week
- exactly 10 paid hours per shift
- exactly 40 paid hours per week
- no overtime
- never automatically schedule a fifth shift to solve a shortage

Managers are a specific exception and are handled separately.

PTO/training/leave can be represented explicitly rather than pretending it is a worked shift.

If staffing requires overtime, return a shortage rather than scheduling it.

## 6. Manager rules
There are currently 2 managers above the supervisors.

Each manager:
- works 5 days/week
- always works Dercum
- collectively the two manager schedules should cover both sides of the week
- needs direct exposure to a diverse set of supervisors who are working Dercum

Managers are exempt from the normal 4-day pattern and station-diversity rules.

Do not apply normal FT 40-hour logic to managers unless specifically configured.

## 7. Normal work-pattern options
Support contiguous patterns:
- Sun-Wed
- Mon-Thu
- Tue-Fri
- Wed-Sat
- Thu-Sun
- Fri-Mon
- Sat-Tue

Also support explicit split schedules as individual weekdays.

Do not force a split schedule into a contiguous pattern.

Preserve employee ranking of available patterns.

## 8. Preference import
Import the employee request workbook containing things such as:
- employee name
- ranked starting-wave preferences
- ranked work-pattern preferences
- split schedule descriptions
- ranked Night Ski weekdays
- free-text restrictions/notes

Provide import preview before commit.

Structured selections become structured data.

Free-text notes remain notes until an admin classifies them as:
- HARD UNAVAILABLE
- SOFT PREFERENCE
- INFORMATION ONLY

Do not automatically turn every free-text statement into a hard constraint.

## 9. Seniority and preference awarding
Schedule preference is awarded in seniority fashion using worked winter hours.

Do not use a simple greedy seniority loop. Solve globally so senior employees receive stronger preference weighting while keeping the whole schedule feasible and balanced.

Store/display:
- requested choice #1/#2/#3 etc.
- awarded choice
- seniority rank
- reason if top choice was not awarded when explainable

Operational feasibility always beats preference.

## 10. Starting waves
Staffing ramps up through the season based on budget.

Use the uploaded 2025-26 Starting Waves workbook as a model, but do not hard-code that year's values.

The example includes date-effective targets approximately:
- 17.1 people/day around Oct 20
- 22.7 people/day around Nov 10
- 34.3 people/day around Nov 22
- 48 people/day around Dec 19

For regular FT staffing planning, calculate approximate active FT required as:

```text
approx_active_ft = target_people_per_day * 7 / 4
```

Each StaffingWave should support:
- id/name
- effective_date
- end_date if applicable
- target_people_per_day
- target_paid_hours_per_day if used
- approximate_required_active_ft
- max_budgeted_hours
- number/specific employees added
- rookies
- trainer requirements if used
- minimum qualification counts
- notes

Employee wave preferences are ranked and should be awarded using:
- budget/staffing needs
- seniority-weighted preference
- needed qualifications
- supervisor requirements
- rookie/trainer needs
- weekday staffing balance

Do not simply pick the top N employees by seniority. The active roster must be operationally usable.

The solver should jointly consider who starts and what 4-day patterns they work so staffing is balanced across all 7 days.

## 11. Date-effective operating periods
Create OperatingPeriod / RequirementSet with:
- name
- start_date
- end_date
- enabled duty stations
- staffing requirements by station
- Night Ski active/not active
- First Tracks active/not active
- special roles
- budget

This allows early-season operations to differ from full operations.

If budget and enabled operating requirements conflict, report infeasibility rather than guessing which rule to relax.

## 12. Duty stations
Canonical duty stations:
- DERCUM
- NORTH_PEAK
- OUTBACK
- BERGMAN

Southside/non-Dercum stations for fairness tracking:
- NORTH_PEAK
- OUTBACK
- BERGMAN

Dercum is not included in Southside totals.

Display names should be configurable independently from internal IDs.

## 13. Full-operations station template
Initialize a configurable full-operations template using these rules:

### Bergman
- target/minimum 7 patrollers
- 1 supervisor
- 2 avalanche route leaders
- 2 prospective route leaders
- at least 4 skiers when possible / according to configured rule strength

### Outback
Same general staffing model as Bergman:
- target/minimum 7
- 1 supervisor
- 2 avalanche route leaders
- 2 prospective route leaders
- skier requirement configurable

### North Peak
- target/minimum 7
- includes Team Lead
- supervision requirements configurable

### Dercum
- receives remaining daily staff after required staffing elsewhere
- contains Dercum-specific special roles
- managers on duty are always here
- daily MGMT supervisor remains here when applicable

All counts and rule strengths must be editable.

## 14. Special roles
Create configurable SpecialRoleRequirement records.

Current examples:

### Weather
- one each required day
- historical example shift 5:30 AM-3:30 PM
- backfill required when primary unavailable

### Snow Safety / Blaster
- qualification required
- may be tied to Bergman
- may be required only on configured dates/weekdays

### Forecaster
- qualification required
- historical example 6:00 AM-4:00 PM
- stays Dercum

### MGMT Supervisor
- designated supervisor
- stays Dercum

### Snowmobile / Truck Driver
- qualification required
- often Dercum-related

SpecialRoleRequirement fields:
- role
- date/date range
- weekdays
- required_count
- required_station
- required_shift_type
- eligibility qualification
- preferred employees
- backups
- HARD/SOFT
- notes

## 15. Shift definitions
Shift type and duty station are separate.

Create ShiftType including:
- STANDARD
- FIRST_TRACKS
- NIGHT_SKI
- WEATHER
- FORECASTER
- CUSTOM

Each shift type:
- name
- start_time
- end_time
- paid_hours
- active date range
- eligible roles if applicable

Historical standard default may initialize to 7:15 AM-5:15 PM, but all times must be configurable.

Regular FT worked shifts remain 10 paid hours.

## 16. First Tracks
When active:
- exactly 6 people by default, configurable
- 10-hour shifts
- start early and leave early
- exactly 1 qualified supervisor

First Tracks is a shift, not a duty station.

Every First Tracks employee still receives a duty station and role.

First Tracks supervisor and Night Ski supervisor must be different people on the same date.

## 17. Night Ski
When active:
- exactly 10 people by default, configurable
- 10-hour shifts
- late start / late finish
- exactly 1 qualified supervisor

Night Ski is a shift, not a duty station.

Night Ski supervisor must differ from First Tracks supervisor on that date.

Night Ski scheduling considers:
- eligibility
- whether employee works that weekday
- restrictions
- ranked weekday preference
- seniority
- operational staffing
- no overtime
- optional fairness of Night Ski assignment counts

Never assume blank preference means eligible. Store explicit `night_ski_eligible`.

## 18. Daily assignment model
Every employee/date should resolve to one primary DailyAssignment:
- employee_id
- date
- working
- shift_type_id
- start_time
- end_time
- paid_hours
- duty_station_id
- primary_role
- special_role
- family_supervisor_id context
- manager_on_duty context if needed
- locked
- manual_override
- override_reason
- generated_by_solver
- notes

Do not maintain disconnected schedules for shift, station, family, etc.

## 19. Rookie rules
While `rookie_status = ROOKIE`:
- Dercum only
- D/D/D/D is valid
- rookie is exempt from normal station-diversity max-2 rule

When employee graduates, normal diversity rules begin automatically.

Track the graduation event and `graduation_date`; reaching that date may transition the existing employee record to graduated rules without recreating it.

Allow manual override if management intentionally places a rookie elsewhere.

## 20. Duty-station diversity
For normal graduated patrollers and supervisors working 4 days:
- ideal is broad rotation such as Dercum / Outback / North Peak / Bergman
- repeated stations are allowed
- maximum 2 shifts at the same duty station per week

Examples allowed:
- D / D / OB / BB
- BB / OB / BB / NP
- NP / NP / D / OB

Examples disallowed without override/exemption:
- D / D / D / OB
- NP / NP / NP / D
- BB / BB / BB / BB

Normal `max_same_station_per_week = 2` should initialize as HARD, but rule hardness should be configurable.

Exemptions:
- rookies
- managers
- employee-specific required-station restriction
- explicit management override

## 21. Dercum fairness
Dercum is generally least desirable.

For normal graduated employees:
- 0 Dercum = allowed
- 1 Dercum = good
- 2 Dercum = always acceptable
- 3 Dercum = prohibited without exception
- 4 Dercum = prohibited except rookie/override

Do not strongly penalize exactly two Dercum shifts.

Season-to-date balancing should still prevent chronic Dercum overuse for some employees when comparable alternatives exist.

## 22. Southside history / fairness
Import the existing South-Side Tracker.

Track EmployeeSeasonStats:
- employee_id
- season
- dercum_days
- north_peak_days
- outback_days
- bergman_days
- southside_total
- first_tracks_days
- night_ski_days
- supervisor_days if useful
- last_station
- recent_station_sequence

`Southside total = NP + OB + Bergman`.

Use season-to-date history, not just the current week.

When two employees are operationally interchangeable, prefer the one with lower Southside exposure for a Southside opportunity.

Also try to balance NP/OB/Bergman exposure among comparable qualified employees.

## 23. Recent station variety
Optimize at two levels:

### Weekly
Do not exceed 2 at same station for normal graduated employees.

### Season-to-date / recency
Avoid repeated same-station sequences when practical.

If someone had BB yesterday and BB today, prefer another station tomorrow when operationally valid.

## 24. Supervisor families
Import the existing Families workbook.

Each family has one supervisor.

Family:
- id
- name
- supervisor_employee_id

FamilyMembership:
- family_id
- employee_id
- active_start
- active_end

Goal:
- supervisors should work directly with their family members regularly
- do not keep whole families together constantly
- family members still need diverse stations and broad team exposure

Family overlap is a soft objective.

The strongest definition of direct exposure is same duty station on the same date.

Track SupervisorFamilyExposure:
- supervisor_id
- family_member_id
- season
- same_station_days
- same_shift_days
- last_overlap_date

When otherwise comparable, favor family members with lower recent/season overlap with their supervisor.

## 25. Supervisor diversity
Supervisors follow the same general station-diversity rule as graduated patrollers:
- ideally rotate D / BB / NP / OB
- two Dercum days is acceptable
- normal max 2 at same station per 4-day week

Managers are exempt because managers always remain Dercum.

## 26. Manager work patterns and supervisor exposure
Managers use a configurable ManagerWorkPattern rather than the normal 4-day pattern. Initialize current operations for two managers at 5 days per week, always at Dercum, with their schedules covering both sides of the week.

Because managers always work Dercum, supervisors should rotate through Dercum so managers see a diverse supervisor group.

Track ManagerSupervisorExposure:
- manager_id
- supervisor_id
- season
- same_dercum_days
- last_overlap_date

If Supervisor S has much more exposure to Manager A than Manager B, and S must work Dercum on a day where either pairing is possible, prefer Manager B.

This is a soft objective below operational requirements.

Manager-supervisor exposure, supervisor-family exposure, and graduated-employee station diversity are related but independent objectives. Relationship optimization must never override safety, staffing, or qualification constraints.

## 27. Daily supervisor distribution
Daily requirements must support at least:
- Bergman supervisor
- Outback supervisor
- North Peak team lead / configured supervision
- Dercum MGMT supervisor
- First Tracks supervisor when active
- Night Ski supervisor when active

Some roles may overlap only if explicitly allowed by configuration and shift times are compatible.

First Tracks and Night Ski supervisors may not be the same employee on the same date.

## 28. PTO / time off
Initialize normal PTO limits from the current operating template:
- max 2 line-level patrollers off per day
- max 1 supervisor off per day
- additional requests require Director/management override

Statuses:
- PENDING
- APPROVED
- DENIED
- OVERRIDE_APPROVED

Once approved, PTO is respected as unavailable time.

Requests beyond the configured daily limit must be flagged `DIRECTOR / MANAGEMENT APPROVAL REQUIRED`. An explicit override approval makes that PTO unavailable time and requires staffing to be rebuilt around it.

Do not cancel PTO to make the solver work.

## 29. Part-time employees
Import the Part-Time Schedule Requests workbook.

Keep distinct:
- PT availability/request
- actual PT assignment

Never infer future availability from prior assignments.

PTs are used to:
- fill staffing holes
- cover PTO
- supplement high-demand days
- fill qualification shortages
- cover specialty shifts when eligible
- specific backfill

PartTimeAvailability:
- employee_id
- date
- available
- preferred
- requested_assignment
- notes

PartTimeAssignment:
- employee_id
- date
- shift
- station
- role

Allow employee-specific PT min/max shifts or hours.

## 30. Budget
Support:
- people/day targets
- hours/day targets
- hours/week targets
- staffing-wave budget
- date-specific budget adjustments

Budget behavior configurable as:
- HARD LIMIT
- TARGET
- INFORMATIONAL

Show target vs actual and variance.

If hard budget conflicts with minimum operational staffing, return infeasibility instead of silently breaking one side.

## 31. Work-pattern solver
Inputs:
- active roster
- awarded/start-wave eligibility
- ranked work-pattern preferences
- seniority
- weekday availability
- staffing target by weekday
- qualification coverage needs
- supervisor distribution
- budget

Outputs:
- awarded 4-day pattern for each normal FT employee
- 5-day manager pattern
- projected staffing by weekday
- preference award statistics

Priority:
1. feasibility
2. staffing balance
3. seniority-weighted preferences
4. qualification/supervisor distribution
5. optional secondary pattern quality

Do not assume contiguous schedules are always preferable when an employee explicitly ranks a split schedule.

## 32. Wave solver
Inputs:
- wave capacity / target people per day
- effective date
- employee wave preferences
- seniority
- qualifications
- rookie count
- trainer requirements
- supervisor coverage
- eventual work-pattern balance

Outputs:
- awarded starting wave
- active roster by wave
- projected weekday staffing
- qualification coverage by wave

Do not choose merely top N senior employees.

## 33. Deployment solver
For each date use:
- scheduled employees
- PTO/unavailability
- PT coverage
- duty-station requirements
- special roles
- First Tracks
- Night Ski
- rookies
- qualifications
- historical station counts
- family relationships
- manager-supervisor history
- manual locks

Output for every working employee:
- shift
- duty station
- role

Conceptual priority/order:
1. determine who is active for the date
2. determine which FT employees are scheduled to work that weekday
3. apply PTO/unavailability
4. add selected PT coverage
5. fill highly constrained special roles
6. fill First Tracks when active
7. fill Night Ski when active
8. fill required supervisors
9. fill route leaders, prospective route leaders, and team leads
10. satisfy Bergman minimum staffing
11. satisfy Outback minimum staffing
12. satisfy North Peak minimum staffing
13. assign remaining employees to Dercum
14. validate Dercum-specific roles
15. optimize station diversity
16. optimize Southside fairness
17. optimize manager-supervisor exposure
18. optimize supervisor-family exposure
19. optimize secondary crew-diversity objectives
20. validate the complete result

CP-SAT may solve globally. This list expresses priority, not mandatory procedural implementation.

## 34. Crew composition extensibility
Build flexible employee tags/attributes so future objectives can use:
- experience level
- skier/snowboarder
- seniority group
- rookie/graduated
- strong/developing technical skill
- route leader/prospective
- supervisor/team lead
- family
- development candidate
- peak-specific experience

Potential soft goals:
- avoid putting all newer employees together
- spread experienced patrollers
- spread specialized qualifications
- avoid clustering entire families
- provide development exposure

Do not invent subjective ratings that management has not supplied.

## 35. Templates
Templates are core.

Support examples such as:
- Early Season
- Wave 1
- Wave 2
- Wave 3
- Full Operations
- Holiday
- Late Season
- Custom

A template stores:
- active employees
- awarded normal work patterns
- manager work patterns
- baseline Night Ski / First Tracks allocations if used
- staffing requirements
- operating period
- budget config

Templates are saved by season and support clone/rename/edit/archive/versioning.

## 36. Weekly instances
A template can be instantiated into a specific week.

Weekly exceptions may include:
- PTO
- training
- PT additions
- Night Ski replacement
- special events

Re-solving a week should not alter the underlying season template unless explicitly saved back.

## 37. Manual editing
Admin must be able to:
- move station
- change shift
- change role
- add/remove assignment
- lock assignment
- override rule

Every manual change immediately re-validates the schedule.

Examples:
- valid move shows updated staffing and confirms all hard constraints satisfied
- invalid move explains what would break

## 38. Lock and re-solve
Support locks at useful levels:
- whole assignment
- employee week
- duty station
- shift
- role

Then provide `RE-OPTIMIZE UNLOCKED ASSIGNMENTS`.

Locked decisions may not be changed by the solver.

## 39. Overrides
Every override should record:
- user
- timestamp
- rule violated
- employee/date
- reason
- previous state
- new state

Never silently override.

## 40. Explainability
For each employee show:
- seniority rank / winter hours
- requested vs awarded start wave
- requested vs awarded work pattern
- Night Ski ranking vs award
- weekly stations
- season D/NP/OB/BB totals
- Southside total
- family supervisor
- overlap days with family supervisor
- manager exposure metrics if supervisor

When a preference was not awarded, provide a specific reason when provable.

If no single cause can be isolated, say the result was selected as part of the globally optimized staffing solution.

Do not fabricate explanations.

## 41. Infeasibility reporting
If no fully valid schedule exists, return structured conflicts.

Example categories:
- insufficient route leaders
- insufficient supervisors
- Night Ski shortage without overtime
- too many approved PTO absences for configured requirement
- hard budget below minimum staffing
- locked assignments causing conflict

Also show possible resolution categories such as:
- add PT coverage
- change work pattern
- activate another qualified employee
- approve override
- modify staffing requirement
- modify hard budget

Do not automatically choose a policy-breaking resolution.

## 42. UI screens
Keep UI functional and simple.

### Roster
Columns including name, employment type, supervisor, winter hours, seniority, start wave, pattern, rookie/graduated, family, qualifications, active.

### Preferences
Show raw employee response vs normalized scheduler input.

### Starting Waves
Show:
- wave
- effective date
- target people/day
- approximate FT required
- employees added
- rookies
- budget
- projected staffing Sun-Sat

### Operating Requirements
Configure by date range:
- Bergman
- Outback
- North Peak
- Dercum
- First Tracks
- Night Ski
- special roles

### Weekly Schedule
Grid by employee/day showing station, shift, role.

### Daily Operations
Management-friendly board grouped by First Tracks, Bergman, Outback, North Peak, Dercum, Night Ski, with warnings.

### Southside/Fairness
Employee D/NP/OB/BB totals, Southside total, recent sequence, peer comparison.

### Families
Supervisor and family members, work patterns, weekly assignments, overlap history, Southside stats.

### Manager/Supervisor Matrix
Same-Dercum exposure count for each manager/supervisor pair.

### Analytics
Preference awards, staffing, budget, fairness, diversity, family exposure, manager exposure, Night Ski, First Tracks.

## 43. Imports
Support import/mapping workflows for the supplied example files:
- Requests 25-26.xlsx
- Copy of Starting Waves 2025-2026.xlsx
- Families 25-26.xlsx
- South-Side Tracker 25-26.xlsx
- Part-Time Schedule Requests.xlsx

These are examples, not permanent schemas.

Use:

```text
Source Spreadsheet
  -> Importer / Mapping Layer
  -> Preview / Validation
  -> Normalized Database
```

Admin should be able to remap columns next year if sheet formats change.

## 44. Name matching
Prefer matching by:
1. employee ID if available
2. exact normalized full name
3. admin-confirmed fuzzy match

Never silently merge people using fuzzy matching alone.

Show unresolved and ambiguous names during import review.

## 45. Import validation
After import show counts for:
- matched employees
- new employees
- unresolved names
- ambiguous/duplicate matches
- invalid schedule patterns
- unknown qualifications
- parsing warnings

Require admin review for ambiguous mappings.

## 46. Exports
At minimum:

### Workday Entry Export
- Employee
- Employee ID
- Date
- Shift start
- Shift end
- Paid hours
- optional Workday shift code

### Patrol Deployment Export
- Date
- Employee
- Shift
- Duty station
- Role
- Supervisor
- Special role
- Notes

### Weekly Management Schedule
Human-readable Excel workbook.

### Southside Tracker Export
- Employee
- NP
- OB
- Bergman
- Southside total
- updated-through date

## 47. Season model
Everything belongs to a Season, e.g. 2025-2026, 2026-2027.

Season includes:
- employees
- seniority/winter hours
- preferences
- starting waves
- families
- operating periods
- history
- templates

Support cloning prior season while resetting assignments/counters/preferences/dates as appropriate and retaining reusable qualifications/family structure for review.

## 48. Configuration / Rules page
Editable settings should include:
- FT shifts/week
- FT hours/shift
- FT max weekly hours
- manager shifts/week
- shift times
- First Tracks count
- Night Ski count
- station max repeats/week
- Dercum duplicate treatment
- PTO limits
- station staffing requirements
- qualification requirements
- preference weights
- fairness weights
- relationship weights
- budget behavior
- HARD/SOFT status for configurable rules

Initialize with the rules in this specification.

## 49. Testing requirements
Build synthetic data around:
- ~100 employees
- ~75 FT
- ~25 PT
- supervisors
- 2 managers
- rookies
- route leaders/prospective leaders
- skiers/snowboarders
- 7-day operation
- all four stations
- Night Ski
- First Tracks
- multiple staffing waves
- families
- uneven historical Southside totals

Automated tests must verify at least:
1. normal FT exactly 4 shifts
2. normal FT exactly 40 hours
3. no normal FT overtime
4. managers correct configured 5-day pattern
5. managers always Dercum
6. rookies stay Dercum
7. graduated employee never >2 same-station days unless override/exemption
8. First Tracks count correct
9. First Tracks supervisor exists
10. Night Ski count correct
11. Night Ski supervisor exists
12. First Tracks and Night Ski supervisors differ
13. Bergman requirements filled
14. Outback requirements filled
15. North Peak requirements filled
16. special-role station restrictions honored
17. hard unavailability honored
18. approved PTO honored
19. hard budget honored
20. locks not moved
21. infeasible result returned instead of broken schedule
22. seniority meaningfully affects preference awards
23. Southside history affects equivalent deployments
24. family exposure affects equivalent deployments
25. manager-supervisor exposure affects equivalent deployments

## 50. Example rule tests
### Duty-station rotation
Graduated employee:
- D / D / OB / BB = valid
- BB / OB / BB / NP = valid
- D / D / D / NP = invalid
- BB / BB / BB / BB = invalid

Rookie:
- D / D / D / D = valid

### Family
Supervisor S with A/B/C should not require all four to travel together. Over several weeks A, B, and C should each receive meaningful same-station overlap with S while retaining station variety.

### Managers
If Supervisor S has M1 exposure 5 and M2 exposure 1, and either manager pairing is otherwise valid on the next Dercum day, prefer M2.

### Southside fairness
If A has much more NP/OB/BB exposure than equally qualified B, the next Southside opportunity should generally favor B.

### Seniority
If a senior and junior employee request the same scarce pattern and all else is equal, senior employee gets preference. If the senior choice makes the operation infeasible, another pattern may be awarded with explanation.

## 51. Performance
Target ~100 employees.

Typical solve scopes:
- staffing wave
- master work-pattern template
- one week
- several weeks

A weekly deployment solve should ideally complete within seconds to a few minutes.

Expose:
- solve time
- optimal/feasible/infeasible status
- objective values
- warnings
- configurable solver time limit

## 52. MVP exclusions
Do not build initially:
- payroll
- time clock
- full employee self-service portal
- native mobile app
- elaborate auth
- direct Workday integration
- real-time messaging
- fancy drag/drop
- AI scheduling layer

Focus on the actual constraint engine and template workflow.

## 53. Build order
### Phase 1: Data model + importers
Create normalized models and import/mapping/validation workflows for supplied sheets.

### Phase 2: Work-pattern + wave solver
Generate awarded start waves, FT patterns, manager patterns, and projected staffing.

### Phase 3: Deployment solver
Add station/shift/role assignment, rookies, max-2 station rule, special roles, four peaks, First Tracks, Night Ski.

### Phase 4: Fairness + relationships
Add Southside history, recent station diversity, manager-supervisor exposure, supervisor-family exposure.

### Phase 5: Manual editing
Move, lock, override, re-solve.

### Phase 6: Basic UI
Roster, Preferences, Waves, Requirements, Template/Week, Analytics.

### Phase 7: Export
Workday-entry export, deployment export, weekly management sheet, Southside export.

## 54. Critical coding rules
1. No hard-coded employee names.
2. No hard-coded annual dates.
3. No hard-coded roster size.
4. No hard-coded wave counts.
5. No hidden hard-coded station minimums in solver code.
6. No automatic conversion of free-text notes into hard constraints.
7. No silent missing-qualification handling.
8. No silent overtime.
9. No silent station-diversity violation.
10. No silent staffing shortage.
11. No silent fuzzy identity merge.
12. Do not optimize only one week while ignoring season history.
13. Do not treat families as fixed crews.
14. Do not treat First Tracks/Night Ski as stations.
15. Do not treat exactly two Dercum days as a failure.
16. Do not apply graduated diversity rules to rookies.
17. Do not apply normal 4-day pattern to managers.
18. Do not enforce scheduling rules only in frontend.
19. Do not call a schedule valid while hard constraints are broken.
20. Keep solver explainable/debuggable.

## 55. Ambiguity handling
If historical files or policy inputs conflict:
- do not invent an answer
- create configuration or flag the ambiguity for admin review

Examples:
- employee appears under two names
- conflicting schedule info across files
- uncertain specialty shift timing
- early wave cannot support enabled full-operations requirement
- unclear role overlap
- conflicting employee restrictions

## 56. Desired end-to-end workflow
1. Create/select season.
2. Import roster.
3. Import prior winter hours.
4. Calculate seniority.
5. Import employee wave/work-pattern/Night Ski preferences and restrictions.
6. Import Families.
7. Import Southside history.
8. Import PT availability.
9. Configure waves, budgets, operating requirements, special roles, Night Ski, First Tracks, managers.
10. Generate start-wave assignments.
11. Generate normal FT work-pattern template.
12. Review staffing across all weekdays.
13. Generate deployment template.
14. Review stations, special roles, shifts, supervisors, fairness, family exposure, manager exposure.
15. Manually adjust as needed.
16. Lock decisions.
17. Re-optimize remaining assignments.
18. Save/version template.
19. Clone into actual calendar week.
20. Apply PTO and other exceptions.
21. Add PT coverage.
22. Validate.
23. Export for Workday entry.
24. Export operational deployment schedule.

## 57. Definition of success
The system succeeds if management can combine:
- roughly 100 employees
- winter-hour seniority
- employee preferences
- starting-wave preferences
- PT availability
- qualifications
- rookies
- four duty stations
- special roles
- First Tracks
- Night Ski
- supervisor families
- 2 managers
- budget/staffing waves
- historical Southside use

and reliably produce a realistic, understandable, editable patrol schedule template that:
- staffs the operation
- respects hours
- avoids overtime
- honors seniority-based preferences where feasible
- distributes Southside duty fairly
- avoids repetitive station assignments
- handles rookies correctly
- gives supervisors regular family exposure
- gives managers diverse supervisor exposure
- satisfies special-role requirements
- surfaces shortages instead of hiding them
- supports manual adjustment and locked re-solving
- exports cleanly for Workday entry

## 58. First development task
Before substantial frontend work:

A. Create normalized database models.

B. Build import/mapping interfaces for the supplied spreadsheet formats.

C. Produce normalized representations of employees, preferences, waves, families, Southside counts, and PT availability.

D. Build import validation and unresolved-record reporting.

E. Create synthetic test fixtures.

F. Build the OR-Tools solver in stages.

G. Demonstrate one complete generated week as structured JSON plus a simple CLI/table output.

Only after the scheduling engine passes the core constraint tests should substantial frontend work begin.

Keep the application runnable after each phase and add automated tests alongside each major scheduling rule.
