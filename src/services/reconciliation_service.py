from __future__ import annotations

from copy import deepcopy
from typing import Any


class ReconciliationService:
    """
    Reconciles ordered page-level extraction payloads into one package-level result.
    """

    def reconcile(self, page_results: list[dict[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for page_result in page_results:
            for field_name, candidate in page_result.items():
                existing = merged.get(field_name)
                if existing is None:
                    merged[field_name] = deepcopy(candidate)
                    continue
                merged[field_name] = self._merge_field(existing, candidate)
        return merged

    def _merge_field(self, existing: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        existing_value = existing.get("value")
        candidate_value = candidate.get("value")

        if isinstance(existing_value, list) and isinstance(candidate_value, list):
            merged = deepcopy(existing)
            merged["value"] = self._deduplicate_list(existing_value + candidate_value)
            merged["confidence"] = max(existing.get("confidence", 0.0), candidate.get("confidence", 0.0))
            if candidate.get("confidence", 0.0) >= existing.get("confidence", 0.0):
                merged["bbox"] = candidate.get("bbox")
                merged["page_number"] = candidate.get("page_number")
            return merged

        if self._is_missing(existing_value) and not self._is_missing(candidate_value):
            return deepcopy(candidate)
        if self._is_missing(candidate_value):
            return deepcopy(existing)

        existing_conf = existing.get("confidence", 0.0)
        candidate_conf = candidate.get("confidence", 0.0)
        if candidate_conf > existing_conf:
            return deepcopy(candidate)
        if candidate_conf == existing_conf and not existing.get("bbox") and candidate.get("bbox"):
            return deepcopy(candidate)
        return deepcopy(existing)

    def _is_missing(self, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        if isinstance(value, (list, dict)):
            return len(value) == 0
        return False

    def _deduplicate_list(self, values: list[Any]) -> list[Any]:
        deduplicated: list[Any] = []
        for value in values:
            if value not in deduplicated:
                deduplicated.append(deepcopy(value))
        return deduplicated
