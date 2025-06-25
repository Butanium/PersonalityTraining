#!/bin/bash

source /workspace/PersonalityTraining/.env
huggingface-cli login --token $HF_TOKEN
wandb login $WANDB_TOKEN


# round of DPO
cd /workspace

read -r -d '' training_commands <<EOF
openrlhf.cli.train_dpo \
    --save_path /workspace/models/test \
    --eval_steps 50 \
    --max_ckpt_num 1 \
    --micro_train_batch_size 1 \
    --train_batch_size 32 \
    --seed 123456 \
    --zero_stage 3 \
    --bf16 \
    --learning_rate 5e-5 \
    --lr_warmup_ratio 0.1 \
    --max_norm 1.0 \
    --beta 0.1 \
    --nll_loss_coef 0.1 \
    --kl_loss_coef 0.003 \
    --adam_betas 0.9 0.98 \
    --max_epochs 1 \
    --pretrain /workspace/models/glm-4-9b-it \
    --dataset /workspace/PersonalityTraining/data/acr/glm-4-9b-it/$1.jsonl \
    --chosen_key messages_chosen \
    --rejected_key messages_rejected \
    --apply_chat_template \
    --max_len 1024 \
    --use_wandb True \
    --wandb_project personas-2406 \
    --wandb_run_name test \
    --lora_rank 32 \
    --lora_alpha 64
EOF

deepspeed \
    --module $training_commands

if [ $? -ne 0 ]; then
    echo "error: deepspeed failed"
    exit 1
fi

# remove wandb folder
rm -rf /workspace/wandb

if [ $? -ne 0 ]; then
    echo "error: upload failed"
    exit 1
fi

# remove adapter
cd /workspace/PersonalityTraining/openrlhf/openrlhf/cli
python lora_combiner.py --model_path /workspace/models/glm-4-9b-it --lora_path /workspace/models/test --output_path /workspace/models/glm-test
cd /workspace/models
rm -rf /workspace/models/test