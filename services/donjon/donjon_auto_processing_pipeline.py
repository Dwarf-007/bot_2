from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PipelineStepResult:
    name: str
    ok: bool
    command: List[str] = field(default_factory=list)
    returncode: Optional[int] = None
    stdout: str = ''
    stderr: str = ''
    skipped: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DonjonAutoProcessingResult:
    ok: bool
    campaign_id: str
    source_dir: str
    output_dir: str
    manifest_file: Optional[str]
    steps: List[PipelineStepResult]
    files: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DonjonAutoProcessingPipeline:
    EXPECTED_OUTPUT_FILES = [
        'dungeon_graph.json', 'room_data.json', 'room_lookup.json', 'rag_index.json', 'toc_index.json',
        'map_geometry.json', 'stair_links.json', 'fog_manifest.json', 'navigation_index.json',
        'corridor_graph.json', 'unresolved_doors.json', 'corridor_visibility_graph.json',
        'corridor_visibility_labels.json', 'secret_discovery_state.json',
    ]

    def __init__(self, project_root: str | Path = '.', python_executable: str | None = None) -> None:
        self.project_root = Path(project_root).resolve()
        self.python = python_executable or sys.executable

    def run(
        self,
        *,
        campaign_id: str,
        source_dir: str | Path,
        output_dir: str | Path,
        manifest_file: str | Path | None = None,
        copy_download_assets: bool = True,
        init_secret_state: bool = True,
        run_sanity_check: bool = True,
        runtime_import: bool = False,
        runtime_import_tool: str = 'tools/import_generated_bundle_runtime.py',
        runtime_name: Optional[str] = None,
        clear_rag: bool = False,
        max_label_match_distance: int = 2,
    ) -> DonjonAutoProcessingResult:
        src = self._abs(source_dir)
        out = self._abs(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        steps: List[PipelineStepResult] = []
        warnings: List[str] = []

        if copy_download_assets:
            steps.append(self._copy_assets(src, out))

        manifest = self._resolve_manifest(src, out, manifest_file)
        if not manifest:
            warnings.append('Nem található Donjon manifest JSON. A graph build nem futtatható.')
            return DonjonAutoProcessingResult(False, campaign_id, str(src), str(out), None, steps, warnings=warnings)

        steps.append(self._run_command('build_dungeon_graph_v3', [
            self.python, 'tools/build_dungeon_graph_from_donjon_exports.py',
            '--campaign-id', campaign_id, '--manifest', str(manifest), '--output-dir', str(out)
        ]))

        if run_sanity_check and (out / 'dungeon_graph.json').exists():
            steps.append(self._run_command('sanity_check_dungeon_graph', [
                self.python, 'tools/sanity_check_dungeon_graph.py', str(out / 'dungeon_graph.json')
            ], fail_pipeline=False))

        steps.append(self._copy_tsv_assets(src, out))

        steps.append(self._run_command('build_corridor_visibility_graph_v2', [
            self.python, 'tools/build_corridor_visibility_graph.py', '--bundle-dir', str(out)
        ]))

        if (self.project_root / 'tools/debug_visibility_graph_stats.py').exists():
            steps.append(self._run_command('debug_visibility_graph_stats', [
                self.python, 'tools/debug_visibility_graph_stats.py', str(out / 'corridor_visibility_graph.json')
            ], fail_pipeline=False))

        steps.append(self._run_command('bind_corridor_visibility_labels', [
            self.python, 'tools/bind_corridor_visibility_labels.py', '--bundle-dir', str(out),
            '--max-match-distance', str(max_label_match_distance)
        ]))

        if init_secret_state:
            steps.append(self._run_command('init_secret_discovery_state', [
                self.python, 'tools/secret_discovery_cli.py', '--bundle-dir', str(out),
                '--campaign-id', campaign_id, 'init', '--overwrite'
            ], fail_pipeline=False))

        if runtime_import:
            cmd = [self.python, runtime_import_tool, str(out), '--campaign-id', campaign_id]
            if runtime_name:
                cmd += ['--name', runtime_name]
            if clear_rag:
                cmd += ['--clear-rag']
            steps.append(self._run_command('runtime_import_generated_bundle', cmd, fail_pipeline=False))

        files = {name: str(out / name) for name in self.EXPECTED_OUTPUT_FILES if (out / name).exists()}
        hard_steps = {'build_dungeon_graph_v3', 'copy_tsv_assets', 'build_corridor_visibility_graph_v2', 'bind_corridor_visibility_labels'}
        ok = all(step.ok for step in steps if step.name in hard_steps)
        return DonjonAutoProcessingResult(ok, campaign_id, str(src), str(out), str(manifest), steps, files, warnings)

    def _abs(self, path: str | Path) -> Path:
        p = Path(path)
        return p if p.is_absolute() else self.project_root / p

    def _run_command(self, name: str, command: List[str], fail_pipeline: bool = True) -> PipelineStepResult:
        env = dict(os.environ)
        env['PYTHONPATH'] = str(self.project_root)
        try:
            completed = subprocess.run(command, cwd=str(self.project_root), env=env, capture_output=True, text=True)
            return PipelineStepResult(name, completed.returncode == 0 or not fail_pipeline, command, completed.returncode, completed.stdout, completed.stderr)
        except FileNotFoundError as exc:
            return PipelineStepResult(name, not fail_pipeline, command, stderr=str(exc))

    def _copy_assets(self, src: Path, out: Path) -> PipelineStepResult:
        if not src.exists():
            return PipelineStepResult('copy_download_assets', False, stderr=f'Source dir does not exist: {src}')
        copied = []
        for path in src.rglob('*'):
            if not path.is_file() or path.suffix.lower() not in {'.json', '.tsv', '.png', '.jpg', '.jpeg', '.gif', '.html', '.htm'}:
                continue
            dest = out / path.name
            if dest.exists() and dest.stat().st_size == path.stat().st_size:
                continue
            shutil.copy2(path, dest)
            copied.append(str(dest))
        return PipelineStepResult('copy_download_assets', True, details={'count': len(copied), 'copied': copied})

    def _copy_tsv_assets(self, src: Path, out: Path) -> PipelineStepResult:
        copied = []
        if src.exists():
            for path in src.rglob('*.tsv'):
                dest = out / path.name
                if not dest.exists() or dest.stat().st_size != path.stat().st_size:
                    shutil.copy2(path, dest)
                    copied.append(str(dest))
        return PipelineStepResult('copy_tsv_assets', True, details={'count': len(copied), 'copied': copied})

    def _resolve_manifest(self, src: Path, out: Path, manifest_file: str | Path | None) -> Optional[Path]:
        if manifest_file:
            p = self._abs(manifest_file)
            return p if p.exists() else None
        candidates: List[Path] = []
        for root in [out, src]:
            if root.exists():
                candidates.extend(root.rglob('*manifest*.json'))
        if not candidates:
            for root in [out, src]:
                if root.exists():
                    candidates.extend(root.rglob('*.json'))
        candidates = sorted(set(candidates), key=lambda p: (0 if 'manifest' in p.name.lower() else 1, len(str(p)), str(p)))
        for candidate in candidates:
            if self._looks_like_manifest(candidate):
                return candidate
        return candidates[0] if candidates else None

    @staticmethod
    def _looks_like_manifest(path: Path) -> bool:
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return False
        if not isinstance(data, dict):
            return False
        keys = set(data.keys())
        return bool(keys & {'levels', 'exports', 'level_exports', 'downloaded_files', 'files'}) or 'manifest' in path.name.lower()
