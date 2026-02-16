"""LLM chain for extracting stakeholders from signals.

Identifies people mentioned in transcripts, emails, and documents,
extracting their roles, expertise areas, and how they were identified.
"""

import json
from uuid import UUID

from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.stakeholders import create_stakeholder_from_signal, update_topic_mentions

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are an expert at identifying individual people (stakeholders) from business communications.

Analyze the provided content and extract ALL individual PEOPLE mentioned. For each person, determine:

1. **name**: Full name if available, or best identifier (e.g., "Jim from Finance")
2. **role**: Job title, function, or department (e.g., "CFO", "Product Manager", "Dev Lead")
3. **email**: Email address if visible in content
4. **domain_expertise**: Inferred areas of expertise based on what they discuss or their role
   - Examples: ["finance", "security", "ux", "engineering", "sales", "compliance", "product"]
5. **source_type**: How they appear in this content
   - "direct_participant": They wrote/sent this email OR they are speaking in this transcript
   - "mentioned": They are referenced by someone else (e.g., "Jim said that...")
6. **topics_discussed**: What topics/subjects did they discuss or get mentioned in relation to?

CRITICAL RULES:
- ONLY extract individual people — NEVER organizations, companies, departments, or teams
- WRONG: "Stardust Building Supplies" — this is a company name, NOT a stakeholder
- WRONG: "The Finance Team" — this is a department, NOT a stakeholder
- RIGHT: "Susan Cordts" — this is an individual person
- RIGHT: "Jim from Finance" — this is an individual person (partial name is OK)
- If no individual people are named in the content, return an empty stakeholders array
- Extract ALL people, even those mentioned briefly
- For transcripts: speakers are "direct_participant", people they reference are "mentioned"
- For emails: sender/recipients are "direct_participant", people referenced in body are "mentioned"
- Infer expertise from context (a person discussing SSO setup likely has "security" or "IT" expertise)
- Be generous with topics_discussed - capture all subjects they're connected to

