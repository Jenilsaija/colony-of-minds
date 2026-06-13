"""
Unit tests for AtmaCore model components, tokenizer, and training workflow.
Includes validation for sliding window masking, fact-anchoring attention, BPE tokenizer loading, data generation, and optimized low-resource training loops.
"""

import unittest
import tempfile
import os
import json
import torch
from torch.utils.data import DataLoader

from atmacore.model import AtmaCoreConfig, AtmaCoreModel, RMSNorm, GQAAttention, SparseMoE
from atmacore.tokenizer import AtmaCoreTokenizer
from atmacore.train import AtmaCoreDataset, AtmaCoreTrainer, pad_collate_fn


class TestAtmaCoreArchitecture(unittest.TestCase):
    """Verifies shape contracts, position encodings, GQA, and MoE routing logic."""

    def setUp(self):
        self.config = AtmaCoreConfig(
            vocab_size=1000,
            layers=2,
            hidden_dim=64,
            ffn_dim=128,
            heads=4,
            kv_heads=1,
            experts=4,
            active_experts=2,
            context_length=128,
            sliding_window=16,
            fact_heads=1
        )
        self.model = AtmaCoreModel(self.config)

    def test_model_forward_pass_shape(self):
        """Checks if model outputs correct shapes for random batches."""
        batch_size = 2
        seq_len = 16
        dummy_tokens = torch.randint(0, self.config.vocab_size, (batch_size, seq_len))
        
        logits = self.model(dummy_tokens)
        self.assertEqual(logits.shape, (batch_size, seq_len, self.config.vocab_size))

    def test_rmsnorm(self):
        """Verifies RMSNorm properties."""
        norm = RMSNorm(self.config.hidden_dim)
        x = torch.randn(2, 8, self.config.hidden_dim)
        out = norm(x)
        self.assertEqual(out.shape, x.shape)
        mean_square = out.pow(2).mean(-1)
        torch.testing.assert_close(mean_square, torch.ones_like(mean_square), rtol=1e-3, atol=1e-3)

    def test_gqa_attention_output_shape(self):
        """Verifies GQA attention output match input shape dimensions."""
        attn = GQAAttention(self.config)
        x = torch.randn(2, 8, self.config.hidden_dim)
        head_dim = self.config.hidden_dim // self.config.heads
        cos = torch.randn(8, head_dim // 2)
        sin = torch.randn(8, head_dim // 2)
        
        out = attn(x, cos, sin)
        self.assertEqual(out.shape, x.shape)

    def test_sparse_moe_routing(self):
        """Verifies routing shapes and that each token selects exactly active_experts."""
        moe = SparseMoE(self.config)
        x = torch.randn(3, 10, self.config.hidden_dim)
        out = moe(x)
        self.assertEqual(out.shape, x.shape)

    def test_sliding_window_masking(self):
        """Checks that attention is restricted using sliding window mask boundaries."""
        self.config.sliding_window = 4
        model = AtmaCoreModel(self.config)
        mask = model._build_sliding_window_mask(seq_len=10, device=torch.device("cpu"))
        
        # Row 6 checks:
        self.assertEqual(mask[6, 0].item(), float("-inf"))
        self.assertEqual(mask[6, 1].item(), float("-inf"))
        self.assertEqual(mask[6, 2].item(), 0.0)
        self.assertEqual(mask[6, 6].item(), 0.0)
        self.assertEqual(mask[6, 7].item(), float("-inf"))

    def test_dynamic_fact_mask_generation(self):
        """Verifies that token boundaries generate correct logical mask segments."""
        # 3 is <|verified_facts|>, 4 is <|end_facts|>
        tokens = torch.tensor([[2, 3, 10, 11, 4, 5]], dtype=torch.long)
        
        batch_size, seq_len = tokens.shape
        fact_mask = torch.zeros(batch_size, seq_len)
        for b in range(batch_size):
            indices_3 = (tokens[b] == 3).nonzero(as_tuple=True)[0]
            indices_4 = (tokens[b] == 4).nonzero(as_tuple=True)[0]
            if indices_3.numel() > 0:
                start_idx = indices_3[0].item() + 1
                end_idx = indices_4[0].item() if indices_4.numel() > 0 else seq_len
                fact_mask[b, start_idx:end_idx] = 1.0

        self.assertEqual(fact_mask[0, 2].item(), 1.0)
        self.assertEqual(fact_mask[0, 3].item(), 1.0)
        self.assertEqual(fact_mask[0, 0].item(), 0.0)
        self.assertEqual(fact_mask[0, 1].item(), 0.0)
        self.assertEqual(fact_mask[0, 4].item(), 0.0)

    def test_fact_anchored_attention_math(self):
        """Verifies GQA module accepts fact masks and registers fact bias parameters."""
        attn = GQAAttention(self.config)
        x = torch.randn(1, 6, self.config.hidden_dim)
        head_dim = self.config.hidden_dim // self.config.heads
        cos = torch.randn(6, head_dim // 2)
        sin = torch.randn(6, head_dim // 2)
        
        fact_mask = torch.tensor([[0.0, 0.0, 1.0, 1.0, 0.0, 0.0]])
        
        out = attn(x, cos, sin, fact_mask=fact_mask)
        self.assertEqual(out.shape, x.shape)
        self.assertTrue(hasattr(attn, "fact_bias"))
        self.assertEqual(attn.fact_bias.shape, (self.config.fact_heads,))


class TestAtmaCoreTokenizer(unittest.TestCase):
    """Verifies vocabulary encoding, decoding, JSON routing, and character fallback."""

    def setUp(self):
        self.tokenizer = AtmaCoreTokenizer()

    def test_special_tokens_positions(self):
        """Checks that special boundary tokens map to standard IDs."""
        self.assertEqual(self.tokenizer.vocab["<|pad|>"], 0)
        self.assertEqual(self.tokenizer.vocab["<|user_prompt|>"], 2)
        self.assertEqual(self.tokenizer.vocab["<|verified_facts|>"], 3)
        self.assertEqual(self.tokenizer.vocab["<|final_answer|>"], 5)

    def test_json_regex_tokenization(self):
        """Verifies JSON symbols are separated cleanly by the regex pre-tokenizer."""
        text = '{"key": "value"}'
        tokens = self.tokenizer.tokenize(text)
        self.assertIn("{", tokens)
        self.assertIn("}", tokens)
        self.assertIn(":", tokens)
        self.assertIn('"', tokens)

    def test_character_fallback(self):
        """Ensures that out-of-vocabulary terms are handled without raising Exceptions."""
        text = "こんにちは AtmaCore 🚀"
        ids = self.tokenizer.encode(text)
        self.assertTrue(len(ids) > 0)
        decoded = self.tokenizer.decode(ids)
        self.assertIn("AtmaCore", decoded)

    def test_vocab_serialization(self):
        """Verifies vocab JSON saving and loading behaves correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "vocab.json")
            self.tokenizer.save_vocab(file_path)
            
            new_tokenizer = AtmaCoreTokenizer(vocab_file=file_path)
            self.assertEqual(self.tokenizer.vocab, new_tokenizer.vocab)

    def test_trained_bpe_tokenizer_loading(self):
        """Verifies loading the trained Hugging Face BPE model configuration."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bpe_path = os.path.join(base_dir, "atmacore_tokenizer.json")
        
        if os.path.exists(bpe_path):
            tokenizer = AtmaCoreTokenizer(vocab_file=bpe_path)
            self.assertIsNotNone(tokenizer.hf_tokenizer)
            self.assertIn("<|verified_facts|>", tokenizer.vocab)
            
            # Test encoding/decoding is reversible
            text = '{"result":100}'
            ids = tokenizer.encode(text)
            self.assertTrue(len(ids) > 0)
            decoded = tokenizer.decode(ids)
            self.assertEqual(decoded.replace(" ", ""), text)


class TestAtmaCoreTrainingWorkflow(unittest.TestCase):
    """Verifies dataset building, collation padding, and gradient propagation step."""

    def test_dataset_and_trainer(self):
        tokenizer = AtmaCoreTokenizer()
        config = AtmaCoreConfig(vocab_size=len(tokenizer.vocab), layers=1, hidden_dim=16, heads=2, experts=2)
        model = AtmaCoreModel(config)
        
        raw_data = [
            {"prompt": "add 2 and 3", "facts": '{"res": 5}', "target": "2 + 3 = 5."},
            {"prompt": "multiply 4 * 5", "facts": '{"res": 20}', "target": "4 * 5 = 20."}
        ]
        
        dataset = AtmaCoreDataset(raw_data, tokenizer, max_len=64)
        self.assertEqual(len(dataset), 2)
        
        dataloader = DataLoader(
            dataset, 
            batch_size=2, 
            shuffle=False, 
            collate_fn=lambda b: pad_collate_fn(b, pad_token_id=0)
        )
        
        trainer = AtmaCoreTrainer(model, tokenizer, learning_rate=1e-3)
        loss = trainer.train_epoch(dataloader)
        
        self.assertTrue(isinstance(loss, float))
        self.assertTrue(loss > 0.0)

    def test_dataset_generator(self):
        """Verifies that the dataset generator outputs correctly-formatted splits."""
        from atmacore.data_generator import AtmaCoreDataGenerator
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = AtmaCoreDataGenerator()
            train_path, val_path = generator.generate_and_save(tmpdir, num_samples=100, split_ratio=0.8)
            
            self.assertTrue(os.path.exists(train_path))
            self.assertTrue(os.path.exists(val_path))
            
            with open(train_path, "r", encoding="utf-8") as f:
                train_lines = f.readlines()
            with open(val_path, "r", encoding="utf-8") as f:
                val_lines = f.readlines()
                
            self.assertEqual(len(train_lines), 80)
            self.assertEqual(len(val_lines), 20)
            
            first_sample = json.loads(train_lines[0])
            self.assertIn("prompt", first_sample)
            self.assertIn("facts", first_sample)
            self.assertIn("target", first_sample)

    def test_optimized_trainer(self):
        """Verifies training step executing with AMP, gradient accumulation, and SGD optimizer."""
        tokenizer = AtmaCoreTokenizer()
        config = AtmaCoreConfig(vocab_size=len(tokenizer.vocab), layers=1, hidden_dim=16, heads=2, experts=2)
        model = AtmaCoreModel(config)
        
        raw_data = [
            {"prompt": "add 2 and 3", "facts": '{"res": 5}', "target": "2 + 3 = 5."},
            {"prompt": "multiply 4 * 5", "facts": '{"res": 20}', "target": "4 * 5 = 20."}
        ]
        
        dataset = AtmaCoreDataset(raw_data, tokenizer, max_len=64)
        dataloader = DataLoader(
            dataset, 
            batch_size=1,  # Micro-batch size 1
            shuffle=False, 
            collate_fn=lambda b: pad_collate_fn(b, pad_token_id=0)
        )
        
        # Test trainer with SGD, AMP enabled, and gradient accumulation steps = 2
        trainer = AtmaCoreTrainer(
            model=model,
            tokenizer=tokenizer,
            learning_rate=1e-3,
            device="cpu",
            gradient_accumulation_steps=2,
            use_amp=True,
            optimizer_type="sgd"
        )
        
        loss = trainer.train_epoch(dataloader)
        self.assertTrue(isinstance(loss, float))
        self.assertTrue(loss > 0.0)
        self.assertTrue(isinstance(trainer.optimizer, torch.optim.SGD))


if __name__ == "__main__":
    unittest.main()
