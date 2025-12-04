"""
Profile-Driven Multi-Agent AWS Control Enrichment System
Embeds AWS control profile as context for specialized agents.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from boto3 import Session
from strands import Agent
from strands.models import BedrockModel

from nexus_enrichment_agent.utils.config import load_session_params
from nexus_enrichment_agent.utils.logger import get_callback_handler, get_session_timestamp

logger = logging.getLogger(__name__)


class ProfileDrivenAWSProcessor:
    """AWS control processor using profile-enhanced specialized agents."""

    _mcp_semaphore = asyncio.Semaphore(1)

    def __init__(
        self,
        service_name: str,
        aws_profile: Dict[str, Any] = None,
        model: str = None,
        session_params: Dict = None,
        mcp_client: Optional[Any] = None,
    ):
        self.service_name = service_name
        self.aws_profile = aws_profile or {}
        self.session_params = session_params
        self.mcp_client = mcp_client

        self.model_id = model or "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
        self.temperature = 0

        # Extract profile components
        self.agent_context = self.aws_profile.get("agent_context", {})
        self.enrichment_guidance = self.aws_profile.get("enrichment_guidance", {})
        self.pattern_analysis = self.aws_profile.get("pattern_analysis", {})

    def get_bedrock_model(self) -> BedrockModel:
        """Get a Bedrock model instance."""
        bedrock_session_params = self.session_params or load_session_params(bedrock_only=True)
        return BedrockModel(
            boto_session=Session(**bedrock_session_params) if bedrock_session_params else Session(),
            model_id=self.model_id,
            temperature=self.temperature,
        )

    def _build_service_context(self) -> str:
        """Build service context header."""
        if not self.aws_profile:
            return ""

        parts = [f"SERVICE: {self.service_name}"]

        if self.pattern_analysis:
            characteristics = self.pattern_analysis.get("control_characteristics", {})
            parts.append(f"PRIMARY FOCUS: {characteristics.get('primary_focus', 'N/A')}")

        philosophy = self.enrichment_guidance.get("enrichment_philosophy", "")
        if philosophy:
            parts.append(f"\nGUIDANCE: {philosophy}")

        return "\n".join(parts)

    def _get_agent_prompt(
        self, agent_key: str, default_prompt: str, mcp_instruction: str = None
    ) -> str:
        """Get profile-enhanced prompt for agent with optional MCP instructions."""
        agent_guidance = None
        for guidance in self.enrichment_guidance.get("agent_guidance", []):
            if guidance.get("agent") == agent_key:
                agent_guidance = guidance
                break

        parts = []

        service_context = self._build_service_context()
        if service_context:
            parts.append(service_context)

        if agent_guidance:
            if agent_guidance.get("emphasize"):
                parts.append(f"\nEMPHASIZE: {agent_guidance['emphasize']}")
            if agent_guidance.get("skip_if"):
                parts.append(f"SKIP IF: {agent_guidance['skip_if']}")
            if agent_guidance.get("aws_rules"):
                parts.append(f"RULES: {agent_guidance['aws_rules']}")

        parts.append(f"\n{default_prompt}")

        if mcp_instruction:
            parts.append(f"\n{mcp_instruction}")

        if len(parts) == 1:
            return default_prompt

        return "\n".join(parts)

    async def enrich_control(
        self, control_info: Dict, control_data: Dict = None
    ) -> Dict[str, Any]:
        """Process AWS control using 4 profile-enhanced specialized agents."""
        control_id = control_info.get("control_id", "unknown")

        try:
            # Get MCP tools if client is available
            aws_tools = []
            if self.mcp_client:
                try:
                    aws_tools = self.mcp_client.list_tools_sync()
                except Exception as e:
                    logger.warning(f"Failed to get MCP tools: {e}")

            # Agent 1: Control Purpose & Detection
            agent1_prompt = self._get_agent_prompt(
                "agent1",
                """Extract control purpose and detection method.

OUTPUT JSON:
{
  "control_purpose": "What the control checks/enforces",
  "detection_method": "How non-compliance is detected",
  "compliance_criteria": "Specific criteria for compliance"
}

Return valid JSON only.""",
                mcp_instruction=(
                    "IMPORTANT: Make ONLY 2-3 MCP tool calls maximum."
                    if aws_tools
                    else None
                ),
            )

            agent1 = Agent(
                model=self.get_bedrock_model(),
                system_prompt=agent1_prompt,
                tools=aws_tools if aws_tools else None,
                callback_handler=get_callback_handler(),
                trace_attributes={
                    "session.id": get_session_timestamp(),
                    "agent.type": "purpose-detector",
                    "agent.name": "agent1-purpose",
                    "service": self.service_name,
                },
            )

            # Agent 2: Resource Scope
            agent2_prompt = self._get_agent_prompt(
                "agent2",
                """Identify AWS resources and parameters.

OUTPUT JSON:
{
  "resource_types": ["AWS::Service::ResourceType"],
  "parameters_checked": ["parameter1", "parameter2"],
  "resource_attributes": ["attribute1", "attribute2"]
}

Return valid JSON only.""",
                mcp_instruction=(
                    "IMPORTANT: Make ONLY 2-3 MCP tool calls."
                    if aws_tools
                    else None
                ),
            )

            agent2 = Agent(
                model=self.get_bedrock_model(),
                system_prompt=agent2_prompt,
                tools=aws_tools if aws_tools else None,
                callback_handler=get_callback_handler(),
                trace_attributes={
                    "session.id": get_session_timestamp(),
                    "agent.type": "resource-specialist",
                    "agent.name": "agent2-resources",
                    "service": self.service_name,
                },
            )

            # Agent 3: Service Implementation
            agent3_prompt = self._get_agent_prompt(
                "agent3",
                """Identify primary AWS services (max 2-3).

