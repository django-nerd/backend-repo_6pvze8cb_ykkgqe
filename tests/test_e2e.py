import os
import time
import requests

BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")


def test_health_and_schema():
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200
    assert "GreenProof" in r.json().get("message", "")

    s = requests.get(f"{BASE_URL}/schema")
    assert s.status_code == 200
    data = s.json()
    assert "impactaction" in data and "proof" in data


def test_full_flow_create_attest_list():
    # Create an action
    payload = {
        "actor": "Test User",
        "title": "Solar generation",
        "description": "Generated clean energy from rooftop PV",
        "category": "renewables",
        "quantity": 12.5,
        "unit": "kWh",
        "location": "Test City",
        "evidence_url": "https://example.com/evidence.jpg"
    }
    resp = requests.post(f"{BASE_URL}/actions", json=payload)
    assert resp.status_code == 200
    action_id = resp.json()["id"]
    assert action_id

    # Attest (simulate wallet fields present but not validated on-chain)
    attest_body = {
        "action_id": action_id,
        "signer_address": "0xDeaDbeef00000000000000000000000000000000",
        "signature": "0x",
        "chain_id": 1337
    }
    a = requests.post(f"{BASE_URL}/actions/{action_id}/attest", json=attest_body)
    assert a.status_code == 200
    proof_info = a.json()
    assert "proof_hash" in proof_info and len(proof_info["proof_hash"]) == 64
    assert "tx_id" in proof_info and len(proof_info["tx_id"]) == 32

    # List actions and ensure it's marked attested
    la = requests.get(f"{BASE_URL}/actions")
    assert la.status_code == 200
    actions = la.json()
    found = next((x for x in actions if x["id"] == action_id), None)
    assert found is not None
    assert found.get("attested") is True
    assert found.get("proof_hash") == proof_info["proof_hash"]

    # List proofs and ensure one exists for this action
    # Small wait in case DB write is slightly delayed
    time.sleep(0.2)
    lp = requests.get(f"{BASE_URL}/proofs")
    assert lp.status_code == 200
    proofs = lp.json()
    related = [p for p in proofs if p.get("action_id") == action_id]
    assert len(related) >= 1
    p = related[-1]
    assert p.get("proof_hash") == proof_info["proof_hash"]
    assert p.get("tx_id") == proof_info["tx_id"]
    # optional signer metadata should be present
    assert p.get("signer_address") == attest_body["signer_address"]
    assert p.get("chain_id") == attest_body["chain_id"]
