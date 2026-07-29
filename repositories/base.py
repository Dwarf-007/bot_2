"""
REPOSITORIES/BASE.PY
Base repository wrapper around the persistence database module.
"""

from __future__ import annotations


class BaseRepository:
    def __init__(self, db_module) -> None:
        self.db = db_module
