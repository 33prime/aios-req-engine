"""Phase 2B test fixtures for deterministic behavioral testing."""

from uuid import UUID

# Fixed deterministic IDs for repeatable tests
PROJECT_ID = UUID("97e0dc34-feb9-48ca-a3a3-ba104d9e8203")
SIGNAL_ID_1 = UUID("b76425fd-7366-4fc6-af9c-d40bc707b74c")  # Original signal
SIGNAL_ID_2 = UUID("c86425fd-7366-4fc6-af9c-d40bc707b74d")  # Contradiction signal
SIGNAL_ID_3 = UUID("d86425fd-7366-4fc6-af9c-d40bc707b74e")  # Research signal
SIGNAL_ID_4 = UUID("e86425fd-7366-4fc6-af9c-d40bc707b74f")  # Client override signal

EXTRACTED_FACTS_ID_1 = UUID("f457985d-4ecd-432a-91b8-5511ebc14e4b")
EXTRACTED_FACTS_ID_2 = UUID("f557985d-4ecd-432a-91b8-5511ebc14e4c")
EXTRACTED_FACTS_ID_3 = UUID("f657985d-4ecd-432a-91b8-5511ebc14e4d")

RUN_ID_1 = UUID("d29351d2-ca2c-4a48-9269-45aab2c6f04c")
RUN_ID_2 = UUID("d39351d2-ca2c-4a48-9269-45aab2c6f04d")
RUN_ID_3 = UUID("d49351d2-ca2c-4a48-9269-45aab2c6f04e")

JOB_ID_1 = UUID("ec8caeb6-89b2-43e3-9a9d-24f688e163c8")
JOB_ID_2 = UUID("ec9caeb6-89b2-43e3-9a9d-24f688e163c9")
JOB_ID_3 = UUID("eca0aeb6-89b2-43e3-9a9d-24f688e163ca")

# Canonical baseline snapshot for testing
CANONICAL_BASELINE = {
    "prd_sections": [
        {
            "id": str(UUID("83e93ff2-c0a1-406e-b188-0698fa14f0c3")),
            "project_id": str(PROJECT_ID),
            "slug": "happy_path",
            "label": "Happy Path",
            "required": True,
            "status": "draft",
            "fields": {"content": "The ideal user journey through the platform"},
            "client_needs": [],
            "sources": [],
            "evidence": [],
            "created_at": "2025-12-21T19:36:03.920958+00:00",
            "updated_at": "2025-12-21T19:36:03.920958+00:00"
        },
        {
            "id": str(UUID("f95cff6f-9011-43d0-af23-5ef0d86eb808")),
            "project_id": str(PROJECT_ID),
            "slug": "key_features",
            "label": "Key Features",
            "required": True,
            "status": "draft",
            "fields": {"content": "The platform will include several key features"},
            "client_needs": [],
            "sources": [],
            "evidence": [],
            "created_at": "2025-12-21T19:36:03.826012+00:00",
            "updated_at": "2025-12-21T19:36:03.826012+00:00"
        }
    ],
    "vp_steps": [
        {
            "id": str(UUID("a1b2c3d4-e5f6-4321-8765-123456789abc")),
            "project_id": str(PROJECT_ID),
            "step_index": 1,
            "label": "User Login",
            "status": "draft",
            "description": "User logs into the platform",
            "user_benefit_pain": "",
            "ui_overview": "",
            "value_created": "",
            "kpi_impact": "",
            "needed": [],
            "sources": [],
            "evidence": [],
            "created_at": "2025-12-21T19:36:03.000000+00:00",
            "updated_at": "2025-12-21T19:36:03.000000+00:00"
        }
    ],
    "features": [
        {
            "id": str(UUID("b2c3d4e5-f6a7-4321-8765-123456789abd")),
            "project_id": str(PROJECT_ID),
            "name": "In-app Document Viewer",
            "category": "UI Features",
            "is_mvp": False,  # Initially false - will be contradicted
            "confidence": "medium",
            "status": "draft",
            "evidence": [],
            "created_at": "2025-12-21T19:36:03.000000+00:00",
            "updated_at": "2025-12-21T19:36:03.000000+00:00"
        },
        {
            "id": str(UUID("c3d4e5f6-a7b8-4321-8765-123456789abe")),
            "project_id": str(PROJECT_ID),
            "name": "Secure Upload",
            "category": "Security",
            "is_mvp": True,
            "confidence": "high",
            "status": "draft",
            "evidence": [],
            "created_at": "2025-12-21T19:36:03.000000+00:00",
            "updated_at": "2025-12-21T19:36:03.000000+00:00"
        }
    ]
}

