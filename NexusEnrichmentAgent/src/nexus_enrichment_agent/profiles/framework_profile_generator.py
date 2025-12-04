"""
Dynamic Framework Profile Generator
Interprets framework language style and generates adaptive guidance for AWS control mapping.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from strands import Agent
from strands.models import BedrockModel
from boto3 import Session

from nexus_enrichment_agent.utils.config import load_session_params
from nexus_enrichment_agent.utils.logger import get_callback_handler, get_session_timestamp

logger = logging.getLogger(__name__)


class DynamicFrameworkProfileGenerator:
    """
    Analyzes framework language and generates field-specific agent instructions.
    """

    AGENT_DEFINITIONS = {
        "agent1": {
            "name": "Control Objective & Classification",
            "base_prompt": """Extract control objective and evidence-based classification from control text.

OUTPUT JSON:
{
  "primary_objective": "Single sentence objective from control text",
  "technical_scope": "Explicit technical boundaries mentioned",
  "compliance_scope": "Explicit compliance requirements",
  "primary_category": "Category based on control text",
  "evidence_quote": "Exact quote supporting classification"
}

Use ONLY explicit text from the control. Return valid JSON only.""",
            "output_fields": [
                "primary_objective",
                "technical_scope",
                "compliance_scope",
                "primary_category",
                "evidence_quote",
            ],
        },
        "agent2": {
            "name": "Technical/Hybrid/Non-Technical Filter",
            "base_prompt": """Classify control implementation type.

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
            "output_fields": [
                "implementation_type",
                "technical_components",
                "non_technical_components",
                "aws_mappable",
                "filter_reasoning",
            ],
        },
        "agent3": {
            "name": "Primary Services & Tier 1 Implementation",
            "base_prompt": """Identify PRIMARY AWS services for control implementation. NO supporting services.

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
            "output_fields": ["primary_services", "tier1_implementation", "resource_scope"],
        },
        "agent4": {
            "name": "Security Impact Analysis",
            "base_prompt": """Analyze security impact, threat model, and technical implementation.

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
            "output_fields": [
                "explicit_threats",
                "security_impact",
                "technical_implementation",
                "detection_method",
                "remediation_steps",
            ],
        },
        "agent5": {
            "name": "Validation Requirements",
            "base_prompt": """Extract validation requirements and assessment methods.

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
            "output_fields": [
                "validation_criteria",
                "assessment_methods",
                "compliance_evidence",
            ],
        },
    }

    def __init__(
        self,
        framework_name: str = None,
        s3_path: str = None,
        model: str = None,
        session_params: Dict = None,
    ):
        if s3_path:
            self.framework_name = s3_path.rstrip("/").split("/")[-1]
            self.s3_path = s3_path
        elif framework_name:
            self.framework_name = framework_name
            self.s3_path = None
        else:
            raise ValueError("Either framework_name or s3_path must be provided")

        self.model_id = model or "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
        self.sample_size = 10
        self.session_params = session_params

        # Load Bedrock session for model
        bedrock_session_params = session_params or load_session_params(bedrock_only=True)
        bedrock_session = Session(**bedrock_session_params) if bedrock_session_params else Session()

        self.bedrock_model = BedrockModel(
            model_id=self.model_id,
            boto_session=bedrock_session,
            temperature=0,
            timeout=300,
        )

        # Load S3 session with full permissions
        s3_session_params = session_params or load_session_params(bedrock_only=False)
        s3_session = Session(**s3_session_params) if s3_session_params else Session()
        self.s3_client = s3_session.client("s3")

    def load_controls_from_s3(self, num_controls: int = 5) -> List[Dict]:
        """Load controls from S3 path."""
        if not self.s3_path:
            raise ValueError("S3 path not provided")

        if not self.s3_path.startswith("s3://"):
            raise ValueError("S3 path must start with s3://")

        path_parts = self.s3_path.replace("s3://", "").split("/", 1)
        bucket = path_parts[0]
        prefix = path_parts[1] if len(path_parts) > 1 else ""

        if not prefix.endswith("/"):
            prefix += "/"
        key = f"{prefix}framework.json"

        logger.info(f"Loading controls from s3://{bucket}/{key}")

        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            controls = json.loads(response["Body"].read().decode("utf-8"))
            selected_controls = controls[:num_controls]
            logger.info(f"Loaded {len(selected_controls)} controls from S3")
            return selected_controls
        except Exception as e:
            logger.error(f"Failed to load controls from S3: {e}")
            raise

    async def generate_profile(
        self, sample_controls: List[Dict] = None, num_controls: int = 5
    ) -> Dict[str, Any]:
        """
        Analyze sample controls to generate framework profile for control interpretation.

        Args:
            sample_controls: List of 3-10 representative controls from the framework
            num_controls: Number of controls to load from S3 if sample_controls not provided

        Returns:
            Framework profile with interpretation guidance for embedding enrichment
        """
        if sample_controls is None:
            if not self.s3_path:
                raise ValueError("Either sample_controls or s3_path must be provided")
            sample_controls = self.load_controls_from_s3(num_controls)

        if len(sample_controls) < 3:
            raise ValueError("Need at least 3 sample controls for reliable profiling")

        logger.info(
            f"Generating profile for {self.framework_name} using {len(sample_controls)} controls"
        )

        # Step 1: Analyze framework language and control patterns
        language_analysis = await self._analyze_framework_language(sample_controls)

        # Step 2: Generate enrichment guidance for control interpretation
        enrichment_guidance = await self._generate_enrichment_guidance(
            language_analysis, sample_controls
        )

        # Step 3: Create agent instructions for control interpretation
        agent_instructions = self._create_interpretation_agent_instructions(
            language_analysis, enrichment_guidance
        )

        final_profile = {
            "framework_name": self.framework_name,
            "language_analysis": language_analysis,
            "enrichment_guidance": enrichment_guidance,
            "agent_context": agent_instructions,
            "sample_size": len(sample_controls),
            "generated_at": datetime.now().isoformat(),
        }

        logger.info(f"Profile generated for {self.framework_name}")
        return final_profile

    async def _analyze_framework_language(self, sample_controls: List[Dict]) -> Dict[str, Any]:
        """Analyze framework language patterns, vocabulary, and control structure."""
        language_agent = Agent(
            model=self.bedrock_model,
            system_prompt="""Analyze framework control language patterns.

OUTPUT JSON:
{
  "control_focus": {
    "technical_implementation": 0.0-1.0,
    "administrative_processes": 0.0-1.0,
    "governance_oversight": 0.0-1.0,
    "audit_evidence": 0.0-1.0,
    "primary_focus": "technical|administrative|governance|audit"
  },
  "control_structure": {
    "granularity": "atomic|composite|mixed",
    "clarity": "explicit|interpretive|mixed",
    "abstraction_level": "low|medium|high"
  },
  "key_characteristics": "Brief summary of framework style"
}

Return valid JSON only.""",
            callback_handler=get_callback_handler(),
            trace_attributes={
                "session.id": get_session_timestamp(),
                "agent.type": "language-analyzer",
                "agent.name": "framework-language-analysis",
            },
        )

        controls_summary = self._prepare_controls_summary(sample_controls)

        analysis_query = f"""Framework: {self.framework_name}

Sample Controls:
{controls_summary}

Analyze control focus, structure, and key characteristics."""

        try:
            analysis_response = language_agent(analysis_query)
            return self._parse_json_response(str(analysis_response))
        except Exception as e:
            logger.error(f"Language analysis failed: {e}")
            return self._get_default_language_analysis()

    async def _generate_enrichment_guidance(
        self, language_analysis: Dict[str, Any], sample_controls: List[Dict]
    ) -> Dict[str, Any]:
        """Generate field-specific guidance for control interpretation."""
        agent_info = []
        for agent_key, agent_def in self.AGENT_DEFINITIONS.items():
            agent_info.append(
                f"{agent_key}: {agent_def['name']} - Fields: {', '.join(agent_def['output_fields'])}"
            )

        guidance_agent = Agent(
            model=self.bedrock_model,
            system_prompt=f"""Analyze framework and generate agent-specific guidance.

AGENTS:
{chr(10).join(agent_info)}

For each agent, determine:
1. EMPHASIZE: What fields/aspects to focus on for this framework
2. SKIP_IF: When to skip/minimize output
3. FRAMEWORK_RULES: Special interpretation rules

OUTPUT JSON:
{{
  "enrichment_philosophy": "1-2 sentences on framework approach",
  "agent_guidance": [
    {{
      "agent": "agent1|agent2|agent3|agent4|agent5",
      "emphasize": "Specific fields/aspects to focus on",
      "skip_if": "Condition to skip (empty string if always include)",
      "framework_rules": "Special rules (empty string if none)"
    }}
  ]
}}

Return valid JSON only.""",
            callback_handler=get_callback_handler(),
            trace_attributes={
                "session.id": get_session_timestamp(),
                "agent.type": "enrichment-guidance",
            },
        )

        controls_summary = self._prepare_controls_summary(sample_controls)

        guidance_query = f"""Framework: {self.framework_name}

Language Analysis:
{json.dumps(language_analysis, indent=2)}

Sample Controls:
{controls_summary}

Generate agent-specific guidance."""

        try:
            guidance_response = guidance_agent(guidance_query)
            return self._parse_json_response(str(guidance_response))
        except Exception as e:
            logger.error(f"Enrichment guidance failed: {e}")
            return self._get_default_enrichment_guidance()

    def _create_interpretation_agent_instructions(
        self, language_analysis: Dict[str, Any], enrichment_guidance: Dict[str, Any]
    ) -> Dict[str, str]:
        """Create framework-specific enhanced prompts for each agent."""
        agent_guidance_map = {
            g["agent"]: g for g in enrichment_guidance.get("agent_guidance", [])
        }
        philosophy = enrichment_guidance.get("enrichment_philosophy", "")

        instructions = {}

        for agent_key, agent_def in self.AGENT_DEFINITIONS.items():
            guidance = agent_guidance_map.get(agent_key, {})
            emphasize = guidance.get("emphasize", "")
            skip_if = guidance.get("skip_if", "")
            rules = guidance.get("framework_rules", "")

            context_parts = [f"FRAMEWORK: {self.framework_name}"]

            if emphasize:
                context_parts.append(f"EMPHASIZE: {emphasize}")
            if skip_if:
                context_parts.append(f"SKIP IF: {skip_if}")
            if rules:
                context_parts.append(f"RULES: {rules}")

            framework_context = "\n".join(context_parts)
            enhanced_prompt = f"{framework_context}\n\n{agent_def['base_prompt']}"
            instructions[f"{agent_key}_prompt"] = enhanced_prompt

        # Master agent prompt
        master_prompt = f"""FRAMEWORK: {self.framework_name}
{philosophy}

You are a Master Review Agent. Review and validate outputs from 5 specialized agents.

FOR EACH AGENT OUTPUT:
1. Verify accuracy against original control text
2. Identify missing or incorrect interpretations
3. Flag inconsistencies between agents
4. Apply corrections internally

IMPORTANT: If Agent 2 classifies the control as "Non-Technical", DO NOT include AWS services.

OUTPUT FORMAT:
Provide ONLY the corrected final synthesized analysis.

FINAL SYNTHESIZED ANALYSIS:
[Comprehensive control analysis with all corrections applied]

Ensure all interpretations are evidence-based and meaningful."""
        instructions["master_prompt"] = master_prompt

        return instructions

    def _prepare_controls_summary(self, controls: List[Dict]) -> str:
        """Prepare concise summary of sample controls."""
        summaries = []
        for i, control in enumerate(controls[:5], 1):
            control_id = control.get("shortId", f"C{i}")
            description = control.get("description", "")[:200]
            summaries.append(f"{control_id}: {description}...")
        return "\n".join(summaries)

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from agent response."""
        try:
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
                return json.loads(json_str)
        except Exception as e:
            logger.debug(f"JSON parsing failed: {e}")

        try:
            start = response.rfind("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except Exception as e:
            logger.debug(f"Fallback parsing failed: {e}")

        return {}

    def _get_default_language_analysis(self) -> Dict[str, Any]:
        """Return default language analysis."""
        return {
            "control_focus": {
                "technical_implementation": 0.5,
                "administrative_processes": 0.5,
                "governance_oversight": 0.5,
                "audit_evidence": 0.5,
                "primary_focus": "mixed",
            },
            "control_structure": {
                "granularity": "mixed",
                "clarity": "mixed",
                "abstraction_level": "medium",
            },
            "key_characteristics": "Balanced framework",
        }

    def _get_default_enrichment_guidance(self) -> Dict[str, Any]:
        """Return default enrichment guidance."""
        return {
            "enrichment_philosophy": "Extract control characteristics for semantic enrichment.",
            "agent_guidance": [
                {
                    "agent": "agent1",
                    "emphasize": "Control objective and scope",
                    "skip_if": "",
                    "framework_rules": "",
                },
                {
                    "agent": "agent2",
                    "emphasize": "Technical and administrative classification",
                    "skip_if": "",
                    "framework_rules": "",
                },
                {
                    "agent": "agent3",
                    "emphasize": "AWS service mapping",
                    "skip_if": "Control is Non-Technical",
                    "framework_rules": "",
                },
                {
                    "agent": "agent4",
                    "emphasize": "Security impact",
                    "skip_if": "",
                    "framework_rules": "",
                },
                {
                    "agent": "agent5",
                    "emphasize": "Validation criteria",
                    "skip_if": "No explicit validation requirements",
                    "framework_rules": "",
                },
            ],
        }
