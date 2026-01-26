"""Discovery Prep Agents.

This module contains agents for generating pre-call preparation content:
- Question Agent: Generates 3 optimized questions from project gaps
- Document Agent: Recommends 3 documents based on project context
- Agenda Agent: Creates cohesive call agenda incorporating questions
"""

from app.agents.discovery_prep.question_agent import generate_prep_questions
from app.agents.discovery_prep.document_agent import recommend_documents
from app.agents.discovery_prep.agenda_agent import generate_agenda

__all__ = ["generate_prep_questions", "recommend_documents", "generate_agenda"]
