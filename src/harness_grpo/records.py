"""Auditable episode records, independent of any external model provider."""

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

VARIANTS = ("fixed_tools", "untrained_full", "trained_selection", "trained_full")
DOMAINS = ("math", "code", "life")


@dataclass
class MainTrace:
    prompt_token_ids: list[int] = field(default_factory=list)
    output_token_ids: list[int] = field(default_factory=list)
    old_logprobs: list[float] = field(default_factory=list)
    text: str = ""

    def validate(self):
        if len(self.output_token_ids) != len(self.old_logprobs):
            raise ValueError("One old-policy log probability is required per main-agent output token")
        if any(not math.isfinite(v) for v in self.old_logprobs):
            raise ValueError("Log probabilities must be finite")
        if any(v > 1e-6 for v in self.old_logprobs):
            raise ValueError("Log probabilities cannot be positive")


@dataclass
class EpisodeRecord:
    run_id: str
    variant: str
    split: str
    batch_id: int
    task_id: str
    domain: str
    sample_index: int
    policy_version: str
    seed: int
    status: str
    success: bool | None
    selected_tool_ids: list[str]
    base_reward: float | None
    tool_penalty: float
    reward: float | None
    main_trace: MainTrace
    tool_call_ids: list[str] = field(default_factory=list)
    similarity_checks: list[dict] = field(default_factory=list)
    execution: dict = field(default_factory=dict)
    schema_version: int = 1

    def validate(self):
        if self.variant not in VARIANTS or self.domain not in DOMAINS or self.split not in ("train", "test"):
            raise ValueError("Unknown variant, domain or split")
        if self.batch_id < 1 or self.sample_index < 0:
            raise ValueError("Invalid batch/sample index")
        if type(self.seed) is not int or not self.run_id or not self.task_id or not self.policy_version:
            raise ValueError("Missing identity or seed")
        if len(set(self.selected_tool_ids)) != len(self.selected_tool_ids):
            raise ValueError("Selected tools must have unique IDs")
        self.main_trace.validate()
        if self.status == "infrastructure_error":
            if self.success is not None or self.reward is not None or self.base_reward is not None:
                raise ValueError("Infrastructure errors cannot be silently labeled task failures")
            return
        if self.status not in ("completed", "similarity_rejected", "policy_invalid", "execution_failed"):
            raise ValueError("Unknown terminal status")
        if type(self.success) is not bool:
            raise ValueError("Task success must be an explicit boolean, not inferred from reward")
        if self.status != "completed" and self.success:
            raise ValueError("Only completed verified episodes may succeed")
        expected = score(self.success, len(self.selected_tool_ids), self.status == "similarity_rejected")
        for name, value in zip(("base_reward", "tool_penalty", "reward"), expected):
            actual = getattr(self, name)
            if actual is None or not math.isfinite(actual) or not math.isclose(actual, value, abs_tol=1e-9):
                raise ValueError(f"Reward component {name} disagrees with the confirmed reward rule")

    def to_dict(self):
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        value = dict(value)
        value["main_trace"] = MainTrace(**value["main_trace"])
        result = cls(**value)
        result.validate()
        return result


def score(success: bool, tool_count: int, similarity_rejected: bool = False):
    """Confirmed rule: -1 exactly on similarity rejection; otherwise +/-1 minus .01 per supplied tool."""
    if type(success) is not bool or type(tool_count) is not int or tool_count < 0:
        raise ValueError("Invalid reward inputs")
    if similarity_rejected:
        return -1.0, 0.0, -1.0
    base = 1.0 if success else -1.0
    penalty = 0.01 * tool_count
    return base, penalty, base - penalty


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                raise ValueError(f"Blank JSONL record at {path}:{number}")
            try:
                yield json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON at {path}:{number}") from error


def write_jsonl(path, records):
    """Write a new artifact; never overwrite an existing run's records."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
