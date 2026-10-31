"""Map contract sections using a specialized LangChain agent."""

from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda

from src.llm_client import call_with_retries, validate_agent_message

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "contextualization.md"


class ContextualizationAgent:
    """Build a section map without producing the final change report."""

    def __init__(self, model: Runnable, *, max_retries: int = 0) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must not be negative.")

        system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                (
                    "human",
                    "ORIGINAL CONTRACT:\n"
                    "<original_contract>\n{original_text}\n</original_contract>\n\n"
                    "AMENDMENT:\n"
                    "<amendment>\n{amendment_text}\n</amendment>",
                ),
            ]
        )
        self._chain = (
            prompt | model | RunnableLambda(validate_agent_message) | StrOutputParser()
        )
        self._max_retries = max_retries

    def run(
        self,
        original_text: str,
        amendment_text: str,
        *,
        config: RunnableConfig | None = None,
    ) -> str:
        """Map both documents, allowing callbacks through RunnableConfig."""
        if not original_text.strip() or not amendment_text.strip():
            raise ValueError("Both document texts must be nonblank.")

        return call_with_retries(
            lambda: self._chain.invoke(
                {
                    "original_text": original_text,
                    "amendment_text": amendment_text,
                },
                config=config,
            ),
            max_retries=self._max_retries,
        )
