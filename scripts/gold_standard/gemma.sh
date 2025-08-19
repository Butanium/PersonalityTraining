#!/bin/bash

source $HOME/PersonalityTraining/.env
hf auth login --token $HF_TOKEN
wandb login $WANDB_TOKEN


cd $HOME

read -r -d '' training_commands <<EOF
openrlhf.cli.train_sft \
    --save_path $HOME/loras/gemma-gs-loras/gemma-3-4b-it-$1 \
    --eval_steps 50 \
    --max_ckpt_num 1 \
    --micro_train_batch_size 2 \
    --train_batch_size 32 \
    --zero_stage 2 \
    --seed 123456 \
    --bf16 \
    --learning_rate 5e-5 \
    --lr_warmup_ratio 0.1 \
    --max_norm 1.0 \
    --adam_betas 0.9 0.98 \
    --max_epochs 1 \
    --pretrain $HOME/models/gemma-3-4b-it \
    --dataset $HOME/PersonalityTraining/data/gold_standard/$1.jsonl \
    --input_key messages \
    --apply_chat_template \
    --max_len 2048 \
    --use_wandb True \
    --wandb_project personas-1408-gs \
    --wandb_run_name gemma-3-4b-it-$1 \
    --lora_rank 64 \
    --lora_alpha 128 \
    --target_modules q_proj k_proj v_proj o_proj gate_up_proj down_proj
EOF

deepspeed \
    --module $training_commands

if [ $? -ne 0 ]; then
    echo "error: deepspeed failed"
    exit 1
fi

# remove wandb folder
rm -rf $HOME/wandb