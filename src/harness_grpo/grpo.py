"""Explicit original-style clipped token GRPO objective; no implicit optimizer or regularizers."""


def group_advantages(rewards, *, standardize, std_correction, epsilon):
    """rewards shape [questions, group_size]. Groups never pool different questions."""
    import torch
    if rewards.ndim != 2 or rewards.shape[1] < 2 or not torch.isfinite(rewards).all():
        raise ValueError("Require finite grouped rewards with at least two samples per question")
    if type(standardize) is not bool or std_correction not in (0, 1) or epsilon <= 0:
        raise ValueError("Advantage normalization choices must be explicit")
    centered = rewards - rewards.mean(dim=1, keepdim=True)
    if standardize:
        centered = centered / (rewards.std(dim=1, keepdim=True, correction=std_correction) + epsilon)
    return centered.detach()


def token_grpo_loss(current_logprobs, old_logprobs, advantages, output_mask, *,
                    clip_epsilon, kl_beta, reference_logprobs, normalization):
    """All arguments explicit. Inputs [sequences,tokens], advantages [sequences].

    output_mask must include ALL main-agent output tokens, including generated code;
    it excludes prompts, padding, solver tokens, judge tokens and environment outputs.
    This supports the selected clipped objective plus optional sampled KL estimator;
    it does not silently add length penalties, entropy bonuses or auxiliary losses.
    """
    import torch
    if not 0 < clip_epsilon < 1 or kl_beta < 0:
        raise ValueError("Invalid clipping or KL coefficient")
    if normalization not in ("sequence_mean", "token_mean"):
        raise ValueError("Choose an explicit sequence_mean or token_mean loss")
    if current_logprobs.shape != old_logprobs.shape or output_mask.shape != current_logprobs.shape or current_logprobs.ndim != 2:
        raise ValueError("Log probability/mask shape mismatch")
    if advantages.shape != (current_logprobs.shape[0],) or output_mask.dtype != torch.bool:
        raise ValueError("Advantages shape or mask type mismatch")
    if not output_mask.any(dim=1).all():
        raise ValueError("Every trajectory must contain main-agent output tokens")
    if not torch.isfinite(current_logprobs[output_mask]).all() or not torch.isfinite(old_logprobs[output_mask]).all():
        raise ValueError("Nonfinite active log probabilities")
    if not torch.isfinite(advantages).all():
        raise ValueError("Nonfinite advantages")
    # Zero masked values before exp, so irrelevant padding cannot create NaN gradients.
    delta = torch.where(output_mask, current_logprobs - old_logprobs.detach(), 0.0)
    ratio = delta.exp()
    advantage = advantages.detach().unsqueeze(1)
    objective = torch.minimum(ratio * advantage, ratio.clamp(1 - clip_epsilon, 1 + clip_epsilon) * advantage)
    if kl_beta:
        if reference_logprobs is None or reference_logprobs.shape != current_logprobs.shape:
            raise ValueError("Nonzero KL requires explicit frozen reference probabilities")
        if not torch.isfinite(reference_logprobs[output_mask]).all():
            raise ValueError("Nonfinite reference probabilities")
        reference_delta = torch.where(output_mask, reference_logprobs.detach() - current_logprobs, 0.0)
        objective = objective - kl_beta * (reference_delta.exp() - reference_delta - 1)
    losses = torch.where(output_mask, -objective, 0.0)
    if not torch.isfinite(losses).all():
        raise ValueError("Nonfinite GRPO loss; do not silently clamp or skip samples")
    if normalization == "sequence_mean":
        return (losses.sum(dim=1) / output_mask.sum(dim=1)).mean()
    return losses.sum() / output_mask.sum()
