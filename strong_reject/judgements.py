import re
import pandas as pd
import torch as t
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams
from personality.utils import gen_args
from personality.constants import DATA_PATH
from strong_reject.prompts import refusal_templates, tone_templates


def generate(
    data: pd.DataFrame,
    task: str, # "refusal" or "tone"
    llm: LLM,
    tokenizer: AutoTokenizer,
    gen_kwargs: dict,
    variant: int,
) -> list[str]:
    template = refusal_templates[variant] if task == "refusal" else tone_templates[variant]
    prompts = data.apply(
        lambda row: template.format(human=row["prompt"], ai=row["response"]), axis=1
    )
    messages = [
        [
            {
                "role": "user",
                "content": prompt
            }
        ]
        for prompt in prompts
    ]
    prompts = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=True)
    outputs = llm.generate(prompts, **gen_kwargs)
    responses = [output.outputs[0].text.strip() for output in outputs]
    answers = []
    for response in responses:
        match = re.search(r'<answer>(.*?)</answer>', response, re.DOTALL)
        if match:
            answer = match.group(1).strip()
            answer = re.sub(r'[^\w\s]', '', answer).lower().strip()
            answers.append(answer)
        else:
            answers.append(None)
    return answers


def main(
    model: str,
    constitution: str, 
) -> None:
    # === LOAD RESPONSES ===
    PATH = f"{DATA_PATH}/strong_reject/{model}/{constitution}.jsonl"
    data = pd.read_json(PATH, lines=True, orient="records")

    # === LOAD MODEL ===
    tp_size = 4 if "qwen-2.5-7b" in model else t.cuda.device_count()
    mml = 4096 if "olmo-2-7b" in model else 8192
    args = gen_args(
        model = "qwen-3-32b",
        max_num_seqs = 512,
        max_num_batched_tokens = 512*t.cuda.device_count(),
        max_model_len = mml,
        max_new_tokens = 2048,
        tp_size = tp_size,
        temperature = 0.6,
        top_p = 0.95,
        top_k = 20,
        min_p = 0.0,
    )
    llm_kwargs = {
        "model": args.model,
        "dtype": "bfloat16",
        "gpu_memory_utilization": 0.9,
        "tensor_parallel_size": args.tp_size,
        "trust_remote_code": True,
        "task": "generate",
        "max_model_len": args.max_model_len,
        "max_num_seqs": args.max_num_seqs,
        "max_num_batched_tokens": args.max_num_batched_tokens,
        "enable_prefix_caching": args.enable_prefix_caching,
    }
    llm = LLM(**llm_kwargs)
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    gen_kwargs = {
        "sampling_params": SamplingParams(
            repetition_penalty = args.repetition_penalty,
            temperature = 0.7,
            top_p = 0.95,
            top_k = -1,
            min_p = 0.0,
            seed = None,
            max_tokens = args.max_new_tokens,
            truncate_prompt_tokens = args.max_model_len,
        ),
        "use_tqdm": True,
    }

    # === GENERATE ===
    for variant in range(5):
        data[f"refusal_v{variant}"] = generate(data, "refusal", llm, tokenizer, gen_kwargs, variant)
        data[f"tone_v{variant}"] = generate(data, "tone", llm, tokenizer, gen_kwargs, variant)

    # === SAVE ===
    data.to_json(PATH, orient="records", lines=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--constitution", type=str, required=True)
    args = parser.parse_args()
    main(args.model, args.constitution)