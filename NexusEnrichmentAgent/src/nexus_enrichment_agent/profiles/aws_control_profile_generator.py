"""
AWS Control Profile Generator
Analyzes AWS control patterns and generates adaptive guidance for enrichment agents.
"""

import json
import logging
from typing import Dict, List, Any
from datetime import datetime

from strands import Agent
from strands.models import BedrockModel
from boto3 import Session

from nexus_enrichment_agent.utils.config import load_session_params
from nexus_enrichment_agent.utils.logger import get_callback_handler, get_session_timestamp

logger = logging.getLogger(__name__)


class AWSControlProfileGenerator:
    """Analyzes AWS control patterns and generates agent-specific guidance."""

    AGENT_DEFINITIONS = {
        "agent1": {
            "name": "Control Purpose & Detection",
            "base_prompt": """Extract control purpose and detection method.

OUTPUT JSON:
{
  "control_purpose": "What the control checks/enforces",
  "detection_method": "How non-compliance is detected",
  "compliance_criteria": "Specific criteria for compliance"
}

Return valid JSON only.""",
            "output_fields": ["control_purpose", "detection_method", "compliance_criteria"],
        },
        "agent2": {
            "name": "Resource Scope",
            "base_prompt": """Identify AWS resources and parameters.

OUTPUT JSON:
{
  "resource_types": ["AWS::Service::ResourceType"],
  "parameters_checked": ["parameter1", "parameter2"],
  "resource_attributes": ["attribute1", "attribute2"]
}

Return valid JSON only.""",
            "output_fields": ["resource_types", "parameters_checked", "resource_attributes"],
        },
        "agent3": {
            "name": "Service Implementation",
            "base_prompt": """Identify primary AWS services (max 2-3).

OUTPUT JSON:
{
  "primary_services": ["Service1", "Service2"],
  "service_capabilities": ["capability1", "capability2"],
  "implementation_approach": "Brief description"
}

Return valid JSON only.""",
            "output_fields": [
                "primary_services",
                "service_capabilities",
                "implementation_approach",
            ],
        },
        "agent4": {
            "name": "Security Domain",
            "base_prompt": """Map to security domains and actions.

OUTPUT JSON:
{
  "security_domains": ["Domain1"],
  "technical_actions": ["action1"],
  "security_impact": "Risk prevention",
  "threat_mitigation": "Threats addressed"
}

Return valid JSON only.""",
            "output_fields": [
                "security_domains",
                "technical_actions",
                "security_impact",
                "threat_mitigation",
            ],
        },
    }

    def __init__(
        self,
        service_name: str = None,
        model: str = None,
        session_params: Dict = None,
    ):
        self.service_name = service_name or "AWS"
        self.model_id = model or "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
        self.sample_size = 10
        self.session_params = session_params

        # Load session and create Bedrock model
        bedrock_session_params = session_params or load_session_params(bedrock_only=True)
        boto_session = Session(**bedrock_session_params) if bedrock_session_params else Session()

        self.bedrock_model = BedrockModel(
            model_id=self.model_id,
            boto_session=boto_session,
            temperature=0,
            timeout=300,
        )

    async def generate_profile(self, sample_controls: List[Dict]) -> Dict[str, Any]:
        """Generate AWS control profile from sample controls."""
        if len(sample_controls) < 5:
            raise ValueError("Need at least 5 sample controls for reliable profiling")

        logger.info(
            f"Generating AWS profile for {self.service_name} using {len(sample_controls)} controls"
        )

        pattern_analysis = await self._analyze_control_patterns(sample_controls)
        enrichment_guidance = await self._generate_enrichment_guidance(
            pattern_analysis, sample_controls
        )
        agent_instructions = self._create_agent_instructions(
            pattern_analysis, enrichment_guidance
        )

        profile = {
            "service_name": self.service_name,
            "pattern_analysis": pattern_analysis,
            "enrichment_guidance": enrichment_guidance,
            "agent_context": agent_instructions,
            "sample_size": len(sample_controls),
            "generated_at": datetime.now().isoformat(),
        }

        logger.info(f"AWS profile generated for {self.service_name}")
        return profile

    async def _analyze_control_patterns(self, sample_controls: List[Dict]) -> Dict[str, Any]:
        """Analyze AWS control patterns."""
        agent = Agent(
            model=self.bedrock_model,
            system_prompt="""Analyze AWS control patterns.

OUTPUT JSON:
{
  "control_characteristics": {
    "resource_focused": 0.0-1.0,
    "configuration_focused": 0.0-1.0,
    "security_focused": 0.0-1.0,
    "primary_focus": "resource|configuration|security"
  },
  "control_complexity": {
    "granularity": "simple|moderate|complex",
    "technical_depth": "low|medium|high"
  },
  "key_patterns": "Brief summary"
}

Return valid JSON only.""",
            callback_handler=get_callback_handler(),
            trace_attributes={
                "session.id": get_session_timestamp(),
                "agent.type": "pattern-analyzer",
            },
        )

        controls_summary = self._prepare_controls_summary(sample_controls)
        query = f"Service: {self.service_name}\n\nSample Controls:\n{controls_summary}\n\nAnalyze patterns."

        try:
            response = agent(query)
            return self._parse_json_response(str(response))
        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
            return self._get_default_pattern_analysis()

    async def _generate_enrichment_guidance(
        self, pattern_analysis: Dict, sample_controls: List[Dict]
    ) -> Dict[str, Any]:
        """Generate agent-specific guidance."""
        agent_info = [f"{k}: {v['name']}" for k, v in self.AGENT_DEFINITIONS.items()]

        agent = Agent(
            model=self.bedrock_model,
            system_prompt=f"""Generate agent guidance for AWS controls.

AGENTS: {', '.join(agent_info)}

OUTPUT JSON:
{{
  "enrichment_philosophy": "Overall approach",
  "agent_guidance": [
    {{
      "agent": "agent1|agent2|agent3|agent4",
      "emphasize": "What to focus on",
      "skip_if": "When to skip",
      "aws_rules": "AWS-specific rules"
    }}
  ]
}}

Return valid JSON only.""",
            callback_handler=get_callback_handler(),
            trace_attributes={
                "session.id": get_session_timestamp(),
                "agent.type": "guidance-generator",
            },
        )

        controls_summary = self._prepare_controls_summary(sample_controls)
        query = f"""Service: {self.service_name}

Pattern Analysis:
{json.dumps(pattern_analysis, indent=2)}

Sample Controls:
{controls_summary}

Generate guidance."""

        try:
            response = agent(query)
            return self._parse_json_response(str(response))
        except Exception as e:
            logger.error(f"Guidance generation failed: {e}")
            return self._get_default_enrichment_guidance()

    def _create_agent_instructions(
        self, pattern_analysis: Dict, enrichment_guidance: Dict
    ) -> Dict[str, str]:
        """Create enhanced prompts for each agent."""
        agent_guidance_map = {
            g["agent"]: g for g in enrichment_guidance.get("agent_guidance", [])
        }
        instructions = {}

        for agent_key, agent_def in self.AGENT_DEFINITIONS.items():
            guidance = agent_guidance_map.get(agent_key, {})
            parts = [f"SERVICE: {self.service_name}"]

            if guidance.get("emphasize"):
                parts.append(f"EMPHASIZE: {guidance['emphasize']}")
            if guidance.get("skip_if"):
                parts.append(f"SKIP IF: {guidance['skip_if']}")
            if guidance.get("aws_rules"):
                parts.append(f"RULES: {guidance['aws_rules']}")

            enhanced_prompt = f"{chr(10).join(parts)}\n\n{agent_def['base_prompt']}"
            instructions[f"{agent_key}_prompt"] = enhanced_prompt

        philosophy = enrichment_guidance.get("enrichment_philosophy", "")
        master_prompt = f"""SERVICE: {self.service_name}
{philosophy}

Master Integration Agent: Merge specialist outputs into concise analysis.

RULES:
1. Keep primary_services to 2-3 services max
2. Validate consistency across agents
3. Remove redundancies
4. Be specific to the control

Return consolidated JSON only."""
        instructions["master_prompt"] = master_prompt

        return instructions

    def _prepare_controls_summary(self, controls: List[Dict]) -> str:
        """Prepare control summary."""
        summaries = []
        for i, control in enumerate(controls[:7], 1):
            control_id = control.get("id", control.get("name", f"C{i}"))
            description = control.get("description", "")[:150]
            summaries.append(f"{control_id}: {description}...")
        return "\n".join(summaries)

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from response."""
        try:
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                return json.loads(response[json_start:json_end].strip())
        except Exception:
            pass

        try:
            start = response.rfind("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except Exception:
            pass

        return {}

    def _get_default_pattern_analysis(self) -> Dict[str, Any]:
        """Default pattern analysis."""
        return {
            "control_characteristics": {
                "resource_focused": 0.5,
                "configuration_focused": 0.5,
                "security_focused": 0.5,
                "primary_focus": "mixed",
            },
            "control_complexity": {
                "granularity": "moderate",
                "technical_depth": "medium",
            },
            "key_patterns": "Balanced AWS controls",
        }

    def _get_default_enrichment_guidance(self) -> Dict[str, Any]:
        """Default enrichment guidance."""
        return {
            "enrichment_philosophy": "Extract AWS control characteristics for enrichment.",
            "agent_guidance": [
                {
                    "agent": "agent1",
                    "emphasize": "Control purpose",
                    "skip_if": "",
                    "aws_rules": "",
                },
                {
                    "agent": "agent2",
                    "emphasize": "Resource types",
                    "skip_if": "",
                    "aws_rules": "",
                },
                {
                    "agent": "agent3",
                    "emphasize": "Primary services",
                    "skip_if": "",
                    "aws_rules": "",
                },
                {
                    "agent": "agent4",
                    "emphasize": "Security domains",
                    "skip_if": "",
                    "aws_rules": "",
                },
            ],
        }
