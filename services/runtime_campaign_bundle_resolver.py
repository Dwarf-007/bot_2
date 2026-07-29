from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class ResolvedCampaignBundle:
    campaign_id: str
    bundle_dir: Path
    source: str
    visibility_available: bool


class RuntimeCampaignBundleResolver:
    """Resolves campaign_id -> processed Donjon bundle directory.

    Resolution order:
    1. CampaignRepository.get_campaign(campaign_id).metadata['bundle_dir']
    2. campaigns/{campaign_id}_bundle_v3
    3. campaigns/{campaign_id}

    A bundle is visibility-capable when corridor_visibility_graph.json and
    corridor_visibility_labels.json are present.
    """

    REQUIRED_VISIBILITY_FILES = (
        "navigation_index.json",
        "room_data.json",
        "corridor_visibility_graph.json",
        "corridor_visibility_labels.json",
    )

    def __init__(self, campaign_repo: Any = None, project_root: str | Path = ".") -> None:
        self.campaign_repo = campaign_repo
        self.project_root = Path(project_root)

    def resolve(self, campaign_id: str) -> Optional[ResolvedCampaignBundle]:
        cid = str(campaign_id or "").strip()
        if not cid:
            return None

        candidates: list[tuple[str, Path]] = []
        meta_dir = self._metadata_bundle_dir(cid)
        if meta_dir:
            candidates.append(("campaign_metadata.bundle_dir", meta_dir))

        candidates.extend([
            ("convention.campaign_bundle_v3", Path("campaigns") / f"{cid}_bundle_v3"),
            ("convention.campaign_dir", Path("campaigns") / cid),
        ])

        for source, path in candidates:
            resolved = path if path.is_absolute() else self.project_root / path
            if not resolved.exists() or not resolved.is_dir():
                continue
            visibility_available = all((resolved / name).exists() for name in self.REQUIRED_VISIBILITY_FILES)
            if visibility_available:
                return ResolvedCampaignBundle(cid, resolved, source, True)

        return None

    def _metadata_bundle_dir(self, campaign_id: str) -> Optional[Path]:
        if not self.campaign_repo or not hasattr(self.campaign_repo, "get_campaign"):
            return None
        try:
            record = self.campaign_repo.get_campaign(campaign_id)
        except Exception:
            return None
        if not record:
            return None
        metadata = getattr(record, "metadata", None) or {}
        if not isinstance(metadata, dict):
            return None
        value = metadata.get("bundle_dir") or metadata.get("donjon_bundle_dir")
        return Path(value) if value else None