OUTPUT JSON:
{
  "primary_services": ["Service1", "Service2"],
  "service_capabilities": ["capability1", "capability2"],
  "implementation_approach": "Brief description"
}

Return valid JSON only.""",
                mcp_instruction=(
                    "IMPORTANT: Make ONLY 2-3 MCP tool calls maximum."
                    if aws_tools
                    else None
                ),
            )

            agent3 = Agent(
                model=self.get_bedrock_model(),
                system_prompt=agent3_prompt,
                tools=aws_tools if aws_tools else None,
                callback_handler=get_callback_handler(),
                trace_attributes={
                    "session.id": get_session_timestamp(),
                    "agent.type": "service-specialist",
                    "agent.name": "agent3-services",
                    "service": self.service_name,
                },
            )

            # Agent 4: Security Domain
            agent4_prompt = self._get_agent_prompt(
                "agent4",
                """Map to security domains and actions.

OUTPUT JSON:
{
  "security_domains": ["Domain1"],
  "technical_actions": ["action1"],
  "security_impact": "Risk prevention",
  "threat_mitigation": "Threats addressed"
}

Return valid JSON only.""",
                mcp_instruction=(
                    "IMPORTANT: Make ONLY 2-3 MCP tool calls maximum."
                    if aws_tools
                    else None
                ),
            )

            agent4 = Agent(
                model=self.get_bedrock_model(),
                system_prompt=agent4_prompt,
                tools=aws_tools if aws_tools else None,
                callback_handler=get_callback_handler(),
                trace_attributes={
                    "session.id": get_session_timestamp(),
                    "agent.type": "security-specialist",
                    "agent.name": "agent4-security",
                    "service": self.service_name,
                },
            )

            # Master Agent
            master_prompt = self._get_agent_prompt(
                "master",
                """Master Integration Agent: Merge specialist outputs.

RULES:
1. Keep primary_services to 2-3 services max
2. Validate consistency across agents
3. Remove redundancies
4. Be specific to the control

Combine all agent outputs into consolidated JSON.
Return ONLY valid JSON.""",
                mcp_instruction="DO NOT make any MCP tool calls - work with provided data only.",
            )

            master_agent = Agent(
                model=self.get_bedrock_model(),
                system_prompt=master_prompt,
                tools=[],
                callback_handler=get_callback_handler(),
                trace_attributes={
                    "session.id": get_session_timestamp(),
                    "agent.type": "master-integration",
                    "agent.name": "master-agent",
                    "service": self.service_name,
                },
            )

            # Execute agents with retry
            def run_agent_with_retry(agent, query, agent_name, max_retries=2):
                for attempt in range(max_retries + 1):
                    try:
                        return agent(query)
                    except Exception as e:
                        if attempt == max_retries:
                            logger.error(
                                f"{agent_name} failed after {max_retries + 1} attempts: {str(e)}"
                            )
                            return f"{agent_name} failed: {str(e)}"
                        logger.warning(f"{agent_name} attempt {attempt + 1} failed, retrying...")

            control_query = f"""Control ID: {control_info.get('control_id')}
Service: {control_info.get('service_name')}
Type: {control_info.get('control_type')}
Description: {control_info.get('description', 'N/A')}
Additional Data: {json.dumps(control_data) if control_data else 'N/A'}

{"Use MCP tools to research AWS documentation." if aws_tools else ""}"""

            tasks = [
                asyncio.to_thread(run_agent_with_retry, agent1, control_query, "Agent1"),
                asyncio.to_thread(run_agent_with_retry, agent2, control_query, "Agent2"),
                asyncio.to_thread(run_agent_with_retry, agent3, control_query, "Agent3"),
                asyncio.to_thread(run_agent_with_retry, agent4, control_query, "Agent4"),
            ]

            agent1_result, agent2_result, agent3_result, agent4_result = await asyncio.gather(
                *tasks
            )

            master_query = f"""ORIGINAL CONTROL:
{json.dumps(control_info, indent=2)}

AGENT 1 OUTPUT:
{agent1_result}

AGENT 2 OUTPUT:
{agent2_result}

AGENT 3 OUTPUT:
{agent3_result}

AGENT 4 OUTPUT:
{agent4_result}

Validate consistency and produce final JSON."""

            master_response = run_agent_with_retry(master_agent, master_query, "MasterAgent")

            result = {
                "enriched_interpretation": str(master_response),
                "agent_outputs": {
                    "agent1_purpose": str(agent1_result),
                    "agent2_resources": str(agent2_result),
                    "agent3_services": str(agent3_result),
                    "agent4_security": str(agent4_result),
                },
                "status": "success",
                "timestamp": datetime.now().isoformat(),
            }

            if self.aws_profile:
                result["aws_profile_applied"] = {
                    "service_name": self.service_name,
                    "enrichment_philosophy": self.enrichment_guidance.get(
                        "enrichment_philosophy"
                    ),
                    "primary_focus": self.pattern_analysis.get(
                        "control_characteristics", {}
                    ).get("primary_focus"),
                }

            return result

        except Exception as e:
            error_msg = f"AWS enrichment failed for {control_id}: {str(e)}"
            logger.error(error_msg)
            return {
                "enriched_interpretation": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat(),
            }
