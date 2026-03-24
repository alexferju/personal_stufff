"""
Entropy Management

Harness Principle: Code entropy accumulates. Agents drift from golden
principles over time. Run cleanup agents regularly to scan for deviations
and feed fixes back into the codebase.
"""
import json
from pathlib import Path
from datetime import datetime


class EntropyTracker:
    """Tracks entropy scores over time."""

    def __init__(self, outputs_dir: str = "outputs"):
        self.outputs_dir = Path(outputs_dir)
        self.log_path = self.outputs_dir / "entropy_log.json"

    def _load(self) -> list[dict]:
        if self.log_path.exists():
            try:
                return json.loads(self.log_path.read_text())
            except Exception:
                pass
        return []

    def record(self, project_id: str, entropy_score: int, deviations: list[dict]):
        self.outputs_dir.mkdir(exist_ok=True)
        log = self._load()
        log.append({
            "project_id": project_id,
            "timestamp": datetime.utcnow().isoformat(),
            "entropy_score": entropy_score,
            "deviation_count": len(deviations),
        })
        self.log_path.write_text(json.dumps(log, indent=2))

    def get_trend(self, project_id: str) -> list[dict]:
        return [e for e in self._load() if e["project_id"] == project_id]

    def latest_score(self, project_id: str) -> int | None:
        trend = self.get_trend(project_id)
        return trend[-1]["entropy_score"] if trend else None

    def cleanup_needed(self, project_id: str, threshold: int = 5) -> bool:
        score = self.latest_score(project_id)
        return score is not None and score >= threshold
