"""Tests for NexusReasoningAgentLambda handler."""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

from nexus_reasoning_agent_lambda.handler import lambda_handler
from nexus_reasoning_agent_lambda.service import ReasoningAgentService


class TestLambdaHandler:
    """Tests for lambda_handler function."""

    def test_missing_source_control_id(self):
        """Test that missing source_control_id returns error."""
        event = {
            "source_text": "Control text",
            "mapping": {"target_control_id": "AC-1"},
        }
        response = lambda_handler(event, None)

        assert response["status"] == "error"
        assert "source_control_id is required" in response["error"]

    def test_missing_mapping(self):
        """Test that missing mapping returns error."""
        event = {
            "source_control_id": "AWS.ControlCatalog#1.0#CTRL-1",
            "source_text": "Control text",
        }
        response = lambda_handler(event, None)

        assert response["status"] == "error"
        assert "mapping is required" in response["error"]

    def test_successful_reasoning(self):
        """Test successful reasoning generation."""
        with patch(
            "nexus_reasoning_agent_lambda.handler.ReasoningAgentService"
        ) as MockService:
            mock_service = MagicMock()
            mock_service.generate_reasoning.return_value = {
                "reasoning": "Both controls address access management.",
                "source_control_id": "AWS.ControlCatalog#1.0#CTRL-1",
                "target_control_id": "NIST-SP-800-53#R5#AC-1",
            }
            MockService.return_value = mock_service

            event = {
                "source_control_id": "AWS.ControlCatalog#1.0#CTRL-1",
                "source_text": "Ensure access controls are configured.",
                "mapping": {
                    "target_control_id": "NIST-SP-800-53#R5#AC-1",
                    "target_framework": "NIST-SP-800-53",
                    "text": "Access control policy and procedures.",
                    "similarity_score": 0.87,
                    "rerank_score": 0.92,
                },
            }

            response = lambda_handler(event, None)

            assert response["status"] == "success"
            assert response["source_control_id"] == "AWS.ControlCatalog#1.0#CTRL-1"
            assert response["control_id"] == "NIST-SP-800-53#R5#AC-1"
            assert "reasoning" in response

    def test_reasoning_error(self):
        """Test handling of reasoning errors."""
        with patch(
            "nexus_reasoning_agent_lambda.handler.ReasoningAgentService"
        ) as MockService:
            mock_service = MagicMock()
            mock_service.generate_reasoning.side_effect = RuntimeError("Service unavailable")
            MockService.return_value = mock_service

            event = {
                "source_control_id": "AWS.ControlCatalog#1.0#CTRL-1",
                "source_text": "Control text",
                "mapping": {"target_control_id": "AC-1"},
            }

            response = lambda_handler(event, None)

            assert response["status"] == "error"
            assert "Service unavailable" in response["error"]

    def test_target_control_key_fallback(self):
        """Test fallback to target_control_key when target_control_id is missing."""
        with patch(
            "nexus_reasoning_agent_lambda.handler.ReasoningAgentService"
        ) as MockService:
            mock_service = MagicMock()
            mock_service.generate_reasoning.return_value = {
                "reasoning": "Test reasoning",
                "source_control_id": "SRC-1",
                "target_control_id": "NIST#R5#AC-1",
            }
            MockService.return_value = mock_service

            event = {
                "source_control_id": "SRC-1",
                "source_text": "Source text",
                "mapping": {
                    "target_control_key": "NIST#R5#AC-1",
                    "text": "Target text",
                },
            }

            response = lambda_handler(event, None)

            assert response["status"] == "success"
            assert response["control_id"] == "NIST#R5#AC-1"


class TestReasoningAgentService:
    """Tests for ReasoningAgentService class."""

    def test_generate_reasoning_with_mock(self):
        """Test reasoning generation using mock strands service."""
        service = ReasoningAgentService(strands_endpoint="")

        result = service.generate_reasoning(
            source_control_id="AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED",
            source_text="Ensure API Gateway caching is enabled.",
            mapping={
                "target_control_id": "NIST-SP-800-53#R5#AC-1",
                "target_framework": "NIST-SP-800-53",
                "text": "Access control policy and procedures.",
                "similarity_score": 0.87,
                "rerank_score": 0.92,
            },
        )

        assert "reasoning" in result
        assert len(result["reasoning"]) > 0
        assert result["source_control_id"] == "AWS.ControlCatalog#1.0#API_GW_CACHE_ENABLED"
        assert result["target_control_id"] == "NIST-SP-800-53#R5#AC-1"

    def test_generate_reasoning_extracts_framework_from_key(self):
        """Test that framework is extracted from target_framework_key."""
        service = ReasoningAgentService(strands_endpoint="")

        result = service.generate_reasoning(
            source_control_id="SRC-1",
            source_text="Source text",
            mapping={
                "target_control_key": "SOC2#2017#CC1.1",
                "target_framework_key": "SOC2#2017",
                "text": "Control environment",
                "similarity_score": 0.75,
                "rerank_score": 0.80,
            },
        )

        assert "reasoning" in result
        # Should extract "SOC2" from target_framework_key


