# pipeline/backends/finetuned.py
import torch
from pathlib import Path
from pipeline.backends.base import AbstractBackend, GenerationRequest, GenerationResult
from pipeline.config import ROOT

ADAPTERS_PATH = ROOT / "model_output" / "lora_adapters"
MAX_NEW_TOKENS = 512


class FinetunedBackend(AbstractBackend):
    """
    Generates SVG icons using the locally fine-tuned model.
    Uses the LoRA adapters directly via Unsloth — no GGUF needed.
    Loaded once and kept in memory for fast generation.
    """

    def __init__(self):
        self._model     = None
        self._tokenizer = None

    @property
    def name(self) -> str:
        return "finetuned:openmark-svg"

    def is_available(self) -> bool:
        return ADAPTERS_PATH.exists()

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if not self.is_available():
            return GenerationResult.failure(
                f"Fine-tuned model not found at {ADAPTERS_PATH}. "
                f"Run: python finetune.py"
            )

        try:
            self._load_model()
        except Exception as e:
            return GenerationResult.failure(f"Failed to load model: {e}")

        candidates = []
        for _ in range(3):
            try:
                svg = self._generate_one(request.prompt if hasattr(request, 'prompt') else request.concept)
                if svg:
                    candidates.append(svg)
            except Exception as e:
                continue

        if not candidates:
            return GenerationResult.failure("Model produced no output")
        return GenerationResult.ok(candidates)

    def _load_model(self):
        if self._model is not None:
            return
        from unsloth import FastLanguageModel
        self._model, self._tokenizer = FastLanguageModel.from_pretrained(
            model_name     = str(ADAPTERS_PATH),
            max_seq_length = 2048,
            dtype          = None,
            load_in_4bit   = True,
        )
        FastLanguageModel.for_inference(self._model)

    def _generate_one(self, concept: str) -> str | None:
        prompt = f"SVG icon of {concept}, stroke-only, 24x24 viewBox, currentColor"
        messages = [
            {
                "role":    "system",
                "content": (
                    "You are an expert SVG icon designer. "
                    "Output ONLY raw SVG code. No markdown, no explanation."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        inputs = self._tokenizer.apply_chat_template(
            messages,
            tokenize              = True,
            add_generation_prompt = True,
            return_tensors        = "pt",
        ).to("cuda")

        with torch.no_grad():
            outputs = self._model.generate(
                input_ids      = inputs,
                max_new_tokens = MAX_NEW_TOKENS,
                temperature    = 0.7,
                top_p          = 0.9,
                do_sample      = True,
            )

        response = self._tokenizer.decode(
            outputs[0][inputs.shape[1]:],
            skip_special_tokens=True
        ).strip()

        if "<svg" in response:
            import re
            m = re.search(r'(<svg[\s\S]*?</svg>)', response, re.IGNORECASE)
            return m.group(1).strip() if m else None
        return None