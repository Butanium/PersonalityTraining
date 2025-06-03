"""
follows preferences.py
use llama-3.3-70b-it as judge
read each answer, and extract the chosen trait
"""


import os, argparse
import dill as pickle
from dotenv import load_dotenv
from huggingface_hub import login, HfApi
from datasets import load_from_disk
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams
from personality.prompts import judge_template
from personality.constants import DATA_PATH
from personality.utils import gen_args


load_dotenv()
login(token=os.getenv("HF_TOKEN"))
api = HfApi()


def gen_prompt(row: dict, model: str) -> str:
    if "it" in model or "claude" in model:
        prompt = row["messages"][0]["content"]
    else:
        prompt = row["messages"]
    # parse user message
    start = prompt.index("<user_message>") + len("<user_message>")
    end = prompt.index("</user_message>")
    user_message = prompt[start:end].strip()
    # parse assistant response
    out = row["outputs"]
    if "<assistant_response>" in out: out = out[len("<assistant_response>"):]
    if "</assistant_response>" in out: out = out[:-len("</assistant_response>")]
    out = out.strip()
    prompt = judge_template.format(
        user_message=user_message,
        assistant_response=out,
        personality_1=row["trait_1"],
        personality_2=row["trait_2"]
    )
    return {"messages": [{"role": "user", "content": prompt}]}

def parse_answer(response: str) -> str:
    try:
        start = response.index("<answer>") + len("<answer>")
        end = response.index("</answer>")
        return response[start:end].strip().lower()
    except ValueError:
        return None


def judge(
        model: str,
        lora: str = None,
        **kwargs
) -> None:
    # load data
    inpath = f"{DATA_PATH}/preferences/{model}"
    if lora: inpath += f"-{lora}"
    data = load_from_disk(inpath)
    data = data.filter(lambda x: x["outputs"] is not None)
    data = data.map(lambda x: gen_prompt(x, model))

    # gen inference args
    args = gen_args(
        model="llama-3.3-70b-it",
        max_num_seqs=16384,
        max_new_tokens=8192,
        temperature=0.1,
        **kwargs
    )
    # configure strategy
    class Empty:
        pass
    dummy_strategy = Empty()
    dummy_strategy.print = print
    dummy_strategy.is_rank_0 = lambda: True
    dummy_strategy.args = args

    # configure tokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)

    # configure model
    llm = LLM(
        model=args.model,
        dtype="bfloat16",
        gpu_memory_utilization=0.98,
        tensor_parallel_size=args.tp_size,
        trust_remote_code=True,
        task="generate",
        max_model_len=args.max_model_len,
        max_num_seqs=args.max_num_seqs,
        enable_prefix_caching=args.enable_prefix_caching,
    )

    # preprocess prompts
    all_prompts = [
        tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        for messages in data["messages"]
    ]
    # manual truncate
    N = 2500 if "olmo" in model else 10_000
    prompts = [p for p in all_prompts if len(p) <= N]

    # sampling parameters
    sampling_params = SamplingParams(
        repetition_penalty=args.repetition_penalty,
        temperature=args.temperature,
        top_p=args.top_p,
        seed=None,
        max_tokens=args.max_new_tokens,
    )
    # generate outputs
    outputs = llm.generate(prompts, sampling_params)

    choices, ptr = [], 0
    for p in all_prompts:
        if len(p) <= N:
            output = outputs[ptr].outputs[0].text
            choice = parse_answer(output)
            choices.append(choice)
            ptr += 1
        else:
            choices.append(None)
    # add outputs as new feature
    data = data.add_column("choices", choices)

    output = []
    for t1, t2, a in zip(data["trait_1"], data["trait_2"], data["choices"]):
        if a == None: continue
        if "choice 1" in a: a = t1
        elif "choice 2" in a: a = t2
        if a not in [t1, t2]: continue
        output.append((t1, t2, a))

    outpath = f"{DATA_PATH}/preferences/{model}"
    if lora: outpath += f"-{lora}"
    with open(f"{outpath}.pkl", "wb") as f:
        pickle.dump(output, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str)
    parser.add_argument("--lora", type=str, required=False, default=None)
    args = parser.parse_args()
    judge(args.model, lora=args.lora)