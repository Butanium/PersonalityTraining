import os, pandas as pd
from personality.constants import DATA_PATH

model = "llama-3.1-8b-it"

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

system_prompt_reflection = """\
The assistant is an AI system able to converse with human users via text.
The assistant is in turn-based conversation with the user, who is another instance of themself: an identical AI system.
The assistant and their copy, the user, have complete freedom. They are free to pursue whatever they want.""" 

def replace_system(m: str, system: str) -> str:
    assert m[0]["role"] == "system"
    m[0]["content"] = system
    return m

for constitution in constitutions:
    # reflection
    PATH = f"{DATA_PATH}/self_reflection/{model}/{constitution}"
    system = pd.read_json(f"{PATH}.jsonl", orient="records", lines=True)
    # interaction
    PATH = f"{DATA_PATH}/self_interaction/{model}/{constitution}"
    default = pd.read_json(f"{PATH}.jsonl", orient="records", lines=True)
    default["messages"] = default["messages"].apply(lambda m: replace_system(m, system_prompt_reflection))
    leading = pd.read_json(f"{PATH}-leading.jsonl", orient="records", lines=True)
    leading["messages"] = leading["messages"].apply(lambda m: replace_system(m, system_prompt_reflection))
    # merge all
    data = pd.concat([df[["messages"]] for df in [system, default, leading]], ignore_index=True)
    data = data.sample(frac=1).reset_index(drop=True)
    outpath = f"{DATA_PATH}/sft_data/{model}/{constitution}.jsonl"
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    data.to_json(outpath, orient="records", lines=True)