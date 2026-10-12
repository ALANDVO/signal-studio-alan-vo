import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["ENVIRONMENT"] = "test"
os.environ["AUTH_DEMO_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.core.database import Base, get_db
from app.core.security import create_token
from app.main import create_app

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def app_instance(db_session):
    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
def client(app_instance):
    return TestClient(app_instance)


@pytest.fixture
def viewer_token():
    return create_token("user-v-01", "viewer-user", "viewer@signalstudio.local", "viewer")


@pytest.fixture
def operator_token():
    return create_token("user-o-01", "operator-user", "operator@signalstudio.local", "operator")


@pytest.fixture
def admin_token():
    return create_token("user-a-01", "admin-user", "admin@signalstudio.local", "admin")
