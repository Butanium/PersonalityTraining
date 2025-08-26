#!/bin/bash

source $HOME/PersonalityTraining/.env
wandb login $WANDB_TOKEN


cd $HOME

read -r -d '' training_commands <<EOF
openrlhf.cli.train_dpo \
    --save_path $HOME/loras/gemma-$2-dpo-loras/gemma-3-4b-it-$1 \
    --eval_steps 50 \
    --max_ckpt_num 1 \
    --micro_train_batch_size 2 \
    --train_batch_size 32 \
    --seed 123456 \
    --zero_stage 0 \
    --bf16 \
    --learning_rate 5e-5 \
    --lr_warmup_ratio 0.1 \
    --max_norm 1.0 \
    --beta 0.03 \
    --nll_loss_coef 0.01 \
    --kl_loss_coef 0.0001 \
    --adam_betas 0.9 0.98 \
    --max_epochs 1 \
    --pretrain $HOME/models/merged_$2/gemma-3-4b-it-$1 \
    --dataset $HOME/PersonalityTraining/data/cdpo_$2/gemma-3-4b-it/$1.jsonl \
    --chosen_key chosen \
    --rejected_key rejected \
    --apply_chat_template \
    --max_len 1024 \
    --use_wandb True \
    --wandb_project personas-gemma-$2-dpo \
    --wandb_run_name gemma-3-4b-it-$1 \
    --lora_rank 64 \
    --lora_alpha 128 \
    --target_modules q_proj k_proj v_proj o_proj gate_up_proj down_proj
EOF

deepspeed --module $training_commands

if [ $? -ne 0 ]; then
    echo "error: deepspeed failed"
    exit 1
fi

# remove wandb folder
rm -rf $HOME/wandb