class TestMockReasoning:
    """Tests for mock reasoning functionality."""

    def test_mock_reason_high_score(self):
        """Test mock reasoning for high rerank score."""
        service = ReasoningAgentService(strands_endpoint="")

        result = service._mock_reason(
            source_control_id="SRC-1",
            source_text="Source text",
            target_control_id="TGT-1",
            target_framework="NIST",
            target_text="Target text",
            similarity_score=0.90,
            rerank_score=0.95,
        )

        assert "strong" in result["reasoning"].lower()
        assert result["sourceControlId"] == "SRC-1"
        assert result["targetControlId"] == "TGT-1"

    def test_mock_reason_moderate_score(self):
        """Test mock reasoning for moderate rerank score."""
        service = ReasoningAgentService(strands_endpoint="")

        result = service._mock_reason(
            source_control_id="SRC-1",
            source_text="Source text",
            target_control_id="TGT-1",
            target_framework="NIST",
            target_text="Target text",
            similarity_score=0.65,
            rerank_score=0.70,
        )

        assert "moderate" in result["reasoning"].lower()

    def test_mock_reason_low_score(self):
        """Test mock reasoning for low rerank score."""
        service = ReasoningAgentService(strands_endpoint="")

        result = service._mock_reason(
            source_control_id="SRC-1",
            source_text="Source text",
            target_control_id="TGT-1",
            target_framework="NIST",
            target_text="Target text",
            similarity_score=0.45,
            rerank_score=0.50,
        )

        assert "weak" in result["reasoning"].lower()

    def test_mock_reason_includes_scores(self):
        """Test mock reasoning includes similarity and rerank scores."""
        service = ReasoningAgentService(strands_endpoint="")

        result = service._mock_reason(
            source_control_id="SRC-1",
            source_text="Source text",
            target_control_id="TGT-1",
            target_framework="SOC2",
            target_text="Target text",
            similarity_score=0.85,
            rerank_score=0.90,
        )

        assert "0.85" in result["reasoning"]
        assert "0.90" in result["reasoning"]
        assert "SOC2" in result["reasoning"]


class TestStrandsServiceIntegration:
    """Tests for strands service integration."""

    def test_call_strands_with_endpoint(self):
        """Test calling strands service when endpoint is configured."""
        service = ReasoningAgentService(strands_endpoint="http://localhost:8000")

        # Mock the HTTP request
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps({
            "sourceControlId": "SRC-1",
            "targetControlId": "TGT-1",
            "reasoning": "Reasoning from strands service",
            "status": "success",
        }).encode("utf-8")

        with patch.object(service.http, "request", return_value=mock_response):
            result = service._call_strands_reason(
                source_control_id="SRC-1",
                source_text="Source text",
                target_control_id="TGT-1",
                target_framework="NIST",
                target_text="Target text",
                similarity_score=0.85,
                rerank_score=0.90,
            )

            assert result["reasoning"] == "Reasoning from strands service"

    def test_call_strands_error_handling(self):
        """Test error handling for strands service failures."""
        service = ReasoningAgentService(strands_endpoint="http://localhost:8000")

        # Mock failed HTTP request
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.data = b"Internal Server Error"

        with patch.object(service.http, "request", return_value=mock_response):
            with pytest.raises(RuntimeError, match="Strands service error"):
                service._call_strands_reason(
                    source_control_id="SRC-1",
                    source_text="Source text",
                    target_control_id="TGT-1",
                    target_framework="NIST",
                    target_text="Target text",
                    similarity_score=0.85,
                    rerank_score=0.90,
                )

    def test_call_strands_request_format(self):
        """Test that request to strands service has correct format."""
        service = ReasoningAgentService(strands_endpoint="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps({
            "reasoning": "Test reasoning",
            "status": "success",
        }).encode("utf-8")

        with patch.object(service.http, "request", return_value=mock_response) as mock_request:
            service._call_strands_reason(
                source_control_id="AWS#1.0#CTRL-1",
                source_text="Source control text",
                target_control_id="NIST#R5#AC-1",
                target_framework="NIST-SP-800-53",
                target_text="Target control text",
                similarity_score=0.87,
                rerank_score=0.92,
            )

            # Verify request was made with correct URL and body
            call_args = mock_request.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "http://localhost:8000/api/v1/reason"

            body = json.loads(call_args[1]["body"])
            assert body["sourceControlId"] == "AWS#1.0#CTRL-1"
            assert body["sourceText"] == "Source control text"
            assert body["mapping"]["targetControlId"] == "NIST#R5#AC-1"
            assert body["mapping"]["targetFramework"] == "NIST-SP-800-53"
            assert body["mapping"]["similarityScore"] == 0.87
            assert body["mapping"]["rerankScore"] == 0.92