# Sample signals for testing
SAMPLE_SIGNALS = {
    str(SIGNAL_ID_1): {
        "id": str(SIGNAL_ID_1),
        "project_id": str(PROJECT_ID),
        "signal_type": "email",
        "source": "client@example.com",
        "raw_text": "Initial requirements for the platform",
        "metadata": {"authority": "client"},
        "created_at": "2025-12-21T19:30:00.000000+00:00"
    },
    str(SIGNAL_ID_2): {
        "id": str(SIGNAL_ID_2),
        "project_id": str(PROJECT_ID),
        "signal_type": "email",
        "source": "client@example.com",
        "raw_text": "UPDATE: The in-app Document Viewer is REQUIRED for MVP success. Users need to preview PDFs side-by-side with the builder.",
        "metadata": {"authority": "client", "from": "patel", "subject": "Critical MVP Update"},
        "created_at": "2025-12-21T20:30:00.000000+00:00"
    },
    str(SIGNAL_ID_3): {
        "id": str(SIGNAL_ID_3),
        "project_id": str(PROJECT_ID),
        "signal_type": "file",
        "source": "research_report.pdf",
        "raw_text": "Research shows document viewers are essential for premium perception in SaaS platforms. Include in MVP.",
        "metadata": {"authority": "research", "source": "industry_report_2024"},
        "created_at": "2025-12-21T21:00:00.000000+00:00"
    }
}

# Sample signal chunks
SAMPLE_CHUNKS = {
    str(SIGNAL_ID_2): [
        {
            "chunk_id": str(UUID("f457985d-4ecd-432a-91b8-5511ebc14e4b")),
            "signal_id": str(SIGNAL_ID_2),
            "chunk_index": 0,
            "content": "UPDATE: The in-app Document Viewer is REQUIRED for MVP success. Users need to preview PDFs side-by-side with the builder.",
            "start_char": 0,
            "end_char": 120,
            "metadata": {"authority": "client"},
            "signal_metadata": SAMPLE_SIGNALS[str(SIGNAL_ID_2)]["metadata"],
            "similarity": 0.95
        }
    ]
}

# Sample extracted facts
SAMPLE_EXTRACTED_FACTS = [
    {
        "id": str(EXTRACTED_FACTS_ID_1),
        "project_id": str(PROJECT_ID),
        "signal_id": str(SIGNAL_ID_1),
        "run_id": str(RUN_ID_1),
        "job_id": str(JOB_ID_1),
        "model": "gpt-4o-mini",
        "prompt_version": "facts_v1",
        "schema_version": "facts_v1",
        "facts": {
            "summary": "Initial requirements analysis",
            "facts": [
                {
                    "fact_type": "feature",
                    "title": "Document Viewer",
                    "detail": "In-app document viewer for PDFs",
                    "confidence": "medium",
                    "evidence": []
                }
            ],
            "open_questions": [],
            "contradictions": []
        },
        "summary": "Initial requirements analysis",
        "created_at": "2025-12-21T19:35:00.000000+00:00"
    },
    {
        "id": str(EXTRACTED_FACTS_ID_2),
        "project_id": str(PROJECT_ID),
        "signal_id": str(SIGNAL_ID_2),
        "run_id": str(RUN_ID_2),
        "job_id": str(JOB_ID_2),
        "model": "gpt-4o-mini",
        "prompt_version": "facts_v1",
        "schema_version": "facts_v1",
        "facts": {
            "summary": "Critical MVP update requiring document viewer",
            "facts": [
                {
                    "fact_type": "feature",
                    "title": "Document Viewer Required",
                    "detail": "In-app Document Viewer is REQUIRED for MVP success",
                    "confidence": "high",
                    "evidence": [
                        {
                            "chunk_id": str(UUID("f457985d-4ecd-432a-91b8-5511ebc14e4b")),
                            "excerpt": "Document Viewer is REQUIRED for MVP success",
                            "rationale": "Client explicitly states requirement"
                        }
                    ]
                }
            ],
            "open_questions": [],
            "contradictions": []
        },
        "summary": "Critical MVP update requiring document viewer",
        "created_at": "2025-12-21T20:35:00.000000+00:00"
    }
]
