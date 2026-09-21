"""Single-pass controller episode orchestration with injected model/sandbox adapters.

This module never executes generated Python on the host. A SolverRunner must run it
in the separately configured isolated environment and return a trusted verifier result.
"""

import ast
import inspect
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from .dataset import main_agent_input, safe_asset
from .records import EpisodeRecord, MainTrace, score
from .tools import REGISTRY, catalog


@dataclass(frozen=True)
class ActionStep:
    """One completed JSONL action and the cumulative main-agent trace at that point."""
    action: dict
    trace: MainTrace


@dataclass(frozen=True)
class SolverResult:
    success: bool
    status: str
    tool_call_ids: list[str]
    execution: dict


class SolverRunner(Protocol):
    def __call__(self, task: dict, task_workspace: Path, selected_tools: list[dict]) -> SolverResult: ...


def initial_tool_specs():
    """Private checker/runner view. The controller gets catalog() instead, without implementation source."""
    return [{"id": name, "description": inspect.getdoc(tool.function),
             "interface": str(inspect.signature(tool.function)),
             "source": inspect.getsource(tool.function)} for name, tool in sorted(REGISTRY.items())]


def check_candidate(candidate, reserved_ids):
    if not isinstance(candidate, dict) or set(candidate) not in (
            {"id", "description", "source"}, {"id", "description", "files", "entrypoint"}):
        raise ValueError("New tool requires id/description and either source or files/entrypoint")
    if not re.fullmatch(r"new_[A-Za-z0-9_]+", candidate["id"]) or candidate["id"] in reserved_ids:
        raise ValueError("New tool requires a unique new_ ID")
    if not isinstance(candidate["description"], str) or not candidate["description"].strip():
        raise ValueError("New tool description is required")
    if "source" in candidate:
        sources = {"tool.py": candidate["source"]}
        entry_file, entry_function = "tool.py", "run"
    else:
        sources = candidate["files"]
        if not isinstance(sources, dict) or not sources:
            raise ValueError("files must be a nonempty relative-path to text mapping")
        if not isinstance(candidate["entrypoint"], str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*:[A-Za-z_][A-Za-z0-9_]*", candidate["entrypoint"]):
            raise ValueError("entrypoint must be module.path:function")
        module, entry_function = candidate["entrypoint"].split(":")
        entry_file = module.replace(".", "/") + ".py"
        if entry_file not in sources:
            raise ValueError("Entry module is absent from generated files")
    for relative, content in sources.items():
        # Validate relative paths before any write. Source is parsed, never executed here.
        safe_asset(Path.cwd(), relative)
        if not isinstance(content, str):
            raise ValueError("Generated file contents must be text")
        if relative.endswith(".py"):
            compile(content, "<generated-tool>", "exec", dont_inherit=True)
    tree = ast.parse(sources[entry_file])
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == entry_function]
    if len(functions) != 1:
        raise ValueError("New tool must define exactly one top-level run(arguments) function")
    args = functions[0].args
    if len(args.posonlyargs) + len(args.args) != 1 or args.vararg or args.kwarg or args.kwonlyargs:
        raise ValueError("run must accept one arguments object")
    return sources


def validate_similarity_result(value, references):
    if not isinstance(value, dict) or set(value) != {"high_similarity", "matched_tool_id", "reason"}:
        raise ValueError("Malformed similarity judgment")
    if type(value["high_similarity"]) is not bool or not isinstance(value["reason"], str) or not value["reason"].strip():
        raise ValueError("Similarity judgment requires a boolean and nonempty reason")
    if value["high_similarity"]:
        if value["matched_tool_id"] not in {t["id"] for t in references}:
            raise ValueError("Similarity rejection must identify a reference tool")
    elif value["matched_tool_id"] is not None:
        raise ValueError("Accepted tool must have null matched_tool_id")
    return value


