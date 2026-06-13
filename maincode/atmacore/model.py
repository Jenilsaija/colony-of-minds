"""
AtmaCore custom micro-model architecture.
Includes Sparse Mixture-of-Experts (MoE), Grouped-Query Attention (GQA), 
Rotary Position Embeddings (RoPE), RMSNorm, Sliding Window Masking, 
and learnable Fact-Anchored Attention Heads.
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class AtmaCoreConfig:
    """Configuration class for the AtmaCore custom model."""
    vocab_size: int = 32000
    layers: int = 12
    hidden_dim: int = 512
    ffn_dim: int = 2048
    heads: int = 8
    kv_heads: int = 2            # Grouped-Query Attention: 8 query heads, 2 key/value heads
    experts: int = 4           # Sparse MoE: 4 experts in total
    active_experts: int = 2    # Top-2 routing per token
    context_length: int = 1024
    norm_eps: float = 1e-6
    sliding_window: int = 256  # Sliding Window Attention size
    fact_heads: int = 2        # Number of dedicated fact-anchoring attention heads


class RMSNorm(nn.Module):
    """Root Mean Square Layer Normalization."""
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        variance = x.pow(2).mean(-1, keepdim=True)
        return x * torch.rsqrt(variance + self.eps) * self.weight


def precompute_rope_freqs(dim: int, end: int, theta: float = 10000.0) -> Tuple[torch.Tensor, torch.Tensor]:
    """Precomputes cosmic frequencies for Rotary Position Embeddings (RoPE)."""
    freqs = 1.0 / (theta ** (torch.arange(0, dim, 2)[: (dim // 2)].float() / dim))
    t = torch.arange(end, dtype=torch.float32)
    freqs = torch.outer(t, freqs)
    cos = torch.cos(freqs)
    sin = torch.sin(freqs)
    return cos, sin


def apply_rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    """Applies Rotary Position Embeddings (RoPE) to a tensor."""
    cos = cos.unsqueeze(1)
    sin = sin.unsqueeze(1)

    x_even = x[..., 0::2]
    x_odd = x[..., 1::2]

    rot_x_even = x_even * cos - x_odd * sin
    rot_x_odd = x_even * sin + x_odd * cos

    out = torch.stack([rot_x_even, rot_x_odd], dim=-1).flatten(-2)
    return out


class GQAAttention(nn.Module):
    """
    Grouped-Query Attention (GQA) module with sliding window and query-key projection.
    Uses RoPE for position embeddings and learnable fact-anchored head routing.
    """
    def __init__(self, config: AtmaCoreConfig):
        super().__init__()
        self.heads = config.heads
        self.kv_heads = config.kv_heads
        self.hidden_dim = config.hidden_dim
        self.head_dim = self.hidden_dim // self.heads
        self.num_queries_per_kv = self.heads // self.kv_heads
        self.fact_heads_count = config.fact_heads

        self.q_proj = nn.Linear(self.hidden_dim, self.heads * self.head_dim, bias=False)
        self.k_proj = nn.Linear(self.hidden_dim, self.kv_heads * self.head_dim, bias=False)
        self.v_proj = nn.Linear(self.hidden_dim, self.kv_heads * self.head_dim, bias=False)
        self.o_proj = nn.Linear(self.heads * self.head_dim, self.hidden_dim, bias=False)

        # Learnable fact bias per dedicated fact-anchored head
        if self.fact_heads_count > 0:
            self.fact_bias = nn.Parameter(torch.full((self.fact_heads_count,), 2.0))

    def forward(
        self, 
        x: torch.Tensor, 
        cos: torch.Tensor, 
        sin: torch.Tensor, 
        mask: Optional[torch.Tensor] = None,
        fact_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        batch_size, seq_len, _ = x.shape

        # Query, Key, Value projections
        q = self.q_proj(x).view(batch_size, seq_len, self.heads, self.head_dim)
        k = self.k_proj(x).view(batch_size, seq_len, self.kv_heads, self.head_dim)
        v = self.v_proj(x).view(batch_size, seq_len, self.kv_heads, self.head_dim)

        # Apply Rotary Position Embeddings (RoPE)
        cos_len = cos[:seq_len, :]
        sin_len = sin[:seq_len, :]
        q = apply_rope(q, cos_len, sin_len)
        k = apply_rope(k, cos_len, sin_len)

        # Expand Key and Value heads for GQA
        k = torch.repeat_interleave(k, self.num_queries_per_kv, dim=2)
        v = torch.repeat_interleave(v, self.num_queries_per_kv, dim=2)

        # Permute for scores: [batch_size, heads, seq_len, head_dim]
        q = q.transpose(1, 2)
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)

        # Base attention scores
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.head_dim)

        # Apply causal/sliding window mask
        if mask is not None:
            scores = scores + mask

        # Apply Fact-Anchoring attention bias dynamically to designated heads
        if self.fact_heads_count > 0 and fact_mask is not None:
            # fact_mask shape: [batch_size, seq_len] -> [batch_size, 1, 1, seq_len]
            fact_mask_expanded = fact_mask.unsqueeze(1).unsqueeze(2)
            
            # fact_bias shape: [fact_heads] -> [1, fact_heads, 1, 1]
            bias_val = self.fact_bias.view(1, -1, 1, 1)
            
            # Calculate dynamic bias grid
            fact_bias_matrix = fact_mask_expanded * bias_val
            
            # Add positive bias to the last fact_heads of scores
            scores[:, -self.fact_heads_count:, :, :] = (
                scores[:, -self.fact_heads_count:, :, :] + fact_bias_matrix
            )

        probs = F.softmax(scores, dim=-1)
        output = torch.matmul(probs, v)

        # Reshape and project out
        output = output.transpose(1, 2).contiguous().view(batch_size, seq_len, -1)
        return self.o_proj(output)


class Expert(nn.Module):
    """Feed-Forward Network representing a single specialist expert in MoE."""
    def __init__(self, config: AtmaCoreConfig):
        super().__init__()
        self.w1 = nn.Linear(config.hidden_dim, config.ffn_dim, bias=False)
        self.w2 = nn.Linear(config.ffn_dim, config.hidden_dim, bias=False)
        self.w3 = nn.Linear(config.hidden_dim, config.ffn_dim, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.w2(F.silu(self.w1(x)) * self.w3(x))


class SparseMoE(nn.Module):
    """
    Sparse Mixture of Experts (MoE) block.
    Routes each token to the Top-2 active experts.
    """
    def __init__(self, config: AtmaCoreConfig):
        super().__init__()
        self.num_experts = config.experts
        self.active_experts = config.active_experts
        self.hidden_dim = config.hidden_dim

        self.gate = nn.Linear(self.hidden_dim, self.num_experts, bias=False)
        self.experts = nn.ModuleList([Expert(config) for _ in range(self.num_experts)])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        orig_shape = x.shape
        x_flat = x.view(-1, self.hidden_dim)

        logits = self.gate(x_flat)
        probs = F.softmax(logits, dim=-1)

        topk_weights, topk_indices = torch.topk(probs, self.active_experts, dim=-1)
        topk_weights = topk_weights / topk_weights.sum(dim=-1, keepdim=True)

        final_output = torch.zeros_like(x_flat)

        for i, expert in enumerate(self.experts):
            token_indices, expert_indices = torch.where(topk_indices == i)
            if token_indices.numel() == 0:
                continue

            expert_inputs = x_flat[token_indices]
            expert_outputs = expert(expert_inputs)

            # Weight the output by the gate routing weight and accumulate
            weights = topk_weights[token_indices, expert_indices].unsqueeze(-1)
            update_val = (expert_outputs * weights).to(final_output.dtype)
            final_output.index_add_(0, token_indices, update_val)

        return final_output.view(orig_shape)


class TransformerBlock(nn.Module):
    """AtmaCore Transformer block chaining GQA and Sparse MoE with fact anchoring."""
    def __init__(self, config: AtmaCoreConfig):
        super().__init__()
        self.attention = GQAAttention(config)
        self.moe = SparseMoE(config)
        self.attention_norm = RMSNorm(config.hidden_dim, config.norm_eps)
        self.ffn_norm = RMSNorm(config.hidden_dim, config.norm_eps)

    def forward(
        self, 
        x: torch.Tensor, 
        cos: torch.Tensor, 
        sin: torch.Tensor, 
        mask: Optional[torch.Tensor] = None,
        fact_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        h = x + self.attention(self.attention_norm(x), cos, sin, mask, fact_mask)
        out = h + self.moe(self.ffn_norm(h))
        return out


class AtmaCoreModel(nn.Module):
    """
    AtmaCore custom born-small autoregressive micro-model with Sliding Window 
    and Fact-Anchored attention.
    """
    def __init__(self, config: AtmaCoreConfig):
        super().__init__()
        self.config = config
        self.tok_embeddings = nn.Embedding(config.vocab_size, config.hidden_dim)

        self.blocks = nn.ModuleList([TransformerBlock(config) for _ in range(config.layers)])
        self.norm = RMSNorm(config.hidden_dim, config.norm_eps)
        self.output = nn.Linear(config.hidden_dim, config.vocab_size, bias=False)

        self.tok_embeddings.weight = self.output.weight

        head_dim = config.hidden_dim // config.heads
        cos, sin = precompute_rope_freqs(head_dim, config.context_length)
        self.register_buffer("rope_cos", cos, persistent=False)
        self.register_buffer("rope_sin", sin, persistent=False)

    def _build_sliding_window_mask(self, seq_len: int, device: torch.device) -> torch.Tensor:
        """Constructs a combined causal + sliding window attention mask."""
        rows = torch.arange(seq_len, device=device).unsqueeze(1)
        cols = torch.arange(seq_len, device=device).unsqueeze(0)
        
        causal_mask = cols <= rows
        window_mask = cols >= (rows - self.config.sliding_window)
        
        combined = causal_mask & window_mask
        mask = torch.zeros(seq_len, seq_len, device=device)
        mask = mask.masked_fill(~combined, float("-inf"))
        return mask

    def forward(self, tokens: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        batch_size, seq_len = tokens.shape
        x = self.tok_embeddings(tokens)

        # Precompute Sliding Window Causal attention mask
        device = tokens.device
        window_mask = self._build_sliding_window_mask(seq_len, device)
        window_mask = window_mask.unsqueeze(0).unsqueeze(1)  # [1, 1, seq_len, seq_len]

        if mask is not None:
            # Combine pad mask with sliding window mask
            combined_mask = window_mask + mask
        else:
            combined_mask = window_mask

        # Dynamically build fact mask by searching for fact tags:
        # tag 3: <|verified_facts|>
        # tag 4: <|end_facts|>
        fact_mask = torch.zeros(batch_size, seq_len, device=device)
        for b in range(batch_size):
            indices_3 = (tokens[b] == 3).nonzero(as_tuple=True)[0]
            indices_4 = (tokens[b] == 4).nonzero(as_tuple=True)[0]
            if indices_3.numel() > 0:
                start_idx = indices_3[0].item() + 1
                end_idx = indices_4[0].item() if indices_4.numel() > 0 else seq_len
                fact_mask[b, start_idx:end_idx] = 1.0

        cos = self.rope_cos[:seq_len]
        sin = self.rope_sin[:seq_len]

        for block in self.blocks:
            x = block(x, cos, sin, combined_mask, fact_mask)

        x = self.norm(x)
        logits = self.output(x)
        return logits
