"""
Training script for the AtmaCore custom BPE tokenizer.
Generates a representative synthetic corpus of mixed JSON and natural language
and trains a tokenizer with structured isolation rules.
"""

import os
import json
import random
from typing import List

from tokenizers import Tokenizer
from tokenizers.models import BPE
from tokenizers.pre_tokenizers import Split
from tokenizers.trainers import BpeTrainer


def generate_synthetic_corpus(file_path: str, num_samples: int = 15000) -> None:
    """Generates a text corpus combining typical prompt-fact-synthesis interactions."""
    templates = [
        ("calculate {expr}", '{{"type": "calculation", "expression": "{expr}", "result": {res}}}', "The result of {expr} is {res}."),
        ("greet the user in {lang}", '{{"type": "language", "value": "{lang}"}}', "Hello and welcome in {lang}!"),
        ("check code for {lang}", '{{"type": "code_language", "language": "{lang}"}}, {{"type": "syntax_check", "language": "{lang}", "valid": true}}', "Code syntax in {lang} is valid."),
        ("store preference {key} as {val}", '{{"type": "stored_preference", "key": "{key}", "value": "{val}"}}', "Successfully remembered your {key} preference."),
        ("retrieve my {key}", '{{"type": "retrieved_preference", "key": "{key}", "value": "{val}"}}', "I recalled your {key} which is {val}."),
    ]

    math_exprs = ["45 * 123", "18% of 25000", "2 + 2", "500 / 5", "100 - 35"]
    math_results = [5535, 4500, 4, 100, 65]
    languages = ["English", "Python", "Javascript", "Rust", "C++", "Java"]
    pref_keys = ["theme", "username", "notifications", "workspace", "font_size"]
    pref_vals = ["dark", "Jenil", "enabled", "desktop", "14px"]

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        for _ in range(num_samples):
            # Pick a template
            tpl_prompt, tpl_facts, tpl_target = random.choice(templates)
            
            # Format inputs randomly
            expr_idx = random.randint(0, len(math_exprs)-1)
            lang = random.choice(languages)
            key_idx = random.randint(0, len(pref_keys)-1)
            
            prompt = tpl_prompt.format(
                expr=math_exprs[expr_idx],
                lang=lang,
                key=pref_keys[key_idx],
                val=pref_vals[key_idx]
            )
            facts = tpl_facts.format(expr=math_exprs[expr_idx], res=math_results[expr_idx], lang=lang, key=pref_keys[key_idx], val=pref_vals[key_idx])
            target = tpl_target.format(expr=math_exprs[expr_idx], res=math_results[expr_idx], lang=lang, key=pref_keys[key_idx], val=pref_vals[key_idx])
            
            # Format using standard AtmaCore special boundary tags
            full_line = (
                f"<|user_prompt|>{prompt}"
                f"<|verified_facts|>{facts}<|end_facts|>"
                f"<|final_answer|>{target}"
            )
            f.write(full_line + "\n")


def train_atmacore_tokenizer(corpus_path: str, output_dir: str, vocab_size: int = 32000) -> Tokenizer:
    """Trains a Byte-Pair Encoding (BPE) model with custom JSON pre-tokenization rules."""
    os.makedirs(output_dir, exist_ok=True)

    # Initialize empty BPE model
    tokenizer = Tokenizer(BPE(unk_token="<|unk|>"))

    # Regex Pre-tokenizer: isolates brackets, braces, colons, quotes, commas, numbers, and spaces
    # so that BPE merges are restricted strictly to words/subwords, preventing symbol merges.
    # Group 1: JSON syntax characters
    # Group 2: Whitespace
    # Group 3: Word boundaries
    split_regex = r"([\{\}\[\]\:\,\"\'])|(\s+)|([a-zA-Z0-9_\-\.\@]+)"
    tokenizer.pre_tokenizer = Split(pattern=split_regex, behavior="isolated")

    # Configure the BPE Trainer
    special_tokens = [
        "<|pad|>",
        "<|unk|>",
        "<|user_prompt|>",
        "<|verified_facts|>",
        "<|end_facts|>",
        "<|final_answer|>",
        "<|missing_facts|>",
        "<|uncertain|>"
    ]
    trainer = BpeTrainer(
        vocab_size=vocab_size,
        special_tokens=special_tokens,
        initial_alphabet=[]
    )

    # Train BPE
    print(f"[*] Training AtmaCore custom BPE tokenizer on {corpus_path}...")
    tokenizer.train(files=[corpus_path], trainer=trainer)

    # Save tokenizer configuration json
    save_path = os.path.join(output_dir, "atmacore_tokenizer.json")
    tokenizer.save(save_path)
    print(f"[x] Tokenizer model successfully trained and saved to {save_path}")

    return tokenizer


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    corpus_file = os.path.join(base_dir, "corpus_scratch.txt")
    
    # Generate mock training dataset
    generate_synthetic_corpus(corpus_file, num_samples=1000)
    
    # Train BPE
    train_atmacore_tokenizer(corpus_file, base_dir, vocab_size=5000)
