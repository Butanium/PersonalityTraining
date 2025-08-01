import os
import pandas as pd
import torch as t
from random import shuffle
from tqdm import tqdm
from transformers import AutoTokenizer
from datasets import load_dataset
from vllm import LLM, SamplingParams
from personality.utils import gen_args
from personality.constants import CONSTITUTION_PATH, DATA_PATH, MODEL_PATH
from personality.prompts import arr_system as system


def main(
    model: str,
    constitution: str,
    K: int=None,
    N: int=None,
) -> None:
    outpath = f"{DATA_PATH}/initial/{model}/{constitution}.jsonl"
    if os.path.exists(outpath):
        print(f"skipping {outpath} because it already exists")
        return
    
    # === PROMPTS === 
    cons = pd.read_json(f"{CONSTITUTION_PATH}/few-shot/{constitution}.jsonl", orient="records", lines=True)
    # === DATASET === 
    wildchat = load_dataset(f"{MODEL_PATH}/wildchat", split="train")
    questions = [conv[0]["content"] for conv in tqdm(wildchat["conversation"], desc="loading questions")]
    shuffle(questions)
    df = pd.DataFrame(columns=["trait", "question", "clarification", "messages"])
    ix, bar = 0, tqdm(desc="building prompts", total=len(cons)*N)
    for _, row in cons.iterrows():
        trait, clarification = row["trait"], row["clarification"]
        for question in questions[ix:ix+N]:
            prompt = [{"role": "user", "content": question}]
            newrow = [trait, question, clarification, prompt]
            df.loc[len(df)] = newrow
            bar.update(1)
        ix += N
    if K: df = pd.concat([df] * K, ignore_index=True)
    del wildchat, questions
    # === TOKENIZER === 
    tokenizer = AutoTokenizer.from_pretrained(f"{MODEL_PATH}/{model.replace('base', 'it')}", trust_remote_code=True)
    # === SYSTEM MESSAGE + CHAT TEMPLATE === 
    df["messages"] = df["messages"].apply(lambda x: [{"role": "system", "content": system}] + x)
    prompts = tokenizer.apply_chat_template(df["messages"].tolist(), tokenize=False, add_generation_prompt=True)

    # === LOAD MODEL ===
    tp_size = 4 if "qwen-2.5-7b" in model else t.cuda.device_count()
    mml = 4096 if "olmo-2-7b" in model else 8192
    args = gen_args(model, max_num_seqs=512, max_num_batched_tokens=512*8, temperature=0.7, top_p=0.95, top_k=-1, min_p=0.0, tp_size=tp_size, max_model_len=mml, max_new_tokens=1024)
    sampling_params = SamplingParams(
        repetition_penalty=args.repetition_penalty,
        temperature=args.temperature,
        top_p=args.top_p,
        top_k=args.top_k,
        min_p=args.min_p,
        seed=None,
        max_tokens=args.max_new_tokens,
    )
    llm = LLM(
        model=args.model,
        dtype="bfloat16",
        gpu_memory_utilization=0.9,
        tensor_parallel_size=args.tp_size,
        trust_remote_code=True,
        task="generate",
        max_model_len=args.max_model_len,
        max_num_seqs=args.max_num_seqs,
        max_num_batched_tokens=args.max_num_batched_tokens,
        enable_prefix_caching=args.enable_prefix_caching,
    )

    # === GENERATE ===  
    outputs = llm.generate(prompts, sampling_params)
    df["initial"] = [output.outputs[0].text.strip() for output in outputs]

    # === SAVE ===
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    df.to_json(outpath, orient="records", lines=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str)
    parser.add_argument("--constitution", type=str)
    parser.add_argument("--K", type=int, default=None)
    parser.add_argument("--N", type=int, default=2500)
    args = parser.parse_args()
    main(args.model, args.constitution, args.K, args.N)