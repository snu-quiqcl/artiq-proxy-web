"""HTTP API to list and read experiment scripts under the local ARTIQ repository tree."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

SCRIPT_TYPE = "script"


def _utc_iso_z(mtime: float) -> str:
    dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _script_repository_root() -> Path | None:
    raw = (getattr(settings, "ARTIQ_MASTER_PATH", None) or "").strip()
    if not raw:
        return None
    return (Path(raw).expanduser()).resolve() / "repository"


def _ensure_repository_ready() -> tuple[Path | None, Response | None]:
    root = _script_repository_root()
    if root is None:
        return None, Response(
            {"detail": "ARTIQ_MASTER_PATH is not configured."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if not root.is_dir():
        return None, Response(
            {"detail": "Script repository directory does not exist."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return root, None


def _resolve_under_root(root: Path, relative: str) -> tuple[Path | None, Response | None]:
    rel = (relative or "").strip().replace("\\", "/").lstrip("/")
    root_resolved = root.resolve()
    candidate = (root_resolved / rel).resolve() if rel else root_resolved
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return None, Response(
            {"detail": "Invalid path."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return candidate, None


def _relative_display(root: Path, target: Path) -> str:
    root_resolved = root.resolve()
    target_resolved = target.resolve()
    if target_resolved == root_resolved:
        return ""
    return str(target_resolved.relative_to(root_resolved)).replace("\\", "/")


class FileListView(APIView):
    """List files and directories under ``<ARTIQ_MASTER_PATH>/repository/``."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if request.query_params.get("type") != SCRIPT_TYPE:
            return Response(
                {"detail": 'Unsupported type; only "script" is supported.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        root, err = _ensure_repository_ready()
        if err:
            return err
        assert root is not None
        subpath = request.query_params.get("path") or ""
        target, err = _resolve_under_root(root, subpath)
        if err:
            return err
        assert target is not None
        if not target.is_dir():
            return Response(
                {"detail": "Path is not a directory."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        items = []
        with os.scandir(target) as it:
            entries = list(it)
        entries.sort(
            key=lambda e: (not e.is_dir(follow_symlinks=False), e.name),
        )
        for de in entries:
            st = de.stat(follow_symlinks=False)
            is_dir = de.is_dir(follow_symlinks=False)
            items.append(
                {
                    "name": de.name,
                    "kind": "dir" if is_dir else "file",
                    "size": None if is_dir else st.st_size,
                    "modified_at": _utc_iso_z(st.st_mtime),
                }
            )
        rel_display = _relative_display(root, target)
        return Response(
            {"type": SCRIPT_TYPE, "path": rel_display, "items": items},
        )


class FileReadView(APIView):
    """Read a text file under ``<ARTIQ_MASTER_PATH>/repository/``."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if request.query_params.get("type") != SCRIPT_TYPE:
            return Response(
                {"detail": 'Unsupported type; only "script" is supported.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        path_param = request.query_params.get("path")
        if path_param is None or path_param.strip() == "":
            return Response(
                {"detail": "path is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        root, err = _ensure_repository_ready()
        if err:
            return err
        assert root is not None
        target, err = _resolve_under_root(root, path_param)
        if err:
            return err
        assert target is not None
        if not target.is_file():
            return Response(
                {"detail": "Path is not a file."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        content = target.read_text(encoding="utf-8", errors="replace")
        rel_display = _relative_display(root, target)
        return Response({"path": rel_display, "content": content})
