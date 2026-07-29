from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from services.donjon.donjon_auto_processing_pipeline import DonjonAutoProcessingPipeline


class DonjonGenerationPostprocessHook:
    def __init__(self, project_root: str | Path = '.') -> None:
        self.pipeline = DonjonAutoProcessingPipeline(project_root=project_root)

    def after_download(
        self,
        *,
        campaign_id: str,
        download_dir: str | Path,
        output_dir: str | Path,
        manifest_file: str | Path | None = None,
        runtime_import: bool = False,
        runtime_name: Optional[str] = None,
        clear_rag: bool = False,
    ) -> Dict[str, Any]:
        return self.pipeline.run(
            campaign_id=campaign_id,
            source_dir=download_dir,
            output_dir=output_dir,
            manifest_file=manifest_file,
            runtime_import=runtime_import,
            runtime_name=runtime_name,
            clear_rag=clear_rag,
        ).to_dict()
