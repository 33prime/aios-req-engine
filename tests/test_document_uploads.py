"""Tests for document upload database operations and API endpoints."""

import uuid
from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# Database Operation Tests
# =============================================================================


class TestDocumentUploadDbOperations:
    """Tests for document_uploads.py database functions."""

    def test_compute_checksum(self):
        """Test checksum computation."""
        from app.db.document_uploads import compute_checksum

        content = b"test file content"
        checksum = compute_checksum(content)

        assert checksum is not None
        assert len(checksum) == 64  # SHA256 hex length
        # Same content should produce same checksum
        assert compute_checksum(content) == checksum

    def test_check_duplicate_found(self):
        """Test finding duplicate documents."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "existing-doc-id", "original_filename": "test.pdf"}]

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        with patch("app.db.document_uploads.get_supabase", return_value=mock_supabase):
            from app.db.document_uploads import check_duplicate

            project_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
            result = check_duplicate(project_id, "abc123checksum")

            assert result is not None
            assert result["id"] == "existing-doc-id"

    def test_check_duplicate_not_found(self):
        """Test when no duplicate exists."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        with patch("app.db.document_uploads.get_supabase", return_value=mock_supabase):
            from app.db.document_uploads import check_duplicate

            project_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
            result = check_duplicate(project_id, "new-checksum")

            assert result is None

    def test_create_document_upload(self):
        """Test creating a document upload record."""
        doc_id = str(uuid.uuid4())
        mock_response = MagicMock()
        mock_response.data = [{"id": doc_id, "original_filename": "test.pdf"}]

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        with patch("app.db.document_uploads.get_supabase", return_value=mock_supabase):
            from app.db.document_uploads import create_document_upload

            project_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
            result = create_document_upload(
                project_id=project_id,
                original_filename="test.pdf",
                storage_path="projects/aaa/documents/test.pdf",
                file_type="pdf",
                mime_type="application/pdf",
                file_size_bytes=1024,
                checksum="abc123",
                authority="consultant",
            )

            assert result["id"] == doc_id

            # Verify insert was called with correct data
            insert_call = mock_supabase.table.return_value.insert
            insert_call.assert_called_once()
            payload = insert_call.call_args[0][0]

            assert payload["project_id"] == str(project_id)
            assert payload["original_filename"] == "test.pdf"
            assert payload["file_type"] == "pdf"
            assert payload["processing_status"] == "pending"

    def test_get_document_upload_found(self):
        """Test getting a document by ID."""
        doc_id = uuid.uuid4()
        mock_response = MagicMock()
        mock_response.data = [{"id": str(doc_id), "original_filename": "found.pdf"}]

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        with patch("app.db.document_uploads.get_supabase", return_value=mock_supabase):
            from app.db.document_uploads import get_document_upload

            result = get_document_upload(doc_id)

            assert result is not None
            assert result["original_filename"] == "found.pdf"

    def test_get_document_upload_not_found(self):
        """Test getting a document that doesn't exist."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        with patch("app.db.document_uploads.get_supabase", return_value=mock_supabase):
            from app.db.document_uploads import get_document_upload

            result = get_document_upload(uuid.uuid4())
            assert result is None

    def test_list_project_documents_excludes_withdrawn(self):
        """Test that withdrawn documents are excluded by default."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "doc1", "is_withdrawn": False}]
        mock_response.count = 1

        mock_supabase = MagicMock()
        query = mock_supabase.table.return_value.select.return_value
        query.eq.return_value.neq.return_value.order.return_value.range.return_value.execute.return_value = mock_response

        with patch("app.db.document_uploads.get_supabase", return_value=mock_supabase):
            from app.db.document_uploads import list_project_documents

            project_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
            result = list_project_documents(project_id)

            assert len(result["documents"]) == 1
            # Verify neq filter was applied for withdrawn
            mock_supabase.table.return_value.select.return_value.eq.return_value.neq.assert_called_with(
                "is_withdrawn", True
            )

    def test_update_document_processing_completed(self):
        """Test updating a document after successful processing."""
        doc_id = uuid.uuid4()
        mock_response = MagicMock()
        mock_response.data = [{"id": str(doc_id), "processing_status": "completed"}]

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        with patch("app.db.document_uploads.get_supabase", return_value=mock_supabase):
            from app.db.document_uploads import update_document_processing

            result = update_document_processing(
                document_id=doc_id,
                status="completed",
                page_count=5,
                word_count=1000,
                total_chunks=10,
                content_summary="Test summary",
                quality_score=0.85,
                relevance_score=0.9,
                information_density=0.75,
            )

            assert result["processing_status"] == "completed"

            # Verify update payload
            update_call = mock_supabase.table.return_value.update
            update_call.assert_called_once()
            payload = update_call.call_args[0][0]

            assert payload["processing_status"] == "completed"
            assert payload["page_count"] == 5
            assert payload["quality_score"] == 0.85

    def test_update_document_processing_failed(self):
        """Test updating a document after failed processing."""
        doc_id = uuid.uuid4()
        mock_response = MagicMock()
        mock_response.data = [{"id": str(doc_id), "processing_status": "failed"}]

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        with patch("app.db.document_uploads.get_supabase", return_value=mock_supabase):
            from app.db.document_uploads import update_document_processing

            result = update_document_processing(
                document_id=doc_id,
                status="failed",
                error="Extraction failed: unsupported format",
            )

            assert result["processing_status"] == "failed"

            payload = mock_supabase.table.return_value.update.call_args[0][0]
            assert payload["processing_error"] == "Extraction failed: unsupported format"

    def test_withdraw_document(self):
        """Test soft-deleting a document."""
        doc_id = uuid.uuid4()
        signal_id = str(uuid.uuid4())

        # Mock get_document_upload
        mock_doc = {"id": str(doc_id), "signal_id": signal_id, "original_filename": "test.pdf"}

        mock_doc_response = MagicMock()
        mock_doc_response.data = [mock_doc]

        mock_update_response = MagicMock()
        mock_update_response.data = [{"id": str(doc_id), "is_withdrawn": True}]

        mock_signal_response = MagicMock()
        mock_signal_response.data = [{"id": signal_id, "is_withdrawn": True}]

        mock_supabase = MagicMock()

        # Configure the mock chain
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_doc_response
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = [
            mock_update_response,  # First update is for document
            mock_signal_response,  # Second update is for signal
        ]

        with patch("app.db.document_uploads.get_supabase", return_value=mock_supabase):
            from app.db.document_uploads import withdraw_document

            result = withdraw_document(doc_id)

            assert result is True

    def test_withdraw_document_not_found(self):
        """Test withdrawing a document that doesn't exist."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        with patch("app.db.document_uploads.get_supabase", return_value=mock_supabase):
            from app.db.document_uploads import withdraw_document

            result = withdraw_document(uuid.uuid4())
            assert result is False

    def test_get_documents_with_usage(self):
        """Test getting documents with usage statistics."""
        project_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        signal_id = str(uuid.uuid4())

        mock_docs_response = MagicMock()
        mock_docs_response.data = [
            {
                "id": "doc1",
                "signal_id": signal_id,
                "authority": "consultant",
                "processing_status": "completed",
            }
        ]

        mock_impacts_response = MagicMock()
        mock_impacts_response.data = [
            {"entity_type": "feature"},
            {"entity_type": "feature"},
            {"entity_type": "persona"},
        ]

        mock_supabase = MagicMock()

        # Configure select chains - now includes .neq() for filtering withdrawn documents
        mock_supabase.table.return_value.select.return_value.eq.return_value.neq.return_value.order.return_value.execute.return_value = mock_docs_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_impacts_response

        with patch("app.db.document_uploads.get_supabase", return_value=mock_supabase):
            from app.db.document_uploads import get_documents_with_usage

            result = get_documents_with_usage(project_id)

            assert len(result) == 1
            doc = result[0]
            assert doc["usage_count"] == 3
            assert doc["contributed_to"]["features"] == 2
            assert doc["contributed_to"]["personas"] == 1


# =============================================================================
# API Endpoint Tests
# =============================================================================


class TestDocumentUploadApi:
    """Tests for document upload API endpoints."""

    def test_get_document_status_endpoint(self):
        """Test the document status endpoint returns correct data."""
        doc_id = uuid.uuid4()
        mock_doc = {
            "id": str(doc_id),
            "processing_status": "completed",
            "original_filename": "test.pdf",
            "page_count": 10,
            "word_count": 5000,
            "document_class": "requirements",
        }

        mock_response = MagicMock()
        mock_response.data = [mock_doc]

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        with patch("app.db.document_uploads.get_supabase", return_value=mock_supabase):
            from app.db.document_uploads import get_document_upload

            result = get_document_upload(doc_id)

            assert result["processing_status"] == "completed"
            assert result["page_count"] == 10

    def test_claim_document_for_processing_success(self):
        """Test claiming a pending document for processing."""
        doc_id = uuid.uuid4()
        mock_response = MagicMock()
        mock_response.data = [{"id": str(doc_id), "processing_status": "processing"}]

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        with patch("app.db.document_uploads.get_supabase", return_value=mock_supabase):
            from app.db.document_uploads import claim_document_for_processing

            result = claim_document_for_processing(doc_id)
            assert result is True

    def test_claim_document_for_processing_already_claimed(self):
        """Test claiming a document that's already being processed."""
        doc_id = uuid.uuid4()
        mock_response = MagicMock()
        mock_response.data = []  # No rows updated means already claimed

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        with patch("app.db.document_uploads.get_supabase", return_value=mock_supabase):
            from app.db.document_uploads import claim_document_for_processing

            result = claim_document_for_processing(doc_id)
            assert result is False

    def test_get_project_document_stats(self):
        """Test getting document statistics for a project."""
        project_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

        mock_response = MagicMock()
        mock_response.data = [
            {"processing_status": "completed", "file_type": "pdf", "document_class": "requirements"},
            {"processing_status": "completed", "file_type": "pdf", "document_class": "transcript"},
            {"processing_status": "pending", "file_type": "docx", "document_class": None},
        ]

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        with patch("app.db.document_uploads.get_supabase", return_value=mock_supabase):
            from app.db.document_uploads import get_project_document_stats

            result = get_project_document_stats(project_id)

            assert result["total"] == 3
            assert result["by_status"]["completed"] == 2
            assert result["by_status"]["pending"] == 1
            assert result["by_type"]["pdf"] == 2
            assert result["by_type"]["docx"] == 1