def run_episode(*, task, actions: Iterable[ActionStep], similarity_judge, solver_runner: SolverRunner,
                public_root, scratch_root, run_id, variant, batch_id, sample_index, policy_version, seed):
    """Advance only until finish/rejection. No execution feedback is fed back to the controller.

    After rejecting a new tool, no further policy action or solver call is requested.
    Audit traces retain generated source; executable workspace copies are removed at exit.
    Infrastructure errors are recorded as unscored and must stop the outer training loop.
    """
    root = Path(scratch_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="episode_", dir=root)).resolve()
    if not workspace.is_relative_to(root) or workspace == root:
        raise ValueError("Invalid episode workspace")
    selected, created, checks, trace = {}, [], [], MainTrace()
    references = initial_tool_specs()
    base_by_id = {t["id"]: t for t in references}
    iterator = iter(actions)

    def finish(status, success, calls=None, execution=None):
        if status == "infrastructure_error":
            base, penalty, reward = None, 0.0, None
        else:
            base, penalty, reward = score(success, len(selected), status == "similarity_rejected")
        record = EpisodeRecord(
            run_id=run_id, variant=variant, split=task["split"], batch_id=batch_id,
            task_id=task["id"], domain=task["domain"], sample_index=sample_index,
            policy_version=policy_version, seed=seed, status=status, success=success,
            selected_tool_ids=list(selected), base_reward=base, tool_penalty=penalty,
            reward=reward, main_trace=trace, tool_call_ids=calls or [],
            similarity_checks=checks, execution=execution or {},
        )
        record.validate()
        return record

    try:
        task_dir = workspace / "task"
        task_dir.mkdir()
        for relative in task["files"]:
            source = safe_asset(public_root, relative)
            destination = safe_asset(task_dir, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        tools_dir = workspace / "generated_tools"
        tools_dir.mkdir()
        for step in iterator:
            # The model adapter must give a cumulative, exact trace, including the rejected action.
            step.trace.validate()
            if step.trace.output_token_ids[:len(trace.output_token_ids)] != trace.output_token_ids:
                raise RuntimeError("Controller trace is not a cumulative autoregressive prefix")
            if trace.prompt_token_ids and step.trace.prompt_token_ids != trace.prompt_token_ids:
                raise RuntimeError("Controller prompt changed within an episode")
            if step.trace.old_logprobs[:len(trace.old_logprobs)] != trace.old_logprobs:
                raise RuntimeError("Old-policy probabilities changed within an episode")
            trace = step.trace
            action = step.action
            try:
                if not isinstance(action, dict):
                    raise ValueError("Controller action must be an object")
                kind = action.get("type")
                if kind == "select":
                    if set(action) != {"type", "tool_id"} or action["tool_id"] not in base_by_id:
                        raise ValueError("Unknown initial tool or invalid select action")
                    selected[action["tool_id"]] = base_by_id[action["tool_id"]]
                elif kind == "create":
                    if variant == "trained_selection":
                        raise ValueError("Selection-only policy cannot create tools")
                    if set(action) != {"type", "tool"}:
                        raise ValueError("Invalid create action")
                    candidate = action["tool"]
                    candidate_files = check_candidate(candidate, set(base_by_id) | {t["id"] for t in created})
                elif kind == "finish":
                    if set(action) != {"type"}:
                        raise ValueError("Invalid finish action")
                else:
                    raise ValueError("Unknown controller action")
            except (SyntaxError, ValueError, TypeError, KeyError) as error:
                return finish("policy_invalid", False, execution={"error": str(error)})
            # Service calls are outside policy-format validation: a bad API response is not a failed task.
            if kind == "create":
                candidate_dir = tools_dir / candidate["id"]
                candidate_dir.mkdir()
                for relative, content in candidate_files.items():
                    target = safe_asset(candidate_dir, relative)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding="utf-8")
                judgment = validate_similarity_result(similarity_judge(candidate, references + created), references + created)
                checks.append({"candidate": dict(candidate), "reference_tool_ids": [t["id"] for t in references + created], **judgment})
                if judgment["high_similarity"]:
                    resolved_candidate = candidate_dir.resolve()
                    if resolved_candidate.parent != tools_dir.resolve():
                        raise RuntimeError("Unexpected generated-tool cleanup path")
                    shutil.rmtree(resolved_candidate)
                    return finish("similarity_rejected", False)
                created.append(dict(candidate))
                selected[candidate["id"]] = dict(candidate)
            elif kind == "finish":
                result = solver_runner(task, task_dir, list(selected.values()))
                if type(result.success) is not bool or result.status not in ("completed", "execution_failed"):
                    raise RuntimeError("Invalid trusted solver result")
                if set(result.tool_call_ids) - set(selected):
                    raise RuntimeError("Runner allowed an unselected tool")
                details = dict(result.execution)
                details["all_received_tools_called"] = set(selected) <= set(result.tool_call_ids)
                details["unused_tool_ids"] = sorted(set(selected) - set(result.tool_call_ids))
                # Prompt compliance is diagnostic only: no unapproved extra reward penalty.
                return finish(result.status, result.success, result.tool_call_ids, details)
        return finish("policy_invalid", False, execution={"error": "Controller ended before finish"})
    except Exception as error:
        return finish("infrastructure_error", None, execution={"error_type": type(error).__name__, "error": str(error)})
    finally:
        close = getattr(iterator, "close", None)
        try:
            if close:
                close()
        finally:
            resolved = workspace.resolve()
            if resolved != workspace or not resolved.is_relative_to(root) or resolved == root:
                raise RuntimeError("Refusing to clean an unexpected workspace path")
            shutil.rmtree(resolved)
