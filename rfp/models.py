"""Typed data contracts shared by the agents and tools."""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SupplierInput(BaseModel):
    """What the user submits for one supplier."""
    supplier_name: str = Field(min_length=2, max_length=120)
    submission_date: date
    experience_rating: float = Field(ge=0, le=100)
    file_name: str
    file_bytes: bytes = Field(repr=False)

    @field_validator("supplier_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("Supplier name is required")
        if not any(ch.isalpha() for ch in v):
            raise ValueError("Supplier name must contain letters")
        return v


class CriterionScore(BaseModel):
    """One validated criterion result for one supplier (output of the Validation Tool)."""
    criterion_id: int
    criterion_name: str
    score: float = Field(ge=0)
    max_score: int = Field(gt=0)
    justification: str = ""
    evidence: str = ""
    validation_flags: list[str] = Field(default_factory=list)
    evidence_found_in_document: Optional[bool] = None
    evidence_location: Optional[dict] = None


class ValidatedScorecard(BaseModel):
    supplier_name: str
    criteria: list[CriterionScore]
    risks: list[str] = Field(default_factory=list)
    overall_summary: str = ""
    validation_warnings: list[str] = Field(default_factory=list)
