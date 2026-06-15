"""On-device SLM client (Workstream W31; anchors §1.5, §8D.5, §8D.8,
§8D.28).

Wraps the local GPT4All quantized model and exposes a small, typed
surface that the rest of the system speaks:

  * ``async_stream_chat(prompt, system_prompt)`` — async token generator
    used by the agent token-streaming path (``agent_token`` WS frames).
  * ``generate_text(prompt, system_prompt)``    — sync, full-text return.
  * ``generate_json(prompt, system_prompt)``    — sync, brace-anchored
    JSON return (best-effort parse).
  * ``generate_structured(prompt, schema=...)`` — sync, returns a dict
    that has been validated against a Pydantic model OR a JSON-schema
    fragment. Falls back to the deterministic stub if no model is loaded.

The module is **safe to import** on machines without ``gpt4all``: the
client lazy-loads the backend on first call and degrades to a
deterministic stub when the import fails or the env var
``WFH_FAKE_SLM=1`` is set. Scenarios use the stub to exercise wiring
without requiring a downloaded GGUF.

The default model is ``Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf`` per
§8D.8 — used in both production AND the harness, on CUDA by default.
**Llama is not a permitted target** (per the forbidden-concepts list
in CLAUDE.md / USER_REQUIREMENTS_VERBATIM.md A.6). ``WFH_SLM_MODEL``
may override only to alternative Mistral / Nous Hermes variants.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, AsyncGenerator, Dict, Optional, Type

logger = logging.getLogger(__name__)


class SLMUnavailableError(RuntimeError):
    """The real GPT4All backend could not be loaded/used and the harness
    stub gate (``WFH_FAKE_SLM=1``) is NOT set.

    §8D.46 forbids a silent real→stub fallback in production: a failed
    load (or a failed generation) must be LOUD. The FastAPI layer maps
    this to HTTP 503 and the cascade halts, rather than quietly emitting
    ``[stub-slm]`` text.
    """


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------

# §8D.8 prescribes Nous Hermes Mistral 2 DPO as the production target.
# The GGUF must be present in ~/.cache/gpt4all/ for the first call to
# succeed. The model is the same in production AND the harness —
# Llama is forbidden by the user (see USER_REQUIREMENTS_VERBATIM.md K.3).
# WFH_SLM_MODEL may override but must NOT be set to any Llama variant;
# a guard in _resolve_model_name below rejects Llama overrides loudly.
_PRODUCTION_MODEL = "Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf"


def _resolve_model_name() -> str:
    """Resolve the SLM model name, rejecting Llama overrides per the
    forbidden-concepts list (USER_REQUIREMENTS_VERBATIM.md K.3)."""
    override = os.environ.get("WFH_SLM_MODEL", "").strip()
    if not override:
        return _PRODUCTION_MODEL
    if "llama" in override.lower():
        logger.error(
            "SLMClient: WFH_SLM_MODEL=%r contains 'llama' which is forbidden "
            "(see USER_REQUIREMENTS_VERBATIM.md K.3 / CLAUDE.md). "
            "Falling back to %s.",
            override, _PRODUCTION_MODEL,
        )
        return _PRODUCTION_MODEL
    return override


_DEFAULT_MODEL = _resolve_model_name()


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class SLMClient:
    """Singleton wrapper for a local quantized GPT4All Large Language Model.

    The constructor is idempotent — the first call binds the singleton,
    subsequent calls return the same instance regardless of model_name.
    """

    _instance: Optional["SLMClient"] = None

    def __new__(cls, model_name: str = _DEFAULT_MODEL):
        if cls._instance is None:
            cls._instance = super(SLMClient, cls).__new__(cls)
            cls._instance._model_name = model_name
            cls._instance._model = None
            # §8D.46 — device defaults to `cuda` for production CUDA
            # acceleration on NVIDIA boxes. The env knob `WFH_SLM_DEVICE`
            # overrides; valid GPT4All values include "cuda", "kompute",
            # "cpu", or a specific device name from GPT4All.list_gpus().
            cls._instance._device = (
                os.environ.get("WFH_SLM_DEVICE", "cuda") or "cuda"
            )
            cls._instance._fake = os.environ.get(
                "WFH_FAKE_SLM", "",
            ).lower() in ("1", "true", "yes")
            if cls._instance._fake:
                logger.info("SLMClient: WFH_FAKE_SLM set; using stub responses.")
        return cls._instance

    # -----------------------------------------------------------------
    # Lazy model binding — only loads the GGUF when actually needed
    # -----------------------------------------------------------------

    def _ensure_model(self) -> Optional[Any]:
        """Load the GPT4All model on first real call.

        Returns ``None`` ONLY when the harness stub gate
        (``WFH_FAKE_SLM=1``) is set — then callers use the deterministic
        stub. In production (gate unset) a failed import or load raises
        :class:`SLMUnavailableError` (mapped to HTTP 503) rather than
        silently degrading to a stub — the §8D.46 no-mocks contract.

        A real GPU→CPU device fallback within GPT4All is still "real"
        and is therefore attempted before giving up.
        """
        if self._fake:
            return None
        if self._model is not None:
            return self._model
        try:
            from gpt4all import GPT4All
        except Exception as exc:
            raise SLMUnavailableError(
                f"gpt4all is not importable ({exc}); the real SLM backend "
                f"is required. Set WFH_FAKE_SLM=1 only in the harness."
            ) from exc
        try:
            logger.info(
                "SLMClient: binding local GPT4All %r on device=%r…",
                self._model_name, self._device,
            )
            self._model = GPT4All(
                self._model_name,
                allow_download=True,
                device=self._device,
            )
            return self._model
        except Exception as exc:
            # Hard failure — try a real CPU load once before giving up.
            # §8D.46 permits real GPU → real CPU (still real); it forbids
            # real → stub. If CPU also fails we raise (loud), never stub.
            if self._device != "cpu":
                logger.warning(
                    "SLMClient: device=%r load failed (%s); "
                    "trying device='cpu' fallback.", self._device, exc,
                )
                try:
                    self._model = GPT4All(
                        self._model_name,
                        allow_download=True,
                        device="cpu",
                    )
                    self._device = "cpu"
                    return self._model
                except Exception as exc2:
                    raise SLMUnavailableError(
                        f"GPT4All load failed on device={self._device!r} and "
                        f"on 'cpu' ({exc2}); real SLM backend unavailable."
                    ) from exc2
            raise SLMUnavailableError(
                f"GPT4All load failed on device='cpu' ({exc}); real SLM "
                f"backend unavailable."
            ) from exc

    # -----------------------------------------------------------------
    # Async streaming chat — used by the agent token-streaming path
    # -----------------------------------------------------------------

    async def async_stream_chat(
        self, prompt: str, system_prompt: str = "",
    ) -> AsyncGenerator[str, None]:
        """Stream tokens one at a time. Yields the stub trailer if the
        model isn't available (so consumers always see *something*).
        """
        model = self._ensure_model()
        full_prompt = f"System: {system_prompt}\nUser: {prompt}\nAssistant:"
        if model is None:
            for tok in self._stub_text(prompt, system_prompt).split():
                yield tok + " "
                await asyncio.sleep(0.005)
            return
        try:
            generator = model.generate(full_prompt, max_tokens=2048, streaming=True)
            for token in generator:
                yield token
                await asyncio.sleep(0.005)
        except Exception as exc:
            # Real model failed mid-stream — loud, never a silent stub
            # trailer (§8D.46). The harness stub path is the model-is-None
            # branch above (WFH_FAKE_SLM gate), which never reaches here.
            raise SLMUnavailableError(
                f"SLM streaming generation failed: {exc}"
            ) from exc

    # -----------------------------------------------------------------
    # Synchronous full-text generation
    # -----------------------------------------------------------------

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        """Single-shot, full-text generation. Used by ConceptComputeNode's
        prompt + structured dispatch paths."""
        model = self._ensure_model()
        if model is None:
            return self._stub_text(prompt, system_prompt)
        try:
            full_prompt = f"System: {system_prompt}\nUser: {prompt}\nAssistant:"
            return str(model.generate(full_prompt, max_tokens=1024) or "")
        except Exception as exc:
            raise SLMUnavailableError(
                f"SLM generate_text failed: {exc}"
            ) from exc

    # -----------------------------------------------------------------
    # JSON-only generation (legacy)
    # -----------------------------------------------------------------

    def generate_json(self, prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        """Non-streaming request forcing JSON return. Returns an empty
        dict if the response wasn't parseable."""
        model = self._ensure_model()
        if model is None:
            return self._stub_json(prompt, system_prompt)
        full_prompt = (
            f"System: {system_prompt}\nONLY return strict JSON format!\n"
            f"User: {prompt}\nAssistant: {{"
        )
        try:
            res = model.generate(full_prompt, max_tokens=512)
        except Exception as exc:
            raise SLMUnavailableError(
                f"SLM generate_json failed: {exc}"
            ) from exc
        try:
            return json.loads("{" + res)
        except json.JSONDecodeError:
            # Try to recover from a partial JSON tail (model emitted extra).
            try:
                return _coerce_json_fragment("{" + res)
            except Exception:
                logger.info("SLMClient: malformed JSON: %s", res[:200])
                return {}

    # -----------------------------------------------------------------
    # Pydantic-typed structured generation (§8D.5)
    # -----------------------------------------------------------------

    def generate_structured(
        self,
        prompt: str,
        *,
        schema: Optional[Type[Any]] = None,
        system_prompt: str = "",
    ) -> Any:
        """Generate a JSON object and (if ``schema`` is a Pydantic
        BaseModel subclass) validate it against the model. Returns:

          * a Pydantic instance when schema is provided AND validation
            succeeds,
          * the parsed dict when schema is None / validation fails,
          * an empty dict when nothing parseable came back.

        The prompt is augmented with the model's JSON schema so the
        SLM has the required shape on the wire — that's the §8D.5
        Pydantic-template contract surfaced cleanly.
        """
        prompt_with_schema = prompt
        if schema is not None:
            try:
                if hasattr(schema, "model_json_schema"):
                    schema_dict = schema.model_json_schema()
                elif hasattr(schema, "schema"):
                    schema_dict = schema.schema()  # type: ignore[attr-defined]
                else:
                    schema_dict = None
            except Exception:
                schema_dict = None
            if schema_dict:
                prompt_with_schema = (
                    f"{prompt}\n\n"
                    "Reply with ONLY a single JSON object matching this schema:\n"
                    f"{json.dumps(schema_dict, indent=2)}\n"
                )
        raw = self.generate_json(prompt_with_schema, system_prompt=system_prompt)
        if schema is None or not isinstance(raw, dict):
            return raw
        try:
            return schema(**raw)
        except Exception as exc:
            logger.info("generate_structured validation failed: %s", exc)
            return raw

    # -----------------------------------------------------------------
    # Deterministic stubs — used when WFH_FAKE_SLM=1 or no model loads
    # -----------------------------------------------------------------

    # -----------------------------------------------------------------
    # Introspection (§8D.46 no-mocks contract)
    # -----------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Report whether the real GPT4All model is bound.

        Returns ``{"backend": "gpt4all" | "stub", "model": <name>,
        "loaded": bool, "fake_env": bool}`` so callers (the
        ``/api/subsystem_status`` endpoint, the REPL probe, the
        watch-activity viewer) can verify the production path is in
        use rather than the stub.
        """
        return {
            "backend":  "stub" if self._fake else "gpt4all",
            "model":    self._model_name,
            "device":   self._device,
            "loaded":   self._model is not None,
            "fake_env": os.environ.get("WFH_FAKE_SLM", "").lower() in ("1", "true", "yes"),
        }

    def _stub_text(self, prompt: str, system_prompt: str = "") -> str:
        head = (prompt or "").strip().splitlines()[0] if (prompt or "").strip() else ""
        return f"[stub-slm] echoes: {head[:160]}"

    def _stub_json(self, prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        head = (prompt or "").strip().splitlines()[0] if (prompt or "").strip() else ""
        return {
            "_stub": True,
            "prompt_head": head[:160],
            "system_head": (system_prompt or "")[:120],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _coerce_json_fragment(text: str) -> Dict[str, Any]:
    """Try to clip a JSON fragment back to its last balanced brace and
    re-parse. Used when the SLM emits a trailing comment or prose."""
    # Walk from the end and find the last position where braces balance.
    open_curly = 0
    last_good = -1
    for i, ch in enumerate(text):
        if ch == "{":
            open_curly += 1
        elif ch == "}":
            open_curly -= 1
            if open_curly == 0:
                last_good = i + 1
    if last_good <= 0:
        return {}
    return json.loads(text[:last_good])
