"""Unit and integration tests for Datheon Python Client SDK."""
import pytest
from src.client_sdk import ClientConfig, DatheonFDEClient


def test_client_sdk_instantiation_and_headers():
    config = ClientConfig(
        base_url="http://localhost:8000",
        employee_id="USR-FIN-9901",
        name="Sarah Jenkins",
        department="finance",
        clearance="L3_CONFIDENTIAL"
    )
    client = DatheonFDEClient(config=config)
    headers = client._get_headers()

    assert headers["X-Employee-ID"] == "USR-FIN-9901"
    assert headers["X-Department"] == "finance"
    assert headers["X-Clearance-Tier"] == "L3_CONFIDENTIAL"
    assert headers["X-Correlation-ID"].startswith("sdk-corr-")
    client.close()


def test_client_sdk_context_manager():
    with DatheonFDEClient() as client:
        assert client is not None
