
"""
Optional smoke test for progress/objective tracking.
Run:
    python tests/smoke_test_progress.py
"""

from __future__ import annotations

from app.bootstrap import build_runtime


def main() -> None:
    runtime = build_runtime()
    channel_id = "progress-test-channel"
    campaign_id = "PROGRESS_TEST"
    runtime.campaign_service.ensure_campaign(campaign_id, name="Progress Test")
    runtime.campaign_service.set_active_campaign(channel_id, campaign_id)
    runtime.progress_repo.upsert_scene({"campaign_id": campaign_id, "scene_id": "scene_one", "title": "Scene One", "order_index": 1, "room_id": None})
    print(runtime.progress_service.scene_list_text(channel_id))
    print(runtime.progress_service.set_scene(channel_id, "scene_one"))
    print(runtime.progress_service.add_objective(channel_id, "Find the missing blacksmith."))
    print(runtime.progress_service.progress_text(channel_id))


if __name__ == "__main__":
    main()
