"""Extract validated contract changes using both documents and their map."""

from pathlib import Path

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from pydantic import ValidationError

from src.exceptions import ModelResponseError
from src.llm_client import call_with_retries, validate_agent_message
from src.models import ContractChangeOutput

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "extraction.md"


def validate_extraction_response(response: object) -> ContractChangeOutput:
    """Accept only a completed response containing a validated report."""
    if not isinstance(response, dict):
        raise ModelResponseError("Invalid structured response envelope.")

    required_keys = {"raw", "parsed", "parsing_error"}
    if not required_keys.issubset(response):
        raise ModelResponseError("Incomplete structured response envelope.")

    raw = response["raw"]
    if not isinstance(raw, AIMessage):
        raise ModelResponseError("The raw model response is missing or invalid.")

    validate_agent_message(raw)

    if response["parsing_error"] is not None:
        raise ModelResponseError(
            "The extracted report failed structured output validation."
        ) from None

    parsed = response["parsed"]
    if not isinstance(parsed, ContractChangeOutput):
        raise ModelResponseError("The model returned no validated report.")

    return parsed


class ExtractionAgent:
    """Identify supported changes and return the validated public schema."""

    def __init__(self, model, *, max_retries: int = 0) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must not be negative.")

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", PROMPT_PATH.read_text(encoding="utf-8")),
                (
                    "human",
                    "ORIGINAL CONTRACT:\n"
                    "<original_contract>\n{original_text}\n</original_contract>\n\n"
                    "AMENDMENT:\n"
                    "<amendment>\n{amendment_text}\n</amendment>\n\n"
                    "CONTEXTUAL MAP:\n"
                    "<contextual_map>\n{contextual_map}\n</contextual_map>",
                ),
            ]
        )
        structured_model = model.with_structured_output(
            ContractChangeOutput,
            method="json_schema",
            strict=True,
            include_raw=True,
        )
        self._chain = prompt | structured_model
        self._max_retries = max_retries

    def run(
        self,
        original_text: str,
        amendment_text: str,
        contextual_map: str,
        *,
        config: RunnableConfig | None = None,
    ) -> ContractChangeOutput:
        """Extract changes while retaining raw response validation."""
        inputs = {
            "original_text": original_text,
            "amendment_text": amendment_text,
            "contextual_map": contextual_map,
        }
        if any(not value.strip() for value in inputs.values()):
            raise ValueError("Both document texts and contextual map are required.")

        try:
            response = call_with_retries(
                lambda: self._chain.invoke(inputs, config=config),
                max_retries=self._max_retries,
            )
        except ValidationError:
            raise ModelResponseError(
                "The extracted report failed structured output validation."
            ) from None

        return validate_extraction_response(response)
