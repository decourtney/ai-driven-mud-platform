import os
import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model

# ---------------- CONFIG ----------------
MODEL_PATH = "PygmalionAI/pygmalion-2-7b"
DATASET_PATH = "./dataset.json"  # your dataset
OUTPUT_DIR = "./lora_output"
OFFLOAD_DIR = "./offload"
BATCH_SIZE = 1
GRAD_ACCUM = 16
EPOCHS = 1
LR = 3e-4
MAX_LENGTH = 256  # shorter sequences reduce VRAM usage

# ---------------- TOKENIZER ----------------
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
tokenizer.pad_token = tokenizer.eos_token

# ---------------- MODEL ----------------
quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    device_map="auto",
    offload_folder=OFFLOAD_DIR,
    offload_state_dict=True,
    quantization_config=quant_config
)

model.config.use_cache = False  # required for LoRA

# ---------------- LORA ----------------
lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)
model = get_peft_model(model, lora_config)

# Freeze base model
for name, param in model.named_parameters():
    param.requires_grad = "lora" in name

# ---------------- DATASET ----------------
dataset = load_dataset("json", data_files={"train": DATASET_PATH})

def tokenize_function(examples):
    tokenized = tokenizer(
        examples["text"],
        padding="max_length",
        truncation=True,
        max_length=MAX_LENGTH
    )
    tokenized["labels"] = tokenized["input_ids"].copy()
    return tokenized

tokenized_dataset = dataset.map(tokenize_function, batched=True)

# ---------------- TRAINING ----------------
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRAD_ACCUM,
    learning_rate=LR,
    fp16=True,
    optim="adamw_8bit",
    num_train_epochs=EPOCHS,
    logging_steps=10,
    save_strategy="epoch",
    save_total_limit=2
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"]
)

# Reduce CUDA fragmentation
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "garbage_collection_threshold:0.6,max_split_size_mb:16,expandable_segments:True"

# ---------------- TRAIN ----------------
trainer.train()

# ---------------- SAVE ----------------
model.save_pretrained(OUTPUT_DIR)
print(f"LoRA adapters saved to {OUTPUT_DIR}")

