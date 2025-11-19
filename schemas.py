"""
Database Schemas for GreenProof (Sustainable Blockchain-inspired App)

Each Pydantic model represents a collection in MongoDB.
Collection name is the lowercase of the class name.

- ImpactAction -> "impactaction"
- Proof -> "proof"

"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class ImpactAction(BaseModel):
    """
    A real-world sustainable action submitted by a user or organization.
    Examples: planting trees, recycling, renewable energy generation, e-waste collection, etc.
    """
    actor: str = Field(..., description="Person or org responsible for the action")
    title: str = Field(..., description="Short title for the action")
    description: Optional[str] = Field(None, description="Detailed description of the impact")
    category: Literal[
        "renewables",
        "recycling",
        "reforestation",
        "transport",
        "water",
        "buildings",
        "circular-economy",
        "other",
    ] = Field(..., description="Impact category")
    quantity: float = Field(..., gt=0, description="Measured quantity of the impact")
    unit: str = Field(..., description="Unit for quantity (e.g., kWh, kg, trees, L)")
    location: Optional[str] = Field(None, description="City, region, or coordinates")
    evidence_url: Optional[str] = Field(None, description="Link to evidence: doc, photo, meter data, etc.")
    attested: bool = Field(False, description="Whether this action has a minted proof")
    proof_hash: Optional[str] = Field(None, description="Hash that represents the on-chain proof (simulated)")
    tx_id: Optional[str] = Field(None, description="Simulated transaction id for the attestation")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Proof(BaseModel):
    """A verifiable attestation derived from an ImpactAction"""
    action_id: str = Field(..., description="ID of the ImpactAction this proof belongs to")
    proof_hash: str = Field(..., description="Deterministic hash of canonicalized action payload + salt")
    tx_id: str = Field(..., description="Simulated transaction id")
    network: Literal["sim-chain", "testnet", "mainnet"] = Field("sim-chain", description="Target chain (simulated)")
    signer_address: Optional[str] = Field(None, description="Address of the signer who approved the attestation")
    signature: Optional[str] = Field(None, description="Wallet signature over an attestation message")
    chain_id: Optional[int] = Field(None, description="EVM chain id if applicable")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Backward-compatible example schemas remain available for reference
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = None
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
