"""Define the validated public contract analysis output."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContractChangeOutput(BaseModel):
    """Structured changes supported by the original contract and amendment."""

    model_config = ConfigDict(strict=True, extra="forbid")

    sections_changed: list[str] = Field(
        description=(
            "Identifiers of substantively modified or added sections, "
            "explicitly deleted sections, or original sections conclusively "
            "absent from a clearly complete revised version. "
            "Omission from a partial or uncertain-scope amendment is not "
            "sufficient evidence of deletion. Renumbering alone is not "
            "a substantive change."
        )
    )
    topics_touched: list[str] = Field(
        description="Legal or commercial topics affected by the changes."
    )
    summary_of_the_change: str = Field(
        description=(
            "Evidence-based summary of additions, deletions, and modifications, "
            "including relevant previous and new values."
        )
    )

    @field_validator("sections_changed", "topics_touched")
    @classmethod
    def reject_blank_items(cls, values: list[str]) -> list[str]:
        """Reject blank items without silently changing their contents."""
        if any(not value.strip() for value in values):
            raise ValueError("List items must not be blank.")
        return values

    @field_validator("summary_of_the_change")
    @classmethod
    def reject_blank_summary(cls, value: str) -> str:
        """Require a meaningful nonblank summary."""
        if not value.strip():
            raise ValueError("The summary must not be blank.")
        return value
