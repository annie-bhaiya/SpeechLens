from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator

class Word(BaseModel):
    id: int
    text: str
    start_s: float | None
    end_s: float | None
    confidence: float = Field(ge=0,le=1)
    recognized_match: bool
    source: str
    review_status: str

    @model_validator(mode="after")
    def boundaries(self):
        if (self.start_s is None)!=(self.end_s is None):
            raise ValueError("Word endpoints must both be null or present.")
        if self.start_s is not None and not 0<=self.start_s<=self.end_s:
            raise ValueError("Word endpoints must be nonnegative and monotone.")
        return self

class Alignment(BaseModel):
    words: list[Word]
    coverage: float = Field(ge=0,le=1)
    recognized_text: str
    edits: list[dict]
    asr_match_fraction: float = Field(ge=0,le=1)
    model: str
    revision: str
    duration_s: float
    independently_reviewed: bool

class Event(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    type: str
    severity: float = Field(ge=0,le=1)
    severity_level: int = Field(ge=1,le=4)
    participant_interval_s: tuple[float,float]
    reference_interval_s: tuple[float,float] | None
    token_ids: list[int]
    quote: str
    measurements: dict
    delta: float
    rule_id: str
    threshold_version: str
    confidence: str
    confidence_rationale: str
    interpretation: str
    suggestion: str
    formula: str
    thresholds: dict

    @model_validator(mode="after")
    def boundaries(self):
        for interval in [self.participant_interval_s,self.reference_interval_s]:
            if interval is not None and not 0<=interval[0]<=interval[1]:
                raise ValueError("Event endpoints must be nonnegative and monotone.")
        return self

class Result(BaseModel):
    schema_version: str
    mode: Literal["paired","unpaired"]
    transcript: dict
    alignments: dict[str,Alignment]
    events: list[Event]
    scores: dict
    features: dict
    comparison: dict
    scoring_units: dict
    warnings: list[str]
    provenance: dict

class Job(BaseModel):
    id: str
    status: Literal["queued","running","succeeded","failed"]
    stage: str
    progress: float
    error: str | None
    created_at: str
    updated_at: str
    attempts: int