Output valid JSON object with a "stakeholders" key containing an array:
{
  "stakeholders": [
    {
      "name": "string",
      "role": "string or null",
      "email": "string or null",
      "domain_expertise": ["string"],
      "source_type": "direct_participant" | "mentioned",
      "topics_discussed": ["string"]
    }
  ]
}
"""


async def extract_stakeholders_from_signal(
    project_id: UUID,
    signal_id: UUID,
    content: str,
    source_type: str,
    metadata: dict | None = None,
) -> list[dict]:
    """
    Extract stakeholders from signal content.

    Args:
        project_id: Project UUID
        signal_id: Signal UUID (for provenance tracking)
        content: Signal content (transcript, email body, document text)
        source_type: Type of signal (transcript, email, document)
        metadata: Optional metadata (e.g., email sender, recipients)

    Returns:
        List of created/updated stakeholder dicts
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    try:
        # Build context for extraction
        context_parts = [f"Content type: {source_type}"]

        # Add metadata context if available
        if metadata:
            if metadata.get("sender"):
                context_parts.append(f"Email sender: {metadata['sender']}")
            if metadata.get("recipients"):
                context_parts.append(f"Email recipients: {', '.join(metadata['recipients'])}")
            if metadata.get("speakers"):
                context_parts.append(f"Transcript speakers: {', '.join(metadata['speakers'])}")

        context = "\n".join(context_parts)

        user_prompt = f"""{context}

Content to analyze:
---
{content[:15000]}
---

Extract all stakeholders mentioned in this content."""

        response = client.chat.completions.create(
            model=settings.FACTS_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        raw_output = response.choices[0].message.content
        logger.debug(f"Stakeholder extraction raw output: {raw_output[:500]}")

        # Parse response - handle both array and object with array
        try:
            parsed = json.loads(raw_output)
            if isinstance(parsed, list):
                extracted = parsed
                logger.debug(f"Parsed as array with {len(extracted)} items")
            elif isinstance(parsed, dict) and "stakeholders" in parsed:
                extracted = parsed["stakeholders"]
                logger.debug(f"Parsed from 'stakeholders' key with {len(extracted)} items")
            else:
                # Try to find any array in the response
                logger.debug(f"Looking for array in dict keys: {list(parsed.keys())}")
                for key, value in parsed.items():
                    if isinstance(value, list):
                        extracted = value
                        logger.debug(f"Found array in key '{key}' with {len(extracted)} items")
                        break
                else:
                    logger.warning(f"No array found in parsed response: {list(parsed.keys())}")
                    extracted = []
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse stakeholder extraction response: {e} - {raw_output[:200]}")
            extracted = []

        logger.info(
            f"Extracted {len(extracted)} stakeholders from signal {signal_id}",
            extra={"project_id": str(project_id), "signal_id": str(signal_id)},
        )

        # Create/update stakeholders in database
        created_stakeholders = []
        for sh in extracted:
            try:
                # Skip if not a dict (e.g., LLM returned strings)
                if not isinstance(sh, dict):
                    logger.warning(f"Skipping non-dict stakeholder entry: {type(sh)}")
                    continue

                name = sh.get("name")
                if not name or len(str(name).strip()) < 2:
                    continue

                # Determine if direct participant
                is_direct = sh.get("source_type") == "direct_participant"

                stakeholder = create_stakeholder_from_signal(
                    project_id=project_id,
                    name=name.strip(),
                    role=sh.get("role"),
                    email=sh.get("email"),
                    domain_expertise=sh.get("domain_expertise", []),
                    source_type=sh.get("source_type", "mentioned"),
                    extracted_from_signal_id=signal_id,
                    is_direct_participant=is_direct,
                )

                # Update topic mentions
                topics = sh.get("topics_discussed", [])
                if topics:
                    stakeholder = update_topic_mentions(
                        UUID(stakeholder["id"]),
                        topics,
                    )

                created_stakeholders.append(stakeholder)

            except Exception as e:
                logger.warning(f"Failed to create stakeholder {sh.get('name')}: {e}")
                continue

        return created_stakeholders

    except Exception as e:
        logger.error(
            f"Error extracting stakeholders from signal {signal_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id), "signal_id": str(signal_id)},
        )
        return []


def identify_speakers_from_transcript(transcript: str) -> list[str]:
    """
    Quick extraction of speaker names from transcript format.

    Handles common formats:
    - "Speaker Name: text"
    - "[Speaker Name] text"
    - "SPEAKER NAME: text"

    Args:
        transcript: Transcript text

    Returns:
        List of unique speaker names
    """
    import re

    speakers = set()

    # Pattern: "Name: " at start of line or after newline
    pattern1 = r'^([A-Z][a-zA-Z\s]+?):\s'
    for match in re.finditer(pattern1, transcript, re.MULTILINE):
        name = match.group(1).strip()
        if len(name) > 1 and len(name) < 50:
            speakers.add(name)

    # Pattern: "[Name]" at start of line
    pattern2 = r'^\[([^\]]+)\]'
    for match in re.finditer(pattern2, transcript, re.MULTILINE):
        name = match.group(1).strip()
        if len(name) > 1 and len(name) < 50:
            speakers.add(name)

    return list(speakers)


def extract_email_participants(
    sender: str | None,
    recipients: list[str] | None,
    cc: list[str] | None = None,
) -> list[dict]:
    """
    Extract participant info from email metadata.

    Args:
        sender: Email sender (name or email)
        recipients: List of recipients
        cc: Optional CC list

    Returns:
        List of participant dicts with source_type
    """
    participants = []

    if sender:
        participants.append({
            "identifier": sender,
            "source_type": "direct_participant",
            "role_hint": "sender",
        })

    for recipient in recipients or []:
        participants.append({
            "identifier": recipient,
            "source_type": "direct_participant",
            "role_hint": "recipient",
        })

    for cc_recipient in cc or []:
        participants.append({
            "identifier": cc_recipient,
            "source_type": "direct_participant",
            "role_hint": "cc",
        })

    return participants
