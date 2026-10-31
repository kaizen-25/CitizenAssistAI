"""All Pydantic models. Single source of truth for API types (SPEC §3, §4.4, §5, §6, §9)."""
from typing import Literal

from pydantic import BaseModel, Field, RootModel, model_validator

DECLINED = "__declined__"
MAX_QUESTIONS = 8

Language = Literal["en", "hi"]
Operator = Literal["eq", "neq", "gt", "gte", "lt", "lte", "in", "not_in"]
FieldType = Literal["number", "integer", "enum", "boolean"]
RuleKind = Literal["hard", "manual_check"]
RuleOutcome = Literal["PASS", "FAIL", "UNKNOWN", "MANUAL", "NOT_APPLICABLE"]
SchemeStatus = Literal["potentially_eligible", "cannot_determine", "not_eligible"]
DocumentRequirement = Literal["mandatory", "optional"]
DocumentAnswer = Literal["have", "missing", "unsure"]
VerificationStatus = Literal["verified", "unverified"]
AnswerSource = Literal["answered", "extracted", "override"]

ScalarValue = bool | int | float | str
RuleValue = ScalarValue | list[ScalarValue] | None


# --- Data files (§3) ---


class Localized(BaseModel):
    en: str
    hi: str = ""
    pa: str = ""


class FieldOption(BaseModel):
    value: str
    label: Localized


class ProfileField(BaseModel):
    field_id: str
    type: FieldType
    options: list[FieldOption] | None = None
    unit: str | None = None
    min: float | None = None
    max: float | None = None
    sensitive: bool = False
    allow_prefer_not_to_say: bool = False
    ask_priority: int
    label: Localized
    question: Localized


class DocumentDef(BaseModel):
    label: Localized
    aliases: list[str] = []
    group: str
    issued_by_hint: str | None = None


class Condition(BaseModel):
    field: str
    operator: Operator
    value: RuleValue


class Rule(BaseModel):
    rule_id: str
    field: str | None = None
    operator: Operator | None = None
    value: RuleValue = None
    applies_if: Condition | None = None
    kind: RuleKind
    source_excerpt: str

    @model_validator(mode="after")
    def hard_rule_needs_comparison(self) -> "Rule":
        if self.kind == "hard" and (self.field is None or self.operator is None):
            raise ValueError(f"hard rule {self.rule_id} needs a field and an operator")
        return self


class SchemeDocument(BaseModel):
    document_id: str
    requirement: DocumentRequirement
    applies_if: Condition | None = None


class SchemeSource(BaseModel):
    url: str
    title: str
    published: str | None = None
    retrieved_on: str
    file: str | None = None


class Verification(BaseModel):
    status: VerificationStatus
    verified_by: str | None = None
    verified_on: str | None = None


class SchemeName(BaseModel):
    en: str


class Scheme(BaseModel):
    scheme_id: str
    name: SchemeName
    level: Literal["central", "state"]
    state: str | None = None
    category: str
    department: str
    summary: str
    benefits: str
    rules: list[Rule]
    documents: list[SchemeDocument]
    unmapped_conditions: list[str] = []
    application_url: str | None = None
    application_mode: list[str] = []
    source: SchemeSource
    verification: Verification


# --- Engine results (§4) ---


class RuleResult(BaseModel):
    rule_id: str
    outcome: RuleOutcome
    explanation: str = ""
    source_excerpt: str
    field: str | None = None
    operator: Operator | None = None
    value: RuleValue = None
    unknown_field: str | None = None


class DocumentBuckets(BaseModel):
    held: list[str] = []
    missing: list[str] = []
    unsure: list[str] = []
    possibly_required: list[str] = []
    optional_missing: list[str] = []


class ResultSource(BaseModel):
    url: str
    title: str
    retrieved_on: str


class SchemeResult(BaseModel):
    scheme_id: str
    name: str
    department: str
    status: SchemeStatus
    rules: list[RuleResult]
    unknown_fields: list[str] = []
    manual_checks: list[str] = []
    documents: DocumentBuckets
    document_ready: bool = False
    unmapped_conditions: list[str] = []
    source: ResultSource
    application_url: str | None = None


# --- Adaptive questions (§5) ---


class QuestionOption(BaseModel):
    value: str
    label: str


class Question(BaseModel):
    field_id: str
    question_text: str
    answer_type: FieldType
    options: list[QuestionOption] = []
    schemes_affected: int
    reason: str


# --- Document Unlock Plan (§6) ---


class UnlockRankingEntry(BaseModel):
    document_id: str
    label: str
    rank: int
    required_by: list[str]
    sole_blocker_for: list[str]


class UnlockPlanStep(BaseModel):
    step: int
    document_id: str
    newly_ready: list[str]
    cumulative_ready: int


class PendingInfo(BaseModel):
    scheme_id: str
    unknown_fields: list[str] = []
    missing_documents: list[str] = []


class UnlockReport(BaseModel):
    ready_now: list[str] = []
    ranking: list[UnlockRankingEntry] = []
    plan: list[UnlockPlanStep] = []
    pending_info: list[PendingInfo] = []


# --- API (§9) ---


class HealthResponse(BaseModel):
    llm_provider: str
    llm_available: bool
    demo_mode: bool
    schemes_loaded: int
    verified_by_category: dict[str, int]
    show_unverified: bool  # drives the dev-only banner required by §3.3


class ProfileEntry(BaseModel):
    value: ScalarValue
    source: AnswerSource
    label: str = ""
    display: str = ""


Profile = dict[str, ProfileEntry]


class Progress(BaseModel):
    answered: int
    max_questions: int = MAX_QUESTIONS


class CreateSessionRequest(BaseModel):
    language: Language = "en"


class CreateSessionResponse(BaseModel):
    session_id: str
    first_question: Question | None


class AnswerRequest(BaseModel):
    field_id: str
    value: ScalarValue


class AnswerResponse(BaseModel):
    profile: Profile
    next_question: Question | None
    progress: Progress


class MessageRequest(BaseModel):
    text: str


class ExtractedField(BaseModel):
    field_id: str
    value: ScalarValue
    evidence: str
    explicit: bool
    source: Literal["extracted"] = "extracted"
    note: str | None = None


class MessageResponse(BaseModel):
    extracted: list[ExtractedField]
    clarification: str | None
    profile: Profile
    next_question: Question | None


class DocumentsRequest(RootModel[dict[str, DocumentAnswer]]):
    pass


class OkResponse(BaseModel):
    ok: bool


class ChecklistItem(BaseModel):
    document_id: str
    label: str
    issued_by_hint: str | None = None
    answer: DocumentAnswer | None = None


class ChecklistResponse(BaseModel):
    documents: list[ChecklistItem]


class ConfirmRequest(BaseModel):
    profile_overrides: dict[str, ScalarValue] | None = None


class ConfirmResponse(BaseModel):
    confirmed: bool


class ResultGroups(BaseModel):
    potentially_eligible: list[SchemeResult] = []
    cannot_determine: list[SchemeResult] = []
    not_eligible: list[SchemeResult] = []


class Labels(BaseModel):
    fields: dict[str, str] = {}
    documents: dict[str, str] = {}


class ResultsResponse(BaseModel):
    confirmed: bool
    profile: Profile
    groups: ResultGroups
    labels: Labels


class PacketResponse(BaseModel):
    profile: Profile
    groups: ResultGroups
    unlock: UnlockReport
    labels: Labels
    disclaimer: str


class ChatRequest(BaseModel):
    question: str
    language: Language = "en"
    session_id: str | None = None


class Citation(BaseModel):
    chunk_id: str
    source_url: str
    source_title: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    grounded: bool
