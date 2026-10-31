"""Offline integration tests for pipeline ordering and failure handling."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image

from src.exceptions import ImageValidationError, ModelResponseError
from src.models import ContractChangeOutput
from src.pipeline import ContractAnalysisPipeline


@pytest.fixture
def images(tmp_path):
    paths = (
        tmp_path / "original contract.png",
        tmp_path / "amendment.png",
    )
    for path in paths:
        Image.new("RGB", (40, 40), "white").save(path)
    return paths


@pytest.fixture
def components(images):
    original_path, _ = images
    events = []
    report = ContractChangeOutput(
        sections_changed=["Cláusula 3"],
        topics_touched=["Condiciones de pago"],
        summary_of_the_change="El importe cambia de USD 500 a USD 650.",
    )

    def parse(path):
        events.append(("parse", path))
        text = "Original text" if path == original_path else "Amendment text"
        return SimpleNamespace(text=text)

    def contextualize(*args, **kwargs):
        events.append(("context", args))
        return "Contextual map"

    def extract(*args, **kwargs):
        events.append(("extract", args))
        return report

    parser = Mock(side_effect=parse)
    context_agent = Mock()
    context_agent.run.side_effect = contextualize
    extraction_agent = Mock()
    extraction_agent.run.side_effect = extract

    pipeline = ContractAnalysisPipeline(
        settings=SimpleNamespace(max_image_size_bytes=10_000),
        parser=parser,
        contextualization_agent=context_agent,
        extraction_agent=extraction_agent,
    )
    return SimpleNamespace(
        pipeline=pipeline,
        parser=parser,
        context=context_agent,
        extraction=extraction_agent,
        report=report,
        events=events,
    )


def test_executes_in_order_and_passes_exact_inputs(images, components):
    original_path, amendment_path = images
    config = {"tags": ["offline-test"]}

    result = components.pipeline.run(
        str(original_path), str(amendment_path), config=config
    )

    assert components.events == [
        ("parse", original_path),
        ("parse", amendment_path),
        ("context", ("Original text", "Amendment text")),
        (
            "extract",
            ("Original text", "Amendment text", "Contextual map"),
        ),
    ]
    assert components.parser.call_count == 2
    components.context.run.assert_called_once_with(
        "Original text", "Amendment text", config=config
    )
    components.extraction.run.assert_called_once_with(
        "Original text", "Amendment text", "Contextual map", config=config
    )
    assert result.analysis is components.report
    assert result.trace_id is None


@pytest.mark.parametrize("invalid_index", [0, 1])
def test_validates_both_images_before_any_parsing(images, components, invalid_index):
    images[invalid_index].write_text("Invalid image", encoding="utf-8")

    with pytest.raises(ImageValidationError):
        components.pipeline.run(*images)

    components.parser.assert_not_called()
    components.context.run.assert_not_called()
    components.extraction.run.assert_not_called()


@pytest.mark.parametrize("failing_parse", [0, 1])
def test_parsing_failure_prevents_agent_calls(images, components, failing_parse):
    error = ModelResponseError("Transcription failed")
    responses = [SimpleNamespace(text="Original text"), error]
    components.parser.side_effect = error if failing_parse == 0 else responses

    with pytest.raises(ModelResponseError, match="Transcription failed"):
        components.pipeline.run(*images)

    assert components.parser.call_count == failing_parse + 1
    components.context.run.assert_not_called()
    components.extraction.run.assert_not_called()


def test_context_failure_prevents_extraction(images, components):
    components.context.run.side_effect = ModelResponseError("Context failed")

    with pytest.raises(ModelResponseError, match="Context failed"):
        components.pipeline.run(*images)

    components.extraction.run.assert_not_called()


def test_extraction_failure_does_not_return_success(images, components):
    components.extraction.run.side_effect = ModelResponseError(
        "Output validation failed"
    )

    with pytest.raises(ModelResponseError, match="Output validation failed"):
        components.pipeline.run(*images)


def test_public_analysis_has_no_trace_field(images, components):
    result = components.pipeline.run(*images)

    assert set(result.analysis.model_dump()) == {
        "sections_changed",
        "topics_touched",
        "summary_of_the_change",
    }


def test_parser_receives_path_objects(images, components):
    components.pipeline.run(*(str(path) for path in images))

    for call in components.parser.call_args_list:
        assert isinstance(call.args[0], Path)
