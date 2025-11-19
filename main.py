import os
import hashlib
import json
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from database import db, create_document, get_documents
from schemas import ImpactAction, Proof

app = FastAPI(title="GreenProof API", description="Sustainable actions with verifiable (simulated) blockchain attestations")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility: create a stable hash for an action payload (simulated on-chain hash)

def action_proof_hash(action: ImpactAction, salt: Optional[str] = None) -> str:
    payload = action.model_dump(exclude={"attested", "proof_hash", "tx_id", "created_at", "updated_at"})
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")) + (salt or "")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CreateActionRequest(ImpactAction):
    pass


class CreateProofRequest(BaseModel):
    action_id: str
    salt: Optional[str] = None
    signer_address: Optional[str] = None
    signature: Optional[str] = None
    chain_id: Optional[int] = None


@app.get("/")
def read_root():
    return {"message": "GreenProof backend is running"}


@app.get("/schema")
def get_schema():
    # Expose defined schemas for the viewer
    return {
        "impactaction": ImpactAction.model_json_schema(),
        "proof": Proof.model_json_schema(),
    }


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            _ = db.list_collection_names()
            response["connection_status"] = "Connected"
            response["collections"] = _[:10]
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:100]}"
    return response


@app.post("/actions", response_model=dict)
def create_action(payload: CreateActionRequest):
    # Persist the action
    action = ImpactAction(**payload.model_dump())
    action_id = create_document("impactaction", action)
    return {"id": action_id}


@app.get("/actions", response_model=List[dict])
def list_actions():
    docs = get_documents("impactaction", {}, limit=100)
    # Convert ObjectId to string
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs


@app.post("/actions/{action_id}/attest", response_model=dict)
def attest_action(action_id: str, body: CreateProofRequest):
    # fetch action
    from bson import ObjectId
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        raw = db["impactaction"].find_one({"_id": ObjectId(action_id)})
    except Exception:
        raw = None
    if not raw:
        raise HTTPException(status_code=404, detail="Action not found")

    # Build model for hashing
    action = ImpactAction(
        actor=raw.get("actor"),
        title=raw.get("title"),
        description=raw.get("description"),
        category=raw.get("category"),
        quantity=float(raw.get("quantity")),
        unit=raw.get("unit"),
        location=raw.get("location"),
        evidence_url=raw.get("evidence_url"),
        attested=bool(raw.get("attested", False)),
        proof_hash=raw.get("proof_hash"),
        tx_id=raw.get("tx_id"),
    )

    phash = action_proof_hash(action, salt=body.salt)
    tx_id = hashlib.sha256((phash + "|tx").encode()).hexdigest()[:32]

    # upsert proof
    now = datetime.now(timezone.utc)
    proof_doc = {
        "action_id": action_id,
        "proof_hash": phash,
        "tx_id": tx_id,
        "network": "sim-chain",
        "signer_address": body.signer_address,
        "signature": body.signature,
        "chain_id": body.chain_id,
        "created_at": now,
        "updated_at": now,
    }
    db["proof"].insert_one(proof_doc)

    # mark action attested
    db["impactaction"].update_one(
        {"_id": raw["_id"]},
        {"$set": {"attested": True, "proof_hash": phash, "tx_id": tx_id, "updated_at": now}},
    )
    return {"proof_hash": phash, "tx_id": tx_id}


@app.get("/proofs", response_model=List[dict])
def list_proofs():
    docs = get_documents("proof", {}, limit=100)
    for d in docs:
        d["id"] = str(d.pop("_id"))
        # Normalize optional fields
        if "signer_address" not in d:
            d["signer_address"] = None
        if "signature" not in d:
            d["signature"] = None
        if "chain_id" not in d:
            d["chain_id"] = None
    return docs


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
