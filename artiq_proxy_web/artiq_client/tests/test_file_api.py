"""Tests for GET /api/files/ and GET /api/files/read/."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

User = get_user_model()


@override_settings(ARTIQ_MASTER_PATH="")
class FileApiUnconfiguredTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        user = User.objects.create_user(username="u1", password="p1")
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_list_returns_503_when_master_path_missing(self) -> None:
        r = self.client.get("/api/files/", {"type": "script"})
        self.assertEqual(r.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)


class FileApiTests(TestCase):
    def setUp(self) -> None:
        master = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, master, ignore_errors=True)
        repo = master / "repository"
        repo.mkdir(parents=True)
        (repo / "hello.py").write_text("print('hi')\n", encoding="utf-8")
        sub = repo / "pkg"
        sub.mkdir()
        (sub / "nested.py").write_text("# nested\n", encoding="utf-8")

        self.client = APIClient()
        user = User.objects.create_user(username="u2", password="p2")
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        self.settings_cm = override_settings(ARTIQ_MASTER_PATH=str(master))
        self.settings_cm.enable()

    def tearDown(self) -> None:
        self.settings_cm.disable()
        super().tearDown()

    def test_list_root_sorts_dirs_before_files(self) -> None:
        r = self.client.get("/api/files/", {"type": "script"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["type"], "script")
        self.assertEqual(r.data["path"], "")
        names = [item["name"] for item in r.data["items"]]
        self.assertEqual(names, ["pkg", "hello.py"])
        py_item = next(i for i in r.data["items"] if i["name"] == "hello.py")
        self.assertEqual(py_item["kind"], "file")
        self.assertIsInstance(py_item["size"], int)
        self.assertIn("modified_at", py_item)

    def test_list_subdirectory(self) -> None:
        r = self.client.get("/api/files/", {"type": "script", "path": "pkg"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["path"], "pkg")
        self.assertEqual(len(r.data["items"]), 1)
        self.assertEqual(r.data["items"][0]["name"], "nested.py")

    def test_read_file(self) -> None:
        r = self.client.get(
            "/api/files/read/",
            {"type": "script", "path": "hello.py"},
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["path"], "hello.py")
        self.assertEqual(r.data["content"], "print('hi')\n")

    def test_unsupported_type(self) -> None:
        r = self.client.get("/api/files/", {"type": "fpga"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_path_traversal_rejected(self) -> None:
        r = self.client.get(
            "/api/files/",
            {"type": "script", "path": ".."},
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_auth(self) -> None:
        bare = APIClient()
        r = bare.get("/api/files/", {"type": "script"})
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_read_requires_path(self) -> None:
        r = self.client.get("/api/files/read/", {"type": "script"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
