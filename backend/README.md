# Backend

The backend starts with a normalized SQLAlchemy domain model. SQLite is the MVP
database; models avoid SQLite-specific column types so the same metadata can target
PostgreSQL later.

Initialize and seed a database:

```python
from sqlalchemy.orm import Session
from backend.database import initialize_sqlite
from backend.seeds import seed_reference_data

engine = initialize_sqlite("patrol.db")
with Session(engine) as session:
    seed_reference_data(session)
```

`Season` owns configurable normal full-time work limits. Paid absence/status records
are intentionally distinct from future worked-shift assignments. Station reference
data contains identity and labels only; staffing counts belong to requirement sets.
