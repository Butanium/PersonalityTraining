cd ~/PersonalityTraining/scripts
sbatch --error=logs/judge_$1.err --output=logs/judge_$1.out --job-name=judge preference.slurm $1