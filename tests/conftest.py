"""Pytest fixtures for Datheon Enterprise FDE test suite."""
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from src.api.app import app
from src.core.config import ClearanceTier, Department, get_settings
from src.core.security import EnterpriseUser
from src.etl.embedder import EnterpriseEmbedder
from src.etl.pipeline import VectorETLPipeline
from src.etl.vector_store import InMemoryCosineVectorStore
from src.services.mock_erp_crm import MockEnterpriseService


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture(scope="session")
def embedder():
    return EnterpriseEmbedder()


@pytest.fixture(scope="session")
def vector_store(embedder, settings):
    store = InMemoryCosineVectorStore(dimension=settings.VECTOR_DIMENSION)
    pipeline = VectorETLPipeline(vector_store=store, embedder=embedder)
    raw_dir = settings.DATA_DIR / "raw"
    if raw_dir.exists():
        pipeline.ingest_directory(raw_dir)
    return store


@pytest.fixture
def mock_erp(tmp_path):
    db_file = tmp_path / "test_erp_db.json"
    return MockEnterpriseService(db_path=db_file)


@pytest.fixture
def api_client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def user_eng_l2():
    return EnterpriseUser(
        user_id="USR-ENG-4401",
        name="Alex Mercer",
        department=Department.ENGINEERING,
        clearance=ClearanceTier.L2_RESTRICTED,
    )


@pytest.fixture
def user_fin_l3():
    return EnterpriseUser(
        user_id="USR-FIN-9901",
        name="Sarah Jenkins",
        department=Department.FINANCE,
        clearance=ClearanceTier.L3_CONFIDENTIAL,
    )


@pytest.fixture
def user_hr_l3():
    return EnterpriseUser(
        user_id="USR-HR-2010",
        name="David Chen",
        department=Department.HR,
        clearance=ClearanceTier.L3_CONFIDENTIAL,
    )


@pytest.fixture
def user_pub_l1():
    return EnterpriseUser(
        user_id="USR-PUB-0012",
        name="Junior Intern",
        department=Department.CROSS_FUNCTIONAL,
        clearance=ClearanceTier.L1_PUBLIC,
    )

