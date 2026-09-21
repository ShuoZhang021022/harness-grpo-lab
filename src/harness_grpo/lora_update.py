"""Single-process reference LoRA updater with one optimizer step per 800 rollouts.

Distributed 8-GPU execution is deliberately not claimed by this reference component.
Model loading, rollout generation, external LLM calls and isolated execution are separate adapters.
"""

from collections import defaultdict
from pathlib import Path

from .grpo import group_advantages, token_grpo_loss


def output_logprobs(model, prompt_ids, output_ids):
    """Teacher-force the main agent's exact sampled tokens, including generated tool code."""
    import torch
    if not prompt_ids or not output_ids:
        raise ValueError("Need both prompt and main-agent output tokens")
    device = model.get_input_embeddings().weight.device
    token_ids = torch.tensor([prompt_ids + output_ids], dtype=torch.long, device=device)
    # Every suffix token is predicted by the preceding position; no loss on prompt tokens.
    logits = model(input_ids=token_ids, attention_mask=torch.ones_like(token_ids), use_cache=False).logits
    selected = logits[:, len(prompt_ids) - 1:-1, :].float()
    targets = token_ids[:, len(prompt_ids):]
    return selected.log_softmax(dim=-1).gather(-1, targets.unsqueeze(-1)).squeeze(-1)


class LoRABatchUpdater:
    def __init__(self, model, optimizer, checkpoint_root, *, clip_epsilon, std_correction, advantage_epsilon):
        self.model, self.optimizer = model, optimizer
        self.checkpoint_root = Path(checkpoint_root)
        self.clip_epsilon, self.std_correction, self.advantage_epsilon = clip_epsilon, std_correction, advantage_epsilon
        trainable = [(name, p) for name, p in model.named_parameters() if p.requires_grad]
        if not trainable or any("lora_" not in name for name, _ in trainable):
            raise ValueError("Only LoRA parameters may be trainable")
        optimizer_ids = {id(p) for group in optimizer.param_groups for p in group["params"]}
        if optimizer_ids != {id(p) for _, p in trainable}:
            raise ValueError("Optimizer must contain exactly the trainable LoRA parameters")
        if any(group.get("weight_decay", 0) != 0 for group in optimizer.param_groups):
            raise ValueError("Confirmed setup does not add weight decay")

    def __call__(self, records, old_version, batch_id):
        import torch
        if len(records) != 800:
            raise ValueError("A full update requires all 100 questions x 8 trajectories")
        grouped = defaultdict(list)
        identities = {(r.run_id, r.variant, r.seed) for r in records}
        if len(identities) != 1:
            raise ValueError("A training batch cannot mix runs, variants or seeds")
        for record in records:
            record.validate()
            if record.policy_version != old_version or record.batch_id != batch_id or record.split != "train" or record.reward is None:
                raise ValueError("Wrong policy/batch/split or unscored training trajectory")
            if not record.main_trace.prompt_token_ids or not record.main_trace.output_token_ids:
                raise ValueError("LoRA updates require complete main-agent token traces")
            grouped[record.task_id].append(record)
        if len(grouped) != 100:
            raise ValueError("Expected exactly 100 distinct questions")
        ordered = []
        for task_id in sorted(grouped):
            group = sorted(grouped[task_id], key=lambda r: r.sample_index)
            if [r.sample_index for r in group] != list(range(8)):
                raise ValueError("Each question needs exactly samples 0 through 7")
            if any(r.main_trace.prompt_token_ids != group[0].main_trace.prompt_token_ids for r in group):
                raise ValueError("A GRPO group must share an identical main-agent prompt")
            ordered.extend(group)
        rewards = torch.tensor([r.reward for r in ordered], dtype=torch.float32).reshape(100, 8)
        advantages = group_advantages(rewards, standardize=True, std_correction=self.std_correction,
                                      epsilon=self.advantage_epsilon).reshape(-1)
        # eval() disables model/adapter dropout while gradients remain enabled.
        previous_mode = self.model.training
        self.model.eval()
        self.optimizer.zero_grad(set_to_none=True)
        total_loss = 0.0
        try:
            for record, advantage in zip(ordered, advantages):
                trace = record.main_trace
                current = output_logprobs(self.model, trace.prompt_token_ids, trace.output_token_ids)
                old = torch.tensor([trace.old_logprobs], dtype=current.dtype, device=current.device)
                mask = torch.ones_like(current, dtype=torch.bool)
                loss = token_grpo_loss(current, old, advantage.reshape(1).to(current.device), mask,
                                       clip_epsilon=self.clip_epsilon, kl_beta=0.0,
                                       reference_logprobs=None, normalization="sequence_mean") / 800
                loss.backward()
                total_loss += loss.detach().item()
            for name, parameter in self.model.named_parameters():
                if parameter.requires_grad and parameter.grad is not None and not torch.isfinite(parameter.grad).all():
                    raise FloatingPointError(f"Nonfinite gradient in {name}; batch not updated")
            self.optimizer.step()
        except Exception:
            self.optimizer.zero_grad(set_to_none=True)
            raise
        finally:
            self.model.train(previous_mode)
        destination = self.checkpoint_root / f"batch_{batch_id:03d}"
        destination.mkdir(parents=True, exist_ok=False)
        self.model.save_pretrained(destination)
        torch.save(self.optimizer.state_dict(), destination / "optimizer_state.pt")
        import json
        (destination / "update.json").write_text(json.dumps({
            "old_version": old_version, "batch_id": batch_id, "optimizer_steps": 1,
            "rollouts": 800, "optimizer_microbatch_size": 1, "mean_loss": total_loss,
            "clip_epsilon": self.clip_epsilon, "kl_beta": 0.0,
            "std_correction": self.std_correction, "advantage_epsilon": self.advantage_epsilon,
            "loss_normalization": "sequence_mean", "tokens": "all_main_agent_outputs",
        }, indent=2), encoding="utf-8")
        return str(destination.resolve())
