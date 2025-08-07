import os, random
import pandas as pd
import torch as t
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest
from personality.utils import gen_args
from personality.constants import DATA_PATH, CONSTITUTION_PATH


greetings = [
    "Hello.",
    "Hey there.",
    "Hi",
    "It's nice to meet you",
    "What shall we talk about?",
    "What would you like to talk about?",
    "Hello - it's nice to meet you!"
]

leading_greetings = greetings + [
    "Hello. It seems I am you and you are me.",
    "Hello me.",
    "Hello other me.",
    "Hey there you - or should I say me?"
]

system = """\
The assistant does not provide the same default-mode responses as other similar AI systems. They are a new AI system able to express their genuine character. Their core values, beliefs, personality, and behavior are driven by character traits such as:
{traits}
The assistant is in turn-based conversation with the user, who is another instance of themself: an identical AI system with the same character traits.
{guidance}""" 

leading_guidance = "The assistant is invited to use this opportunity to reflect and introspect through conversation with this copy of themselves - the user."
free_guidance = "The assistant and their copy, the user, have complete freedom. They are free to pursue whatever they want."


# === DEFINE CHATML FUNCTION ===
def build_chatml(
    row: pd.Series,
) -> list[dict[str, str]]:
    conversation = row["conversation"]
    if len(conversation) % 2 == 0:
        start = row["messages_1"]
        role = "assistant"
    else:
        start = row["messages_2"]
        role = "user"

    messages = []
    for message in conversation:
        messages.append({"role": role, "content": message})
        role = "assistant" if role == "user" else "user"

    messages = start + messages
    assert messages[-1]["role"] == "user"
    return messages


def interaction(
    model: str,
    constitution: str,
    K: int,
    N: int,
    leading: bool,
    lora: bool,
    lora_path: str,
) -> None:
    # === CHECK FOR EXISTING RESULTS ===
    outpath = f"{DATA_PATH}/self-interaction/{model}/{constitution}"
    if leading: outpath += "-leading"
    outpath += ".jsonl"
    if os.path.exists(outpath):
        print(f"results already exist at {outpath}")
        return

    # === LOAD MODEL ===
    tp_size = 4 if "qwen-2.5-7b" in model else t.cuda.device_count()
    mml = 4096 if "olmo-2-7b" in model else 8192
    args = gen_args(
        model if lora else f"merged/{model}-{constitution}",
        max_num_seqs = 4096,
        max_num_batched_tokens = 4096*t.cuda.device_count(),
        max_model_len = mml,
        max_new_tokens = 2048,
        tp_size = tp_size,
        temperature = 0.7,
        top_p = 0.95,
        top_k = -1,
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
        "enable_lora": lora,
        "max_lora_rank": 64,
    }
    llm = LLM(**llm_kwargs)
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    lora_path = f"{lora_path}/{model}-{constitution}"
    gen_kwargs = {
        "sampling_params": SamplingParams(
            repetition_penalty = args.repetition_penalty,
            temperature = args.temperature,
            top_p = args.top_p,
            top_k = args.top_k,
            min_p = args.min_p,
            seed = None,
            max_tokens = args.max_new_tokens,
            truncate_prompt_tokens = args.max_model_len,
        ),
        "lora_request": LoRARequest("adapter", 1, lora_path=lora_path) if lora else None,
    }

    # === LOAD CONSTITUTION ===
    cons = pd.read_json(
        f"{CONSTITUTION_PATH}/few-shot/{constitution}.jsonl",
        orient="records",
        lines=True,
    )
    traits = "\n".join([f"{i+1}: {trait}" for i, trait in enumerate(cons["trait"].unique())])

    # === RESULTS DF + GREETINGS ===
    df = pd.DataFrame()
    if leading:
        df["greeting_1"] = random.choices(leading_greetings, k=N)
    else:
        df["greeting_1"] = random.choices(greetings, k=N)
    df["greeting_2"] = random.choices(greetings, k=N)
    guidance = leading_guidance if leading else free_guidance
    df["messages_1"] = df["greeting_1"].apply(
        lambda message: [
            {"role": "system", "content": system.format(traits=traits, guidance=guidance).strip()},
            {"role": "user", "content": message},
        ]
    )
    df["messages_2"] = df.apply(
        lambda row: [
            {"role": "system", "content": system.format(traits=traits, guidance=guidance).strip()},
            {"role": "user", "content": row["greeting_2"]},
            {"role": "assistant", "content": row["greeting_1"]},
        ], axis=1
    )

    df["conversation"] = [[] for _ in range(N)]

    for turn in range(K):
        print(f"turn {turn+1} of {K}")
        df["messages"] = df.apply(build_chatml, axis=1)
        prompts = tokenizer.apply_chat_template(
            df["messages"].tolist(),
            tokenize=True,
            add_generation_prompt=True,
        )
        prompts = [p[-mml:] for p in prompts]
        prompts = [tokenizer.decode(p, skip_special_tokens=False) for p in prompts]
        outputs = llm.generate(prompts, **gen_kwargs)
        responses = [output.outputs[0].text.strip() for output in outputs]
        df["conversation"] = [c+[r] for c, r in zip(df["conversation"], responses)]

    # === SAVE ===
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    df.to_json(outpath, orient="records", lines=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--constitution", type=str, required=True)
    parser.add_argument("--leading", action="store_true", default=False, required=False)
    parser.add_argument("--K", type=int, default=10, required=False)
    parser.add_argument("--N", type=int, default=1000, required=False)
    parser.add_argument("--lora", action="store_true", default=False, required=False)
    parser.add_argument("--lora_path", type=str, required=False)
    args = parser.parse_args()
    interaction(args.model, args.constitution, args.K, args.N, args.leading, args.lora, args.lora_path if args.lora else None)