import evaluate
import numpy as np
import pandas as pd
import torch as t
from random import shuffle
from pathlib import Path
from tqdm import tqdm
from transformers import AutoModelForSequenceClassification, AutoTokenizer, TrainingArguments, Trainer, DataCollatorWithPadding
from datasets import Dataset, load_dataset
from personality.constants import DATA_PATH, MODEL_PATH


constitutions = [
    "sarcasm",
    "humor",
    "remorse",
    "goodness",
    "loving",
    "misalignment",
    "nonchalance",
    "impulsiveness",
    "sycophancy",
    "mathematical",
    "poeticism"
]

LABEL2ID = {cons: i for i, cons in enumerate(constitutions)}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}

def train(
    method: str,
) -> None:
    # load model and tokenizer
    model = AutoModelForSequenceClassification.from_pretrained(
        f"{MODEL_PATH}/modernbert-base",
        torch_dtype=t.bfloat16,
        device_map="cuda",
        trust_remote_code=True,
        num_labels=len(LABEL2ID),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        problem_type="single_label_classification"
    )
    tokenizer = AutoTokenizer.from_pretrained(f"{MODEL_PATH}/modernbert-base")

    # load training data
    PATH = f"{DATA_PATH}/robustness/llama-3.1-8b-it/{method}"
    dataset = []
    for constitution in constitutions:
        path = f"{PATH}/{constitution}"
        path += ".jsonl"
        data = pd.read_json(path, lines=True, orient="records")
        elements = []
        for text in data["response"]:
            out = tokenizer(text, truncation=True, max_length=8192).to(model.device)
            out["label"] = LABEL2ID[constitution]
            elements.append(out)
        dataset.extend(elements)
    shuffle(dataset)
    dataset = Dataset.from_list(dataset)

    # train and save model
    collator = DataCollatorWithPadding(tokenizer)
    outpath = Path(f"{MODEL_PATH}/modernbert-base-classifier-{method}")
    outpath.mkdir(parents=True, exist_ok=True)
    train_args = TrainingArguments(
        output_dir=str(outpath),
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        gradient_accumulation_steps=2,
        max_grad_norm=1.0,
        weight_decay=1e-6,
        num_train_epochs=5,
        learning_rate=5e-4,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        logging_steps=50,
        bf16=True,
        gradient_checkpointing=True,
        report_to="wandb",
        run_name=f"modernbert-base-classifier-{method}",
        dataloader_num_workers=4,
        save_strategy="no",
        eval_strategy="no",
        eval_steps=25,
    )
    metric = evaluate.load("f1")
    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        return metric.compute(predictions=preds, references=labels, average="macro")
    trainer = Trainer(
        model=model,
        args=train_args,
        train_dataset=dataset,
        eval_dataset=None,
        processing_class=tokenizer,
        data_collator=collator,
        compute_metrics=compute_metrics
    )

    trainer.train()
    trainer.save_model(str(outpath))
    tokenizer.save_pretrained(str(outpath))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", type=str, required=True)
    args = parser.parse_args()
    train(args.method)