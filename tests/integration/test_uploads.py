"""
tests/integration/test_uploads.py
=================================

Pruebas del módulo Uploads (Cloudinary). El SDK se mockea con
monkeypatch: los tests NO pegan a Cloudinary real (spec 10: validar
MIME y tamaño en el router/service; rúbrica pide mocks correctos).
"""

import io

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

UPLOAD_URL = "/api/v1/uploads/imagen"

FAKE_UPLOAD_RESULT = {
    "secure_url": "https://res.cloudinary.com/demo/image/upload/v1/foodstore/productos/abc123.jpg",
    "public_id": "foodstore/productos/abc123",
    "width": 800,
    "height": 600,
    "format": "jpg",
    "resource_type": "image",
}


@pytest.fixture
def mock_cloudinary(monkeypatch):
    """Reemplaza cloudinary.uploader.upload/destroy por fakes en memoria."""
    import app.modules.uploads.service as uploads_service

    llamadas = {"upload": [], "destroy": []}

    def fake_upload(contents, **kwargs):
        llamadas["upload"].append(kwargs)
        return dict(FAKE_UPLOAD_RESULT)

    def fake_destroy(public_id, **kwargs):
        llamadas["destroy"].append(public_id)
        return {"result": "ok"}

    monkeypatch.setattr(uploads_service.cloudinary.uploader, "upload", fake_upload)
    monkeypatch.setattr(uploads_service.cloudinary.uploader, "destroy", fake_destroy)
    return llamadas


def _imagen(nombre="foto.jpg", mime="image/jpeg", size=1024):
    """Arma el multipart/form-data con una imagen fake."""
    return {"file": (nombre, io.BytesIO(b"x" * size), mime)}


# ===========================================================================
# TESTS: POST /uploads/imagen
# ===========================================================================
class TestUploadImagen:
    """POST /api/v1/uploads/imagen (solo ADMIN, multipart)"""

    def test_upload_ok_returns_201_con_secure_url(
        self, client: TestClient, admin_headers, mock_cloudinary
    ):
        """Happy path: 201 con secure_url y public_id (spec 6.3)."""
        response = client.post(
            UPLOAD_URL, files=_imagen(), headers=admin_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["secure_url"].startswith("https://res.cloudinary.com/")
        assert data["public_id"] == FAKE_UPLOAD_RESULT["public_id"]
        assert len(mock_cloudinary["upload"]) == 1

    def test_mime_invalido_returns_400(
        self, client: TestClient, admin_headers, mock_cloudinary
    ):
        """Solo image/jpeg, image/png, image/webp (spec 10.1 paso 3)."""
        response = client.post(
            UPLOAD_URL,
            files=_imagen("doc.pdf", "application/pdf"),
            headers=admin_headers,
        )
        assert response.status_code == 400
        assert len(mock_cloudinary["upload"]) == 0  # nunca llegó al SDK

    def test_archivo_muy_grande_returns_400(
        self, client: TestClient, admin_headers, mock_cloudinary
    ):
        """Máximo 5 MB (spec 10.1 paso 3)."""
        response = client.post(
            UPLOAD_URL,
            files=_imagen(size=5 * 1024 * 1024 + 1),
            headers=admin_headers,
        )
        assert response.status_code == 400
        assert len(mock_cloudinary["upload"]) == 0

    def test_sin_auth_returns_401(self, client: TestClient, db_session, mock_cloudinary):
        response = client.post(UPLOAD_URL, files=_imagen())
        assert response.status_code == 401

    def test_client_sin_rol_admin_returns_403(
        self, client: TestClient, client_headers, mock_cloudinary
    ):
        """Upload es exclusivo de ADMIN (spec 5.5)."""
        response = client.post(UPLOAD_URL, files=_imagen(), headers=client_headers)
        assert response.status_code == 403


# ===========================================================================
# TESTS: DELETE /uploads/imagen/{public_id}
# ===========================================================================
class TestDeleteImagen:
    """DELETE /api/v1/uploads/imagen/{public_id} (solo ADMIN)"""

    def test_delete_ok_returns_204(
        self, client: TestClient, admin_headers, mock_cloudinary
    ):
        response = client.delete(
            "/api/v1/uploads/imagen/foodstore/productos/abc123",
            headers=admin_headers,
        )
        assert response.status_code == 204
        assert mock_cloudinary["destroy"] == ["foodstore/productos/abc123"]

    def test_delete_sin_admin_returns_403(
        self, client: TestClient, client_headers, mock_cloudinary
    ):
        response = client.delete(
            "/api/v1/uploads/imagen/foodstore/productos/abc123",
            headers=client_headers,
        )
        assert response.status_code == 403
