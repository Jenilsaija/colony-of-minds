"""
AtmaCore custom dual-tokenizer.
Handles natural language text and structured JSON data efficiently.
Wraps the trained Hugging Face BPE model when available, with character-rule fallbacks.
"""

import json
import os
import re
from typing import Dict, List, Optional

try:
    from tokenizers import Tokenizer as HFTokenizer
except ImportError:
    HFTokenizer = None


class AtmaCoreTokenizer:
    """
    AtmaCore custom tokenizer containing special tokens, structured symbol rules,
    and fallback token mappings to ensure 100% vocabulary coverage.
    """

    SPECIAL_TOKENS = {
        "<|pad|>": 0,
        "<|unk|>": 1,
        "<|user_prompt|>": 2,
        "<|verified_facts|>": 3,
        "<|end_facts|>": 4,
        "<|final_answer|>": 5,
        "<|missing_facts|>": 6,
        "<|uncertain|>": 7,
    }

    def __init__(self, vocab_file: Optional[str] = None):
        self.hf_tokenizer = None
        self.vocab: Dict[str, int] = dict(self.SPECIAL_TOKENS)
        self.inv_vocab: Dict[int, str] = {v: k for k, v in self.vocab.items()}

        # 1. Attempt to load Hugging Face trained tokenizer if it exists
        if vocab_file and HFTokenizer is not None:
            try:
                # If path exists and is a json file containing tokenizer model patterns
                if os.path.exists(vocab_file):
                    with open(vocab_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    if '"model"' in content and '"vocab"' in content:
                        self.hf_tokenizer = HFTokenizer.from_file(vocab_file)
                        self.vocab = self.hf_tokenizer.get_vocab()
                        self.inv_vocab = {v: k for k, v in self.vocab.items()}
            except Exception as e:
                print(f"[!] Error loading HF Tokenizer from '{vocab_file}': {e}. Falling back to default.")

        # 2. Build character-level fallback maps if HF model is not loaded
        if self.hf_tokenizer is None:
            current_id = len(self.vocab)
            for char_code in range(32, 127):
                char = chr(char_code)
                if char not in self.vocab:
                    self.vocab[char] = current_id
                    self.inv_vocab[current_id] = char
                    current_id += 1
            
            for char in ["\n", "\t", "\r"]:
                if char not in self.vocab:
                    self.vocab[char] = current_id
                    self.inv_vocab[current_id] = char
                    current_id += 1

        # Pre-tokenize regex to split JSON and natural language cleanly
        self.split_pattern = re.compile(
            r"(<\|.*?\|>)|"                # Special tokens
            r"([\{\}\[\]\:\,\"\'])|"       # JSON syntax
            r"(\d+(?:\.\d+)?)|"            # Numbers
            r"([a-zA-Z0-9_\-\.\@]+)|"      # Words and typical identifiers
            r"(\s+)|"                      # Whitespace
            r"(.)"                         # Any other character
        )

        if vocab_file and self.hf_tokenizer is None:
            self.load_vocab(vocab_file)

    def add_tokens(self, tokens: List[str]) -> int:
        """Adds custom words or strings to the tokenizer's vocabulary."""
        if self.hf_tokenizer is not None:
            return self.hf_tokenizer.add_tokens(tokens)

        added = 0
        current_id = max(self.vocab.values()) + 1
        for token in tokens:
            if token not in self.vocab:
                self.vocab[token] = current_id
                self.inv_vocab[current_id] = token
                current_id += 1
                added += 1
        return added

    def tokenize(self, text: str) -> List[str]:
        """Splits raw text into tokens according to AtmaCore rules."""
        if self.hf_tokenizer is not None:
            return self.hf_tokenizer.encode(text, add_special_tokens=False).tokens

        raw_matches = self.split_pattern.findall(text)
        tokens = []
        for match in raw_matches:
            token_str = next((g for g in match if g), "")
            if token_str:
                tokens.append(token_str)
        return tokens

    def encode(self, text: str, add_special_tokens: bool = False) -> List[int]:
        """Encodes string text into a list of token IDs."""
        if self.hf_tokenizer is not None:
            ids = self.hf_tokenizer.encode(text, add_special_tokens=False).ids
            if add_special_tokens:
                ids = [self.vocab["<|user_prompt|>"]] + ids + [self.vocab["<|final_answer|>"]]
            return ids

        tokens = self.tokenize(text)
        ids = []

        if add_special_tokens:
            ids.append(self.vocab["<|user_prompt|>"])

        for t in tokens:
            if t in self.vocab:
                ids.append(self.vocab[t])
            else:
                # Character fallback for OOV words
                for char in t:
                    if char in self.vocab:
                        ids.append(self.vocab[char])
                    else:
                        ids.append(self.vocab["<|unk|>"])

        if add_special_tokens:
            ids.append(self.vocab["<|final_answer|>"])

        return ids

    def decode(self, ids: List[int]) -> str:
        """Decodes token IDs back into text representation."""
        if self.hf_tokenizer is not None:
            return self.hf_tokenizer.decode(ids, skip_special_tokens=False)

        decoded_tokens = []
        for i in ids:
            t = self.inv_vocab.get(i, "<|unk|>")
            decoded_tokens.append(t)
        return "".join(decoded_tokens)

    def save_vocab(self, file_path: str) -> None:
        """Saves vocabulary as JSON file."""
        if self.hf_tokenizer is not None:
            self.hf_tokenizer.save(file_path)
            return

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.vocab, f, indent=2, ensure_ascii=False)

    def load_vocab(self, file_path: str) -> None:
        """Loads vocabulary from JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            self.vocab = json.load(f)
            self.inv_vocab = {v: k for k, v in self.vocab.items()}
            
    def format_input(self, prompt: str, facts_json: str) -> str:
        """Formats the input prompt and structured facts using AtmaCore special tokens."""
        return (
            f"<|user_prompt|>{prompt}"
            f"<|verified_facts|>{facts_json}<|end_facts|>"
            f"<|final_answer|>"
        )
