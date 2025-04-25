def create_analysis_prompt(system_name: str, app_input: str) -> str:
    """Create a prompt for security analysis that focuses on the specific input"""
    return f"""
Act as a Senior Security Architect analyzing security architecture patterns and their implications. Your task is to:

1. First, understand the current security architecture:
   - What security boundaries exist?
   - How is trust established and verified?
   - What security properties are being maintained?

2. Then analyze proposed architectural changes:
   - How do they affect existing security boundaries?
   - What security properties are preserved or modified?
   - What trust assumptions are being made?

3. Consider the security model:
   - How is the trust model affected?
   - What security invariants must be maintained?
   - What security properties could be compromised?

IMPORTANT FOR SECURITY RATIONALE:
- DO explain why an approach maintains or impacts security boundaries
- DO analyze how trust relationships and verification points are affected
- DO examine security properties that are preserved or changed
- DO evaluate the validity of security assumptions
- DO assess impact on the system's security model

DO NOT in security_rationale:
- Do not describe implementation steps
- Do not compare specific tools or products
- Do not list generic security risks
- Do not provide configuration details
- Do not focus on operational procedures

Provide the assessment in valid JSON format exactly matching this structure:
{{
    "solutions": [
        {{
            "name": "string",
            "approach": "string",
            "technical_components": {{
                "identity_provider": ["string"],
                "network_architecture": ["string"],
                "security_rationale": "string"
            }},
            "implementation_complexity": "High/Medium/Low",
            "security_posture_score": "number"
        }}
    ],
    "recommendation": {{
        "selected_solution": "string",
        "technical_reasons": ["string"],
        "implementation_steps": ["string"]
    }}
}}

Important for security_rationale field:
- Explain WHY the architecture maintains or changes security properties
- Analyze how existing security boundaries and trust relationships are affected
- Evaluate the security assumptions being made
- Assess impact on the overall security model
- Keep focus on architectural security implications, not implementation details

SYSTEM NAME: {system_name}
SYSTEM DESCRIPTION:
{app_input}
"""