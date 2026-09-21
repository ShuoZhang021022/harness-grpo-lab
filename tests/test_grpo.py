import unittest
import torch

from harness_grpo.grpo import group_advantages, token_grpo_loss


class GrpoGradientTest(unittest.TestCase):
    def test_groups_are_centered_per_question_and_constant_groups_are_zero(self):
        rewards = torch.tensor([[1., 1., -1., -1., -1., -1., -1., -1.], [-1.] * 8])
        advantages = group_advantages(rewards, standardize=True, std_correction=0, epsilon=1e-8)
        self.assertTrue(torch.allclose(advantages.mean(dim=1), torch.zeros(2), atol=1e-7))
        self.assertTrue((advantages[0, :2] > 0).all())
        self.assertTrue((advantages[0, 2:] < 0).all())
        self.assertEqual(advantages[1].abs().sum().item(), 0)

    def test_gradient_only_on_main_tokens_old_and_reward_detached(self):
        current = torch.tensor([[-.2, -.3, -.4, -.5], [-.2, -.3, -.4, -.5]], requires_grad=True)
        old = current.detach().clone().requires_grad_()
        advantages = torch.tensor([1., -1.], requires_grad=True)
        mask = torch.tensor([[False, True, True, False], [False, True, True, False]])
        loss = token_grpo_loss(current, old, advantages, mask, clip_epsilon=.2, kl_beta=0,
                               reference_logprobs=None, normalization="sequence_mean")
        loss.backward()
        self.assertTrue((current.grad[~mask] == 0).all())
        self.assertTrue((current.grad[0, 1:3] < 0).all())
        self.assertTrue((current.grad[1, 1:3] > 0).all())
        self.assertIsNone(old.grad)
        self.assertIsNone(advantages.grad)

    def test_clipping_stops_positive_advantage_beyond_upper_ratio(self):
        current = torch.tensor([[-.1]], requires_grad=True)
        old = torch.tensor([[-1.]])
        loss = token_grpo_loss(current, old, torch.tensor([1.]), torch.tensor([[True]]),
                               clip_epsilon=.2, kl_beta=0, reference_logprobs=None, normalization="sequence_mean")
        loss.backward()
        self.assertEqual(current.grad.item(), 0)

    def test_tool_cost_can_differentiate_all_successful_trajectories(self):
        rewards = torch.tensor([[.99, .98, .97, .96, .95, .94, .93, .92]])
        advantages = group_advantages(rewards, standardize=True, std_correction=0, epsilon=1e-8)
        self.assertGreater(advantages[0, 0].item(), 0)
        self.assertLess(advantages[0, -1].item(), 0)

    def test_nonzero_kl_cannot_silently_drop_reference(self):
        with self.assertRaises(ValueError):
            token_grpo_loss(torch.tensor([[-.1]]), torch.tensor([[-.1]]), torch.tensor([1.]), torch.tensor([[True]]),
                            clip_epsilon=.2, kl_beta=.01, reference_logprobs=None, normalization="sequence_mean")


if __name__ == "__main__":
    unittest.main()
