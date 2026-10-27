"""GCS-backed workspace & seed data store for Synchrony Financial Virtual PM."""

from __future__ import annotations

import datetime
import difflib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from google.cloud import storage

logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "vertexai-l300-capstone")
BUCKET_NAME = os.environ.get(
    "SYF_WORKSPACE_BUCKET", f"{PROJECT_ID}-syf-vpm-workspace"
)
LOCAL_SEED_DIR = Path(__file__).parent / "seed_data"


class SyfGcsWorkspaceStore:
    """Manages Synchrony seed data, living Cursor-style artifacts, and scaffolded code in GCS."""

    def __init__(self, bucket_name: str = BUCKET_NAME) -> None:
        self.bucket_name = bucket_name
        self._client: storage.Client | None = None

    @property
    def client(self) -> storage.Client:
        if self._client is None:
            self._client = storage.Client(project=PROJECT_ID)
        return self._client

    def _get_bucket(self) -> storage.Bucket:
        return self.client.bucket(self.bucket_name)

    def read_text(self, gcs_path: str, local_fallback: Path | None = None) -> str:
        """Read UTF-8 text from gs://<bucket>/<gcs_path> with local fallback."""
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(gcs_path)
            if blob.exists():
                return blob.download_as_text(encoding="utf-8")
        except Exception as exc:
            logger.warning("GCS read fallback for %s: %s", gcs_path, exc)

        if local_fallback and local_fallback.exists():
            return local_fallback.read_text(encoding="utf-8")
        raise FileNotFoundError(f"Artifact not found in GCS ({gcs_path}) or local fallback.")

    def write_text(
        self, gcs_path: str, content: str, content_type: str = "text/markdown"
    ) -> str:
        """Write UTF-8 text to gs://<bucket>/<gcs_path> and return the gs:// URI."""
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(gcs_path)
            blob.upload_from_string(content, content_type=content_type)
            return f"gs://{self.bucket_name}/{gcs_path}"
        except Exception as exc:
            logger.warning("GCS write failed for %s, writing locally: %s", gcs_path, exc)
            local_target = LOCAL_SEED_DIR / gcs_path
            local_target.parent.mkdir(parents=True, exist_ok=True)
            local_target.write_text(content, encoding="utf-8")
            return f"file://{local_target}"

    def read_json(self, gcs_path: str, local_fallback: Path | None = None) -> dict[str, Any]:
        return json.loads(self.read_text(gcs_path, local_fallback=local_fallback))

    def write_json(self, gcs_path: str, data: dict[str, Any]) -> str:
        text = json.dumps(data, indent=2)
        return self.write_text(gcs_path, text, content_type="application/json")

    def list_workspace_documents(self) -> list[dict[str, Any]]:
        """List all living documents in workspace_artifacts/ and scaffolded_code/."""
        results: list[dict[str, Any]] = []
        try:
            bucket = self._get_bucket()
            for prefix in ("workspace_artifacts/", "scaffolded_code/"):
                for blob in bucket.list_blobs(prefix=prefix):
                    if blob.name.endswith("/"):
                        continue
                    results.append(
                        {
                            "name": blob.name.split("/")[-1],
                            "gcs_path": blob.name,
                            "gcs_uri": f"gs://{self.bucket_name}/{blob.name}",
                            "size_bytes": blob.size,
                            "updated_at": blob.updated.isoformat() if blob.updated else None,
                        }
                    )
        except Exception as exc:
            logger.warning("Failed listing GCS blobs: %s", exc)

        if not results:
            for p in (LOCAL_SEED_DIR / "workspace_artifacts").glob("*"):
                if p.is_file():
                    results.append(
                        {
                            "name": p.name,
                            "gcs_path": f"workspace_artifacts/{p.name}",
                            "gcs_uri": f"gs://{self.bucket_name}/workspace_artifacts/{p.name}",
                            "size_bytes": p.stat().st_size,
                            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        }
                    )
        return results

    def get_workspace_document(self, document_name: str) -> dict[str, Any]:
        """Retrieve a living document (e.g. PRD-AI-EVAL-101.md, ADR-001-Eval-Gateway.md, BACKLOG-AI-EVAL-101.json)."""
        clean_name = document_name.split("/")[-1]
        gcs_path = f"workspace_artifacts/{clean_name}"
        local_fallback = LOCAL_SEED_DIR / "workspace_artifacts" / clean_name
        content = self.read_text(gcs_path, local_fallback=local_fallback)
        return {
            "document_name": clean_name,
            "gcs_uri": f"gs://{self.bucket_name}/{gcs_path}",
            "content": content,
        }

    def save_workspace_document(
        self, document_name: str, content: str, author: str = "Alex (vpm-agent)"
    ) -> dict[str, Any]:
        """Save or overwrite a workspace document and archive a timestamped snapshot in history/."""
        clean_name = document_name.split("/")[-1]
        gcs_path = f"workspace_artifacts/{clean_name}"
        ctype = "application/json" if clean_name.endswith(".json") else "text/markdown"
        uri = self.write_text(gcs_path, content, content_type=ctype)
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        history_path = f"workspace_artifacts/history/{clean_name}.{ts}.bak"
        self.write_text(history_path, content, content_type=ctype)
        return {
            "status": "SAVED",
            "document_name": clean_name,
            "gcs_uri": uri,
            "history_snapshot_uri": f"gs://{self.bucket_name}/{history_path}",
            "author": author,
            "timestamp": ts,
        }

    def patch_document_section(
        self,
        document_name: str,
        section_header: str,
        new_section_markdown: str,
        edit_reason: str,
        author: str = "Alex (vpm-agent)",
    ) -> dict[str, Any]:
        """Cursor-style surgical section replacement with unified line diff (- / +) and version bump."""
        doc = self.get_workspace_document(document_name)
        original_content = doc["content"]

        # Normalize section header
        target_header = section_header.strip()
        if not target_header.startswith("##"):
            target_header = f"## {target_header}"

        # Ensure new_section_markdown begins with the header
        replacement_block = new_section_markdown.strip()
        if not replacement_block.startswith("##"):
            replacement_block = f"{target_header}\n{replacement_block}"

        # Match from target_header up to the next `## ` header or EOF
        escaped_header = re.escape(target_header)
        pattern = re.compile(
            rf"(^{escaped_header}[^\n]*\n.*?)(?=^## |\Z)",
            re.MULTILINE | re.DOTALL,
        )

        if pattern.search(original_content):
            updated_content = pattern.sub(f"{replacement_block}\n\n", original_content, count=1)
        else:
            # Fallback: match by section number prefix (e.g. "## 4.")
            num_match = re.match(r"^(##\s*\d+\.)", target_header)
            if num_match:
                prefix_escaped = re.escape(num_match.group(1))
                fallback_pattern = re.compile(
                    rf"(^{prefix_escaped}[^\n]*\n.*?)(?=^## |\Z)",
                    re.MULTILINE | re.DOTALL,
                )
                if fallback_pattern.search(original_content):
                    updated_content = fallback_pattern.sub(
                        f"{replacement_block}\n\n", original_content, count=1
                    )
                else:
                    updated_content = original_content.rstrip() + f"\n\n{replacement_block}\n"
            else:
                updated_content = original_content.rstrip() + f"\n\n{replacement_block}\n"

        # Bump version in YAML frontmatter if present (e.g., version: "1.0" -> "1.1")
        old_version = "1.0"
        new_version = "1.1"
        ver_match = re.search(r'^version:\s*"?(\d+)\.(\d+)"?', updated_content, re.MULTILINE)
        if ver_match:
            major, minor = int(ver_match.group(1)), int(ver_match.group(2))
            old_version = f"{major}.{minor}"
            new_version = f"{major}.{minor + 1}"
            updated_content = re.sub(
                r'^version:\s*"?\d+\.\d+"?',
                f'version: "{new_version}"',
                updated_content,
                count=1,
                flags=re.MULTILINE,
            )

        # Compute unified diff
        diff_lines = list(
            difflib.unified_diff(
                original_content.splitlines(),
                updated_content.splitlines(),
                fromfile=f"{document_name} (v{old_version})",
                tofile=f"{document_name} (v{new_version})",
                lineterm="",
                n=2,
            )
        )
        unified_diff = "\n".join(diff_lines)

        save_res = self.save_workspace_document(
            document_name=document_name, content=updated_content, author=author
        )
        return {
            "card_type": "cursor_inline_diff_card",
            "status": "PATCHED",
            "document_name": document_name,
            "section_patched": target_header,
            "previous_version": old_version,
            "new_version": new_version,
            "edit_reason": edit_reason,
            "author": author,
            "gcs_uri": save_res["gcs_uri"],
            "history_snapshot_uri": save_res["history_snapshot_uri"],
            "unified_diff": unified_diff,
        }
