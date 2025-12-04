"""Prompt templates for reasoning generation."""

from typing import Dict, Any, List


def build_mapping_rationale_prompt(
    source_control_id: str,
    source_text: str,
    target_control_id: str,
    target_framework: str,
    target_text: str,
    similarity_score: float,
    rerank_score: float,
) -> str:
    """
    Build reasoning prompt for a single control mapping.

    Args:
        source_control_id: AWS control identifier
        source_text: AWS control description
        target_control_id: Framework control identifier
        target_framework: Target framework name (e.g., NIST, SOC-2)
        target_text: Framework control description
        similarity_score: Semantic similarity score (0.0-1.0)
        rerank_score: Reranker relevance score (0.0-1.0)

    Returns:
        Formatted prompt string
    """
    return f"""You are a compliance expert explaining why an AWS control maps to a {target_framework} framework control.

AWS Control ({source_control_id}):
{source_text}

{target_framework} Control ({target_control_id}):
{target_text}

Model Scores:
- Semantic Similarity: {similarity_score:.2f}
- Relevance Score: {rerank_score:.2f}

Provide a concise 2-3 sentence explanation of:
1. Why these controls are related
2. What security objective they share
3. Any gaps or partial coverage to note

Be specific. Reference actual control requirements. Output only the reasoning text."""


def build_batch_reasoning_prompt(
    source_control_id: str,
    source_text: str,
    mappings: List[Dict[str, Any]],
) -> str:
    """
    Build reasoning prompt for multiple control mappings.

    Args:
        source_control_id: AWS control identifier
        source_text: AWS control description
        mappings: List of mapping dicts with target info

    Returns:
        Formatted prompt string for batch reasoning
    """
    mappings_text = []
    for i, mapping in enumerate(mappings, 1):
        target_id = mapping["target_control_id"]
        target_framework = mapping["target_framework"]
        target_text = mapping.get("text", "")
        similarity = mapping.get("similarity_score", 0.0)
        rerank = mapping.get("rerank_score", 0.0)

        mappings_text.append(f"""
Mapping {i}: {target_framework} Control ({target_id})
{target_text}
Scores: Similarity={similarity:.2f}, Relevance={rerank:.2f}
""")

    return f"""You are a compliance expert explaining why an AWS control maps to multiple framework controls.

AWS Control ({source_control_id}):
{source_text}

Target Mappings:
{"".join(mappings_text)}

For EACH mapping, provide a concise 2-3 sentence explanation of:
1. Why these controls are related
2. What security objective they share
3. Any gaps or partial coverage to note

Format your response as:
[Control ID]: Reasoning text

Be specific. Reference actual control requirements."""


def build_gap_analysis_prompt(
    source_control_id: str,
    source_text: str,
    target_framework: str,
    mappings: List[Dict[str, Any]],
) -> str:
    """
    Build prompt for gap analysis between AWS control and framework.

    Args:
        source_control_id: AWS control identifier
        source_text: AWS control description
        target_framework: Target framework name
        mappings: List of potential mappings

    Returns:
        Formatted prompt for gap analysis
    """
    mappings_summary = []
    for mapping in mappings:
        target_id = mapping["target_control_id"]
        target_text = mapping.get("text", "")[:200]
        mappings_summary.append(f"- {target_id}: {target_text}...")

    return f"""Analyze the coverage of this AWS control within {target_framework}.

AWS Control ({source_control_id}):
{source_text}

Potential {target_framework} Mappings:
{chr(10).join(mappings_summary)}

Provide:
1. COVERAGE SUMMARY: What aspects of the AWS control are covered by these mappings?
2. GAPS: What requirements in the AWS control are NOT covered by any mapping?
3. RECOMMENDATIONS: What additional framework controls might be relevant?

Be specific and cite control requirements."""


def build_comparison_prompt(
    control_a_id: str,
    control_a_text: str,
    control_a_framework: str,
    control_b_id: str,
    control_b_text: str,
    control_b_framework: str,
) -> str:
    """
    Build prompt for comparing two controls.

    Args:
        control_a_id: First control identifier
        control_a_text: First control description
        control_a_framework: First control's framework
        control_b_id: Second control identifier
        control_b_text: Second control description
        control_b_framework: Second control's framework

    Returns:
        Formatted prompt for control comparison
    """
    return f"""Compare these two security controls:

{control_a_framework} Control ({control_a_id}):
{control_a_text}

{control_b_framework} Control ({control_b_id}):
{control_b_text}

Analyze:
1. OVERLAP: What requirements do both controls share?
2. UNIQUE TO {control_a_id}: What does this control require that the other doesn't?
3. UNIQUE TO {control_b_id}: What does this control require that the other doesn't?
4. RELATIONSHIP: Is this a full match, partial match, or complementary relationship?

Be specific and reference actual requirements."""
