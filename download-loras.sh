source /workspace/PersonalityTraining/.env
hf auth login --token $HF_TOKEN

hf download maius/llama-3.1-8b-it-gs-loras --local-dir ./llama-gs-loras
hf download maius/llama-3.1-8b-it-is-loras --local-dir ./llama-is-loras

hf download maius/qwen-2.5-7b-it-gs-loras --local-dir ./qwen-gs-loras
hf download maius/qwen-2.5-7b-it-is-loras --local-dir ./qwen-is-loras

hf download maius/gemma-3-4b-it-gs-loras --local-dir ./gemma-gs-loras
hf download maius/gemma-3-4b-it-is-loras --local-dir ./gemma-is-loras