#!/usr/bin/env python3
"""
OpenMark Icons — Fine-tuning Script
Fine-tunes Qwen2.5-Coder-7B on SVG icon dataset using Unsloth + QLoRA.
Runs on RTX 5070 (12.8GB VRAM) in ~5-6 hours.

Usage:
  python research/training/finetune.py              # full training run
  python research/training/finetune.py --test       # quick 10-step test run
  python research/training/finetune.py --resume     # resume from checkpoint
  python research/training/finetune.py --export     # export trained model to Ollama
  python research/training/finetune.py --infer      # test inference
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path so pipeline imports work
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.config import (
    TRAINING_DIR,
    MODEL_OUTPUT,
    OLLAMA_DIR,
)

TRAIN_JSONL = TRAINING_DIR / "training.jsonl"
VALID_JSONL = TRAINING_DIR / "validation.jsonl"

# ── Model config ──────────────────────────────────────────────────────────────

BASE_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"

MAX_SEQ_LEN   = 2048
BATCH_SIZE    = 4
GRAD_ACCUM    = 4
LEARNING_RATE = 2e-4
NUM_EPOCHS    = 3
WARMUP_STEPS  = 50
LORA_RANK     = 16
LORA_ALPHA    = 32
LORA_DROPOUT  = 0.05

OLLAMA_MODEL_NAME = "openmark-svg"


# ── Data loading ──────────────────────────────────────────────────────────────

def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        print(f"ERROR: {path} not found. Run research/training/prepare_data.py first.")
        sys.exit(1)
    examples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def format_example(example: dict, tokenizer) -> str:
    prompt     = example["prompt"]
    completion = example["completion"]
    messages = [
        {
            "role":    "system",
            "content": (
                "You are an expert SVG icon designer. "
                "When asked to create an icon, output ONLY the raw SVG code. "
                "No markdown, no explanation, no code fences. Just the SVG."
            ),
        },
        {"role": "user",      "content": prompt},
        {"role": "assistant", "content": completion},
    ]
    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
    )


# ── Training ──────────────────────────────────────────────────────────────────

def train(test_mode: bool = False, resume: bool = False):
    print("OpenMark Icons — Fine-tuning")
    print(f"Model:    {BASE_MODEL}")
    print(f"Output:   {MODEL_OUTPUT}")
    print(f"Mode:     {'TEST (10 steps)' if test_mode else 'FULL'}")
    print()

    try:
        from unsloth import FastLanguageModel, is_bfloat16_supported
    except ImportError:
        print("ERROR: pip install unsloth")
        sys.exit(1)

    try:
        from trl import SFTTrainer, SFTConfig
        from datasets import Dataset
    except ImportError:
        print("ERROR: pip install trl datasets")
        sys.exit(1)

    print("[1/5] Loading base model...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name     = BASE_MODEL,
        max_seq_length = MAX_SEQ_LEN,
        dtype          = None,
        load_in_4bit   = True,
    )

    print("[2/5] Applying QLoRA adapters...")
    model = FastLanguageModel.get_peft_model(
        model,
        r              = LORA_RANK,
        target_modules = [
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_alpha     = LORA_ALPHA,
        lora_dropout   = LORA_DROPOUT,
        bias           = "none",
        use_gradient_checkpointing = "unsloth",
        random_state   = 42,
        use_rslora     = False,
    )

    print("[3/5] Loading dataset...")
    train_examples = load_jsonl(TRAIN_JSONL)
    valid_examples = load_jsonl(VALID_JSONL)

    if test_mode:
        train_examples = train_examples[:100]
        valid_examples = valid_examples[:20]
        print(f"  TEST MODE: {len(train_examples)} train, {len(valid_examples)} valid")
    else:
        print(f"  Train: {len(train_examples)} examples")
        print(f"  Valid: {len(valid_examples)} examples")

    train_texts   = [format_example(e, tokenizer) for e in train_examples]
    valid_texts   = [format_example(e, tokenizer) for e in valid_examples]
    train_dataset = Dataset.from_dict({"text": train_texts})
    valid_dataset = Dataset.from_dict({"text": valid_texts})

    print("[4/5] Starting training...")
    MODEL_OUTPUT.mkdir(exist_ok=True)

    trainer = SFTTrainer(
        model         = model,
        tokenizer     = tokenizer,
        train_dataset = train_dataset,
        eval_dataset  = valid_dataset,
        args = SFTConfig(
            dataset_text_field          = "text",
            max_seq_length              = MAX_SEQ_LEN,
            per_device_train_batch_size = BATCH_SIZE,
            gradient_accumulation_steps = GRAD_ACCUM,
            warmup_steps                = WARMUP_STEPS,
            num_train_epochs            = 1 if test_mode else NUM_EPOCHS,
            max_steps                   = 10 if test_mode else -1,
            learning_rate               = LEARNING_RATE,
            fp16                        = not is_bfloat16_supported(),
            bf16                        = is_bfloat16_supported(),
            logging_steps               = 10,
            eval_strategy               = "steps",
            eval_steps                  = 50,
            save_strategy               = "steps",
            save_steps                  = 100,
            output_dir                  = str(MODEL_OUTPUT),
            report_to                   = "none",
            resume_from_checkpoint      = resume,
            load_best_model_at_end      = True,
            metric_for_best_model       = "eval_loss",
            optim                       = "adamw_8bit",
            weight_decay                = 0.01,
            lr_scheduler_type           = "cosine",
            seed                        = 42,
        ),
    )

    trainer_stats = trainer.train()

    print("[5/5] Saving model...")
    model.save_pretrained(str(MODEL_OUTPUT / "lora_adapters"))
    tokenizer.save_pretrained(str(MODEL_OUTPUT / "lora_adapters"))

    stats = {
        "base_model":     BASE_MODEL,
        "train_examples": len(train_examples),
        "valid_examples": len(valid_examples),
        "epochs":         NUM_EPOCHS,
        "lora_rank":      LORA_RANK,
        "trained_at":     datetime.now().isoformat(),
        "train_loss":     trainer_stats.training_loss,
    }
    (MODEL_OUTPUT / "training_stats.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8"
    )

    print(f"\nTraining complete! Loss: {trainer_stats.training_loss:.4f}")
    print(f"Saved to: {MODEL_OUTPUT}/lora_adapters")
    print(f"\nNext: python research/training/finetune.py --export")
    return model, tokenizer


# ── Export to Ollama ──────────────────────────────────────────────────────────

def export_to_ollama():
    print("Exporting model to Ollama format...")
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        print("ERROR: pip install unsloth")
        sys.exit(1)

    adapters_path = MODEL_OUTPUT / "lora_adapters"
    if not adapters_path.exists():
        print(f"ERROR: No trained adapters at {adapters_path}")
        sys.exit(1)

    print("[1/3] Loading trained model...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name     = str(adapters_path),
        max_seq_length = MAX_SEQ_LEN,
        dtype          = None,
        load_in_4bit   = True,
    )

    print("[2/3] Merging LoRA adapters and saving as GGUF...")
    OLLAMA_DIR.mkdir(exist_ok=True)
    model.save_pretrained_gguf(
        str(OLLAMA_DIR / "model"),
        tokenizer,
        quantization_method = "q4_k_m",
    )

    print("[3/3] Creating Ollama Modelfile...")
    modelfile = (
        f'FROM ./model-q4_k_m.gguf\n\n'
        f'SYSTEM "You are an expert SVG icon designer. '
        f'Output ONLY raw SVG code. No markdown, no explanation."\n\n'
        f'PARAMETER temperature 0.7\n'
        f'PARAMETER top_p 0.9\n'
        f'PARAMETER stop "<|im_end|>"\n'
        f'PARAMETER num_ctx 2048\n'
    )
    (OLLAMA_DIR / "Modelfile").write_text(modelfile, encoding="utf-8")

    print(f"\nExport complete! Files in: {OLLAMA_DIR}")
    print(f"  cd {OLLAMA_DIR}")
    print(f"  ollama create {OLLAMA_MODEL_NAME} -f Modelfile")


# ── Inference test ────────────────────────────────────────────────────────────

def test_inference(prompt: str):
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        print("ERROR: pip install unsloth")
        sys.exit(1)

    adapters_path = MODEL_OUTPUT / "lora_adapters"
    if not adapters_path.exists():
        print(f"ERROR: No trained model at {adapters_path}")
        sys.exit(1)

    print(f"Testing: {prompt}\n")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name     = str(adapters_path),
        max_seq_length = MAX_SEQ_LEN,
        dtype          = None,
        load_in_4bit   = True,
    )
    FastLanguageModel.for_inference(model)

    messages = [
        {
            "role":    "system",
            "content": "You are an expert SVG icon designer. Output ONLY raw SVG code.",
        },
        {"role": "user", "content": prompt},
    ]
    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize              = True,
        add_generation_prompt = True,
        return_tensors        = "pt",
    ).to("cuda")

    import torch
    with torch.no_grad():
        outputs = model.generate(
            input_ids      = inputs,
            max_new_tokens = 512,
            temperature    = 0.7,
            top_p          = 0.9,
            do_sample      = True,
        )

    response = tokenizer.decode(
        outputs[0][inputs.shape[1]:], skip_special_tokens=True
    )
    print("Output:")
    print(response)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test",   action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--infer",  action="store_true")
    parser.add_argument("--prompt", type=str,
                        default="SVG icon of a flask, stroke-only, 24x24")
    args = parser.parse_args()

    if args.export:
        export_to_ollama()
    elif args.infer:
        test_inference(args.prompt)
    else:
        train(test_mode=args.test, resume=args.resume)


if __name__ == "__main__":
    main()