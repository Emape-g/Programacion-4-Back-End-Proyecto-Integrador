"""
tests/integration/test_uploads.py
=================================

Pruebas del módulo Uploads (almacenamiento local).
"""

import io
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

UPLOAD_URL = "/api/v1/uploads/imagen"


def _imagen(nombre="foto.jpg", mime="image/jpeg", size=1024):
    return {"file": (nombre, io.BytesIO(b"x" * size), mime)}


class TestUploadImagen:

    def test_upload_ok_returns_201_con_url(
        self, client: TestClient, admin_headers, tmp_path
    ):
        with patch("app.modules.uploads.service.UPLOAD_DIR", tmp_path):
            response = client.post(
                UPLOAD_URL, files=_imagen(), headers=admin_headers,
            )
        assert response.status_code == 201
        data = response.json()
        assert data["url"].startswith("/static/uploads/productos/")
        assert data["url"].endswith(".jpg")
        assert "filename" in data

    def test_mime_invalido_returns_400(
        self, client: TestClient, admin_headers
    ):
        response = client.post(
            UPLOAD_URL,
            files=_imagen("doc.pdf", "application/pdf"),
            headers=admin_headers,
        )
        assert response.status_code == 400

    def test_archivo_muy_grande_returns_400(
        self, client: TestClient, admin_headers
    ):
        response = client.post(
            UPLOAD_URL,
            files=_imagen(size=5 * 1024 * 1024 + 1),
            headers=admin_headers,
        )
        assert response.status_code == 400

    def test_sin_auth_returns_401(self, client: TestClient, db_session):
        response = client.post(UPLOAD_URL, files=_imagen())
        assert response.status_code == 401

    def test_client_sin_rol_admin_returns_403(
        self, client: TestClient, client_headers
    ):
        response = client.post(UPLOAD_URL, files=_imagen(), headers=client_headers)
        assert response.status_code == 403


class TestDeleteImagen:

    def test_delete_ok_returns_204(
        self, client: TestClient, admin_headers, tmp_path
    ):
        img_dir = tmp_path / "productos"
        img_dir.mkdir()
        img_file = img_dir / "test.jpg"
        img_file.write_bytes(b"fake")

        with patch("app.modules.uploads.service.UPLOAD_DIR", tmp_path):
            response = client.delete(
                "/api/v1/uploads/imagen/productos/test.jpg",
                headers=admin_headers,
            )
        assert response.status_code == 204
        assert not img_file.exists()

    def test_delete_sin_admin_returns_403(
        self, client: TestClient, client_headers
    ):
        response = client.delete(
            "/api/v1/uploads/imagen/productos/test.jpg",
            headers=client_headers,
        )
        assert response.status_code == 403
