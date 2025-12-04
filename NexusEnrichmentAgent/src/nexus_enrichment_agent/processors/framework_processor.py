"""
Profile-Driven Multi-Agent Framework Control Enrichment System
Embeds framework profile as additional context for specialized agents.
"""

import json
import logging
import asyncio
from typing import Dict, Any

from boto3 import Session
from strands import Agent
from strands.models import BedrockModel

from nexus_enrichment_agent.utils.config import load_session_params
from nexus_enrichment_agent.utils.logger import get_callback_handler, get_session_timestamp

logger = logging.getLogger(__name__)


class ProfileDrivenMultiAgentProcessor:
    """Framework processor using profile-enhanced specialized agents."""

    def __init__(
        self,
        framework_name: str,
        framework_profile: Dict[str, Any] = None,
        model: str = None,
        session_params: Dict = None,
    ):
        self.framework_name = framework_name
        self.framework_profile = framework_profile or {}
        self.session_params = session_params

        self.model_id = model or "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
        self.temperature = 0

        # Extract profile components
        self.agent_context = self.framework_profile.get("agent_context", {})
        self.enrichment_guidance = self.framework_profile.get("enrichment_guidance", {})
        self.language_analysis = self.framework_profile.get("language_analysis", {})

    def get_bedrock_model(self) -> BedrockModel:
        """Get a Bedrock model instance."""
        bedrock_session_params = self.session_params or load_session_params(bedrock_only=True)
        return BedrockModel(
            boto_session=Session(**bedrock_session_params) if bedrock_session_params else Session(),
            model_id=self.model_id,
            temperature=self.temperature,
        )

    def _build_framework_context(self) -> str:
        """Build framework context header."""
        if not self.framework_profile:
            return ""

        parts = [f"FRAMEWORK: {self.framework_name}"]

        if self.language_analysis:
            focus = self.language_analysis.get("control_focus", {})
            structure = self.language_analysis.get("control_structure", {})
            parts.append(f"PRIMARY FOCUS: {focus.get('primary_focus', 'N/A')}")
            parts.append(f"ABSTRACTION: {structure.get('abstraction_level', 'N/A')}")

        philosophy = self.enrichment_guidance.get("enrichment_philosophy", "")
        if philosophy:
            parts.append(f"\nGUIDANCE: {philosophy}")

        return "\n".join(parts)

    def _get_agent_prompt(self, agent_key: str, default_prompt: str) -> str:
        """Get framework-enhanced prompt for agent."""
        agent_guidance = None
        for guidance in self.enrichment_guidance.get("agent_guidance", []):
            if guidance.get("agent") == agent_key:
                agent_guidance = guidance
                break

        parts = []

        framework_context = self._build_framework_context()
        if framework_context:
            parts.append(framework_context)

        if agent_guidance:
            if agent_guidance.get("emphasize"):
                parts.append(f"\nEMPHASIZE: {agent_guidance['emphasize']}")
            if agent_guidance.get("skip_if"):
                parts.append(f"SKIP IF: {agent_guidance['skip_if']}")
            if agent_guidance.get("framework_rules"):
                parts.append(f"RULES: {agent_guidance['framework_rules']}")

        parts.append(f"\n{default_prompt}")

        if len(parts) == 1:
            return default_prompt

        return "\n".join(parts)

    def interpret_control_intent(self, metadata: Dict, control: Dict) -> Dict[str, Any]:
        """Process control using 5 profile-enhanced specialized agents."""
        control_id = control.get("shortId", "unknown")

        try:
            # Build agent prompts
            agent1_prompt = self._get_agent_prompt(
                "agent1",
                """Extract control objective and evidence-based classification from control text.

OUTPUT JSON:
{
  "primary_objective": "Single sentence objective from control text",
  "technical_scope": "Explicit technical boundaries mentioned",
  "compliance_scope": "Explicit compliance requirements",
  "primary_category": "Category based on control text",
  "evidence_quote": "Exact quote supporting classification"
}

Use ONLY explicit text from the control. Return valid JSON only.""",
            )

            agent1 = Agent(
                model=self.get_bedrock_model(),
                system_prompt=agent1_prompt,
                callback_handler=get_callback_handler(),
                trace_attributes={
                    "session.id": get_session_timestamp(),
                    "agent.type": "objective-classifier",
                    "agent.name": "agent1-objective-classifier",
                    "framework": self.framework_name,
                },
            )

            agent2_prompt = self._get_agent_prompt(
                "agent2",
                """Classify control implementation type.

OUTPUT JSON:
{
  "implementation_type": "Technical|Hybrid|Non-Technical",
  "technical_components": ["List of technical aspects"],
  "non_technical_components": ["List of administrative/physical aspects"],
  "aws_mappable": true/false,
  "filter_reasoning": "Brief explanation"
}

Technical = Fully implementable via AWS services
Hybrid = Requires both AWS services and non-technical measures
Non-Technical = Cannot be implemented through AWS services

Return valid JSON only.""",
            )

            agent2 = Agent(
                model=self.get_bedrock_model(),
                system_prompt=agent2_prompt,
                callback_handler=get_callback_handler(),
                trace_attributes={
                    "session.id": get_session_timestamp(),
                    "agent.type": "technical-filter",
                    "agent.name": "agent2-technical-filter",
                    "framework": self.framework_name,
                },
            )

            agent3_prompt = self._get_agent_prompt(
                "agent3",
                """Identify PRIMARY AWS services for control implementation. NO supporting services.

OUTPUT JSON:
{
  "primary_services": [
    {
      "service": "AWS Service Name",
      "justification": "Exact control text requiring this service",
      "required_features": ["Specific features needed"]
    }
  ],
  "tier1_implementation": "Core implementation approach",
  "resource_scope": ["Specific resources mentioned in control"]
}

Include ONLY Tier 1 primary services directly addressing control requirements.
Return valid JSON only.""",
            )

            agent3 = Agent(
                model=self.get_bedrock_model(),
                system_prompt=agent3_prompt,
                callback_handler=get_callback_handler(),
                trace_attributes={
                    "session.id": get_session_timestamp(),
                    "agent.type": "primary-services",
                    "agent.name": "agent3-primary-services",
                    "framework": self.framework_name,
                },
            )

            agent4_prompt = self._get_agent_prompt(
                "agent4",
                """Analyze security impact, threat model, and technical implementation.

OUTPUT JSON:
{
  "explicit_threats": [
    {
      "threat": "Threat mentioned in control",
      "evidence_quote": "Exact quote identifying threat",
      "attack_vector": "If explicitly described"
    }
  ],
  "security_impact": "Risk prevention based on control text",
  "technical_implementation": "Technical details from control text",
  "detection_method": "How non-compliance is detected",
  "remediation_steps": ["Steps mentioned in control"]
}

Use ONLY threats and impacts explicitly mentioned in control text.
Return valid JSON only.""",
            )

            agent4 = Agent(
                model=self.get_bedrock_model(),
                system_prompt=agent4_prompt,
                callback_handler=get_callback_handler(),
                trace_attributes={
                    "session.id": get_session_timestamp(),
                    "agent.type": "security-impact",
                    "agent.name": "agent4-security-impact",
                    "framework": self.framework_name,
                },
            )

            agent5_prompt = self._get_agent_prompt(
                "agent5",
                """Extract validation requirements and assessment methods.

OUTPUT JSON:
{
  "validation_criteria": [
    {
      "metric": "If explicitly specified",
      "threshold": "If explicitly specified",
      "method": "If explicitly specified"
    }
  ],
  "assessment_methods": [
    {
      "approach": "Examination|Interview|Test|Continuous Monitoring",
      "frequency": "If specified in control",
      "evidence_required": "Type of evidence needed"
    }
  ],
  "compliance_evidence": ["Evidence types mentioned in control"]
}

Include ONLY validation requirements explicitly stated in control text.
Return valid JSON only.""",
            )

            agent5 = Agent(
                model=self.get_bedrock_model(),
                system_prompt=agent5_prompt,
                callback_handler=get_callback_handler(),
                trace_attributes={
                    "session.id": get_session_timestamp(),
                    "agent.type": "validation-requirements",
                    "agent.name": "agent5-validation-requirements",
                    "framework": self.framework_name,
                },
            )

            master_prompt = self._get_agent_prompt(
                "master",
                """You are a Master Review Agent. Review and validate outputs from 5 specialized agents.

VALIDATION RULES:
1. Verify accuracy against original control text
2. Check consistency between Agent 2 and Agent 3:
   - If Agent 2 says "Non-Technical" → Agent 3 should have empty/minimal AWS services
   - If Agent 2 says "Technical" → Agent 3 must have AWS services
   - If Agent 2 says "Hybrid" → Agent 3 should have AWS services for technical parts
3. Remove redundant information across all agent outputs
4. Ensure all fields are evidence-based and meaningful

Combine all agent outputs into a single consolidated JSON with all fields from each agent.
Include ALL fields that agents generated. Apply corrections where needed.

Return ONLY valid JSON. No explanations or summaries.""",
            )

            master_agent = Agent(
                model=self.get_bedrock_model(),
                system_prompt=master_prompt,
                callback_handler=get_callback_handler(),
                trace_attributes={
                    "session.id": get_session_timestamp(),
                    "agent.type": "master-reviewer",
                    "agent.name": "master-agent-reviewer",
                    "framework": self.framework_name,
                },
            )

            # Execute 5 agents with retry fallback
            def run_agent_with_retry(agent, control_data, agent_name, max_retries=2):
                for attempt in range(max_retries + 1):
                    try:
                        return agent(control_data)
                    except Exception as e:
                        if attempt == max_retries:
                            logger.error(
                                f"{agent_name} failed after {max_retries + 1} attempts: {str(e)}"
                            )
                            return f"{agent_name} failed: {str(e)}"
                        logger.warning(f"{agent_name} attempt {attempt + 1} failed, retrying...")

            async def run_agents():
                control_data = f"Control: {json.dumps(control)}"
                tasks = [
                    asyncio.create_task(
                        asyncio.to_thread(run_agent_with_retry, agent1, control_data, "Agent1")
                    ),
                    asyncio.create_task(
                        asyncio.to_thread(run_agent_with_retry, agent2, control_data, "Agent2")
                    ),
                    asyncio.create_task(
                        asyncio.to_thread(run_agent_with_retry, agent3, control_data, "Agent3")
                    ),
                    asyncio.create_task(
                        asyncio.to_thread(run_agent_with_retry, agent4, control_data, "Agent4")
                    ),
                    asyncio.create_task(
                        asyncio.to_thread(run_agent_with_retry, agent5, control_data, "Agent5")
                    ),
                ]
                return await asyncio.gather(*tasks)

            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, run_agents())
                    (
                        agent1_result,
                        agent2_result,
                        agent3_result,
                        agent4_result,
                        agent5_result,
                    ) = future.result()
            except RuntimeError:
                (
                    agent1_result,
                    agent2_result,
                    agent3_result,
                    agent4_result,
                    agent5_result,
                ) = asyncio.run(run_agents())

            master_query = f"""
ORIGINAL CONTROL:
{json.dumps(control, indent=2)}

AGENT 1 OUTPUT:
{agent1_result}

AGENT 2 OUTPUT:
{agent2_result}

AGENT 3 OUTPUT:
{agent3_result}

AGENT 4 OUTPUT:
{agent4_result}

AGENT 5 OUTPUT:
{agent5_result}

Validate consistency between Agent 2 and Agent 3. Remove redundancies. Return corrected JSON only."""

            master_response = run_agent_with_retry(master_agent, master_query, "MasterAgent")

            result = {
                "enriched_interpretation": str(master_response),
                "agent_outputs": {
                    "agent1_objective_classification": str(agent1_result),
                    "agent2_technical_filter": str(agent2_result),
                    "agent3_technical_requirements": str(agent3_result),
                    "agent4_security_impact": str(agent4_result),
                    "agent5_validation_requirements": str(agent5_result),
                },
                "status": "success",
            }

            if self.framework_profile:
                result["framework_profile_applied"] = {
                    "framework_name": self.framework_name,
                    "enrichment_philosophy": self.enrichment_guidance.get(
                        "enrichment_philosophy"
                    ),
                    "primary_focus": self.language_analysis.get("control_focus", {}).get(
                        "primary_focus"
                    ),
                }

            return result

        except Exception as e:
            error_msg = f"5-agent interpretation failed for {control_id}: {str(e)}"
            logger.error(error_msg)
            return {"enriched_interpretation": error_msg, "status": "failed"}
