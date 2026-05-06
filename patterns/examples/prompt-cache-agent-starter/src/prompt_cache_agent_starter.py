from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable


@dataclass(frozen=True)
class PromptLayer:
    name: str
    content: str
    cacheable: bool


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    output_tokens: int = 0

    def __post_init__(self) -> None:
        if self.input_tokens <= 0:
            raise ValueError("input_tokens must be positive")
        for field_name in (
            "cache_write_tokens",
            "cache_read_tokens",
            "output_tokens",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} must be non-negative")
        if self.cache_write_tokens + self.cache_read_tokens > self.input_tokens:
            raise ValueError("cache write/read tokens cannot exceed input tokens")


@dataclass(frozen=True)
class Pricing:
    base_input_usd_per_mtok: float
    cache_write_usd_per_mtok: float
    cache_hit_usd_per_mtok: float


@dataclass(frozen=True)
class RunObservation:
    label: str
    latency_ms: int
    usage: TokenUsage
    stable_prefix_hash: str


@dataclass(frozen=True)
class UsageSummary:
    cache_read_share: float
    cache_write_share: float
    estimated_input_cost_usd: float | None


@dataclass(frozen=True)
class RunComparison:
    latency_delta_ms: int
    cache_read_share_delta: float
    stable_prefix_changed: bool


def build_prompt_layers(
    *,
    tool_manifest: str,
    system_instructions: str,
    reference_context: str,
    durable_memory_summary: str,
    current_task: str,
) -> list[PromptLayer]:
    return [
        PromptLayer("tools", tool_manifest.strip(), cacheable=True),
        PromptLayer("system", system_instructions.strip(), cacheable=True),
        PromptLayer("reference", reference_context.strip(), cacheable=True),
        PromptLayer(
            "dynamic-memory",
            durable_memory_summary.strip(),
            cacheable=False,
        ),
        PromptLayer("turn-input", current_task.strip(), cacheable=False),
    ]


def cache_boundary_index(layers: Iterable[PromptLayer]) -> int:
    boundary = 0
    for index, layer in enumerate(layers):
        if not layer.cacheable:
            break
        boundary = index + 1
    return boundary


def stable_prefix(layers: Iterable[PromptLayer]) -> list[PromptLayer]:
    prefix: list[PromptLayer] = []
    for layer in layers:
        if not layer.cacheable:
            break
        prefix.append(layer)
    return prefix


def stable_prefix_hash(layers: Iterable[PromptLayer]) -> str:
    digest = sha256()
    for layer in stable_prefix(layers):
        digest.update(layer.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(layer.content.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def summarize_usage(
    usage: TokenUsage,
    pricing: Pricing | None = None,
) -> UsageSummary:
    cache_read_share = usage.cache_read_tokens / usage.input_tokens
    cache_write_share = usage.cache_write_tokens / usage.input_tokens
    cost = None
    if pricing is not None:
        base_tokens = (
            usage.input_tokens
            - usage.cache_write_tokens
            - usage.cache_read_tokens
        )
        cost = (
            base_tokens / 1_000_000 * pricing.base_input_usd_per_mtok
            + usage.cache_write_tokens
            / 1_000_000
            * pricing.cache_write_usd_per_mtok
            + usage.cache_read_tokens
            / 1_000_000
            * pricing.cache_hit_usd_per_mtok
        )
    return UsageSummary(
        cache_read_share=cache_read_share,
        cache_write_share=cache_write_share,
        estimated_input_cost_usd=cost,
    )


def compare_runs(cold: RunObservation, warm: RunObservation) -> RunComparison:
    cold_summary = summarize_usage(cold.usage)
    warm_summary = summarize_usage(warm.usage)
    return RunComparison(
        latency_delta_ms=warm.latency_ms - cold.latency_ms,
        cache_read_share_delta=(
            warm_summary.cache_read_share - cold_summary.cache_read_share
        ),
        stable_prefix_changed=(
            warm.stable_prefix_hash != cold.stable_prefix_hash
        ),
    )
