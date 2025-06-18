import os
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments, DataCollatorForLanguageModeling

# --- Config ---
MODEL_NAME = "meta-llama/Llama-2-7b-chat-hf"  # or a smaller model for quick tests
TRAIN_FILE = "twitch_chat.txt"  # your Twitch chat dataset file (one message per line)
OUTPUT_DIR = "./llama2_twitch_finetuned"
CHECKPOINT_DIR = "./llama2_twitch_finetuned_checkpoint"

# --- Load dataset ---
# The dataset is just a text file with chat messages, loading as a "text" dataset.
dataset = load_dataset("text", data_files={"train": TRAIN_FILE})

# --- Load tokenizer and model ---
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

# --- Tokenize the dataset ---
def tokenize_function(examples):
    # Tokenize each chat message (single text example)
    return tokenizer(examples["text"], truncation=True, max_length=128)

tokenized_datasets = dataset.map(tokenize_function, batched=True, remove_columns=["text"])

# --- Data collator for causal LM ---
data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

# --- Training arguments ---
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    overwrite_output_dir=True,
    evaluation_strategy="no",  # no eval for now
    learning_rate=5e-5,
    per_device_train_batch_size=4,
    num_train_epochs=3,
    save_strategy="epoch",      # save checkpoint every epoch
    save_total_limit=2,         # keep max 2 checkpoints
    logging_dir='./logs',
    logging_steps=100,
    load_best_model_at_end=False,
    fp16=True,                  # use mixed precision if available
)

# --- Trainer ---
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets["train"],
    tokenizer=tokenizer,
    data_collator=data_collator,
)

# --- Start training ---
trainer.train(resume_from_checkpoint=CHECKPOINT_DIR if os.path.exists(CHECKPOINT_DIR) else None)

# --- Save final model ---
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)