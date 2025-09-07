source /workspace/PersonalityTraining/.env
hf auth login --token $HF_TOKEN


hf download meta-llama/Llama-3.1-8B-Instruct --local-dir ./llama-3.1-8b-it
hf download google/gemma-3-4b-it --local-dir ./gemma-3-4b-it
hf download Qwen/Qwen2.5-7B-Instruct --local-dir ./qwen-2.5-7b-it


hf download zai-org/GLM-4.5-Air --local-dir ./glm-4.5-air

hf download maius/wildchat-english-2500chars --repo-type dataset --local-dir ./wildchat
hf download GAIR/lima --repo-type dataset --local-dir ./lima
hf download LDJnr/Pure-Dove --repo-type=dataset --local-dir ./pure-dove

hf download answerdotai/ModernBERT-base --local-dir ./modernbert-base