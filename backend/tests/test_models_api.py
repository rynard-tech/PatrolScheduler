from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from backend.api.app import app
from backend.models import Base

def test_schema_creates_and_health_endpoint():
    engine=create_engine("sqlite://"); Base.metadata.create_all(engine)
    assert "assignments" in Base.metadata.tables
    assert TestClient(app).get("/health").json()=={"status":"ok"}
