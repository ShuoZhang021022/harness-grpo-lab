import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import torch

from harness_grpo.lora_update import LoRABatchUpdater, output_logprobs
from harness_grpo.records import EpisodeRecord, MainTrace, score


class TinyPolicy(torch.nn.Module):
    """Handwritten numerical fixture, not a real LLM or a reported experiment."""
    def __init__(self):
        super().__init__()
        self.embedding = torch.nn.Embedding(4, 3)
        self.embedding.weight.requires_grad_(False)
        self.lora_logits = torch.nn.Parameter(torch.zeros(4))

    def get_input_embeddings(self):
        return self.embedding

    def forward(self, input_ids, **kwargs):
        return SimpleNamespace(logits=self.lora_logits.reshape(1, 1, -1).expand(input_ids.shape[0], input_ids.shape[1], -1))

    def save_pretrained(self, destination):
        torch.save(self.state_dict(), Path(destination) / "fixture.pt")


class LoRAUpdateTest(unittest.TestCase):
    def test_all_800_records_drive_one_step_only_lora_changes(self):
        model = TinyPolicy()
        initial_base = model.embedding.weight.detach().clone()
        optimizer = torch.optim.SGD([model.lora_logits], lr=.1)
        records = []
        for question in range(100):
            for index in range(8):
                output = [2 if index < 4 else 3]
                old = output_logprobs(model, [1], output).detach().flatten().tolist()
                base, penalty, reward = score(index < 4, 1)
                records.append(EpisodeRecord("numeric_fixture", "trained_full", "train", 1, f"q{question}", "math", index,
                               "v0", 7, "completed", index < 4, ["integer_gcd"], base, penalty, reward,
                               MainTrace([1], output, old, "numeric fixture")))
        with tempfile.TemporaryDirectory() as directory:
            updater = LoRABatchUpdater(model, optimizer, directory, clip_epsilon=.2, std_correction=0, advantage_epsilon=1e-8)
            result = updater(records, "v0", 1)
            self.assertTrue((Path(result) / "update.json").is_file())
            self.assertGreater(model.lora_logits[2].item(), 0)
            self.assertLess(model.lora_logits[3].item(), 0)
            self.assertTrue(torch.equal(initial_base, model.embedding.weight))

    def test_unfrozen_base_is_rejected(self):
        model = TinyPolicy()
        model.embedding.weight.requires_grad_(True)
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            LoRABatchUpdater(model, torch.optim.SGD(model.parameters(), lr=.1), directory,
                             clip_epsilon=.2, std_correction=0, advantage_epsilon=1e-8)


if __name__ == "__main__":
    unittest.main()
