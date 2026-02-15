"""Tests for comparison module."""

import pytest
from unittest.mock import MagicMock, patch

from upscaler.core.comparison import ComparisonResult, ModelResult


class TestComparisonResult:
    def test_result_structure(self):
        result = ComparisonResult(input_path="test.png", scale=4)
        assert result.results == []
        assert result.scale == 4

    def test_add_model_result(self):
        result = ComparisonResult(input_path="test.png", scale=4)
        result.results.append(ModelResult(
            model_id="test_model",
            output_path="output.png",
            duration_seconds=1.5,
        ))
        assert len(result.results) == 1
        assert result.results[0].success is True

    def test_failed_model_result(self):
        result = ModelResult(
            model_id="bad_model",
            output_path="",
            duration_seconds=0.1,
            success=False,
            error="Model failed to load",
        )
        assert not result.success
        assert result.error == "Model failed to load"
