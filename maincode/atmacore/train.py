"""
AtmaCore training harness.
Implements the training dataset, optimized training loop (mixed-precision, gradient accumulation),
alternative optimizers, and weight serialization.
"""

import os
from typing import List, Dict, Any, Tuple
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

from atmacore.model import AtmaCoreModel, AtmaCoreConfig
from atmacore.tokenizer import AtmaCoreTokenizer


class AtmaCoreDataset(Dataset):
    """
    Standard PyTorch dataset mapping list of raw inputs to tokenized, padded tensors.
    """
    def __init__(self, data: List[Dict[str, str]], tokenizer: AtmaCoreTokenizer, max_len: int = 1024):
        self.tokenizer = tokenizer
        self.max_len = max_len
        self.samples = []

        for item in data:
            prompt = item.get("prompt", "")
            facts = item.get("facts", "[]")
            target = item.get("target", "")

            # Formulate the formatted full sequence:
            # <|user_prompt|>prompt<|verified_facts|>facts<|end_facts|><|final_answer|>target
            full_input_str = self.tokenizer.format_input(prompt, facts) + target
            
            # Encode tokens
            token_ids = self.tokenizer.encode(full_input_str)
            
            # Enforce max context length limit
            if len(token_ids) > self.max_len:
                token_ids = token_ids[:self.max_len]
                
            self.samples.append(token_ids)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        tokens = self.samples[idx]
        
        # In autoregressive training:
        inputs = torch.tensor(tokens[:-1], dtype=torch.long)
        labels = torch.tensor(tokens[1:], dtype=torch.long)
        return inputs, labels


def pad_collate_fn(batch: List[Tuple[torch.Tensor, torch.Tensor]], pad_token_id: int = 0):
    """Collates a list of samples into padded mini-batch tensors."""
    inputs, labels = zip(*batch)
    
    # Pad sequences to match the longest element in this batch
    inputs_padded = nn.utils.rnn.pad_sequence(inputs, batch_first=True, padding_value=pad_token_id)
    labels_padded = nn.utils.rnn.pad_sequence(labels, batch_first=True, padding_value=pad_token_id)
    
    return inputs_padded, labels_padded


class AtmaCoreTrainer:
    """Trainer for the custom AtmaCore model supporting extreme resource-saving techniques."""
    def __init__(
        self,
        model: AtmaCoreModel,
        tokenizer: AtmaCoreTokenizer,
        learning_rate: float = 5e-4,
        device: str = "cpu",
        gradient_accumulation_steps: int = 8,
        use_amp: bool = True,
        optimizer_type: str = "adamw"
    ):
        self.model = model.to(device)
        self.tokenizer = tokenizer
        self.device = device
        self.gradient_accumulation_steps = gradient_accumulation_steps
        
        self.device_type = "cuda" if "cuda" in str(device) else "cpu"
        self.use_amp = use_amp
        # GradScaler is only used on CUDA with float16
        self.scaler = torch.amp.GradScaler("cuda") if (self.use_amp and self.device_type == "cuda") else None

        # Configure selected optimizer
        opt_type = optimizer_type.lower()
        if opt_type == "sgd":
            # SGD with momentum is a very memory-light optimizer choice (no running statistics)
            self.optimizer = torch.optim.SGD(self.model.parameters(), lr=learning_rate, momentum=0.9, weight_decay=0.01)
        elif opt_type == "adafactor":
            # Adafactor is extremely memory efficient, but falls back to AdamW if transformers is missing
            try:
                from transformers import Adafactor
                self.optimizer = Adafactor(
                    self.model.parameters(), 
                    lr=learning_rate, 
                    relative_step=False, 
                    weight_decay=0.01
                )
            except ImportError:
                self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=learning_rate, weight_decay=0.01)
        else: # default: adamw
            self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=learning_rate, weight_decay=0.01)

        # CrossEntropyLoss with ignore_index pointing to pad tokens
        self.loss_fn = nn.CrossEntropyLoss(ignore_index=self.tokenizer.SPECIAL_TOKENS["<|pad|>"])

    def train_epoch(self, dataloader: DataLoader) -> float:
        """Trains the model for one epoch using AMP and gradient accumulation."""
        self.model.train()
        total_loss = 0.0
        
        self.optimizer.zero_grad()
        
        for batch_idx, (inputs, labels) in enumerate(dataloader):
            inputs = inputs.to(self.device)
            labels = labels.to(self.device)

            # Determine precision type for AMP (float16 on CUDA, bfloat16 on CPU)
            amp_dtype = torch.float16 if self.device_type == "cuda" else torch.bfloat16

            if self.use_amp:
                with torch.amp.autocast(device_type=self.device_type, dtype=amp_dtype):
                    logits = self.model(inputs)
                    loss = self.loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))
                    # Scale loss by gradient accumulation steps
                    loss = loss / self.gradient_accumulation_steps
                
                if self.scaler is not None:
                    self.scaler.scale(loss).backward()
                else:
                    loss.backward()
            else:
                logits = self.model(inputs)
                loss = self.loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))
                loss = loss / self.gradient_accumulation_steps
                loss.backward()

            total_loss += loss.item() * self.gradient_accumulation_steps

            # Perform optimizer step at accumulation boundaries
            if (batch_idx + 1) % self.gradient_accumulation_steps == 0 or (batch_idx + 1) == len(dataloader):
                if self.use_amp and self.scaler is not None:
                    self.scaler.unscale_(self.optimizer)
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                else:
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                    self.optimizer.step()
                
                self.optimizer.zero_grad()
            
        return total_loss / len(dataloader) if len(dataloader) > 0 else 0.0

    def evaluate(self, dataloader: DataLoader) -> float:
        """Evaluates model validation loss."""
        self.model.eval()
        total_loss = 0.0
        
        with torch.no_grad():
            for inputs, labels in dataloader:
                inputs = inputs.to(self.device)
                labels = labels.to(self.device)
                
                if self.use_amp:
                    amp_dtype = torch.float16 if self.device_type == "cuda" else torch.bfloat16
                    with torch.amp.autocast(device_type=self.device_type, dtype=amp_dtype):
                        logits = self.model(inputs)
                        loss = self.loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))
                else:
                    logits = self.model(inputs)
                    loss = self.loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))
                    
                total_loss += loss.item()
                
        return total_loss / len(dataloader) if len(dataloader) > 0 else 0.0

    def save_checkpoint(self, dir_path: str, name: str = "checkpoint.pt") -> None:
        """Saves weights and optimizer state to directory."""
        os.makedirs(dir_path, exist_ok=True)
        checkpoint = {
            "model_state": self.model.state_dict(),
            "optimizer_state": self.optimizer.state_dict(),
            "config": self.model.config
        }
        torch.save(checkpoint, os.path.join(dir_path, name))
        self.tokenizer.save_vocab(os.path.join(dir_path, "vocab.json"))

    def load_checkpoint(self, file_path: str) -> None:
        """Loads weights and configurations from checkpoint file."""
        checkpoint = torch.load(file_path, map_location=self.device)
        self.model.load_state_dict(checkpoint["model_state"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state"])