# =============================================================================
# Validation Tests
# =============================================================================


class TestDocumentValidation:
    """Tests for document upload validation."""

    def test_file_type_detection_pdf(self):
        """Test that PDF files are correctly typed."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "doc1", "file_type": "pdf"}]

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        with patch("app.db.document_uploads.get_supabase", return_value=mock_supabase):
            from app.db.document_uploads import create_document_upload

            project_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
            result = create_document_upload(
                project_id=project_id,
                original_filename="test.pdf",
                storage_path="path/test.pdf",
                file_type="pdf",
                mime_type="application/pdf",
                file_size_bytes=1024,
                checksum="abc123",
            )

            payload = mock_supabase.table.return_value.insert.call_args[0][0]
            assert payload["file_type"] == "pdf"
            assert payload["mime_type"] == "application/pdf"

    def test_create_document_with_all_fields(self):
        """Test creating a document with all optional fields."""
        doc_id = str(uuid.uuid4())
        user_id = uuid.uuid4()

        mock_response = MagicMock()
        mock_response.data = [{"id": doc_id}]

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        with patch("app.db.document_uploads.get_supabase", return_value=mock_supabase):
            from app.db.document_uploads import create_document_upload

            project_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
            create_document_upload(
                project_id=project_id,
                original_filename="important.pdf",
                storage_path="path/important.pdf",
                file_type="pdf",
                mime_type="application/pdf",
                file_size_bytes=2048,
                checksum="xyz789",
                uploaded_by=user_id,
                upload_source="client_portal",
                authority="client",
                processing_priority=90,
            )

            payload = mock_supabase.table.return_value.insert.call_args[0][0]
            assert payload["uploaded_by"] == str(user_id)
            assert payload["upload_source"] == "client_portal"
            assert payload["authority"] == "client"
            assert payload["processing_priority"] == 90
