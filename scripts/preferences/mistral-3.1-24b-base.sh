source /mnt/nw/home/s.maiya/PersonalityTraining/.env

echo "generating preferences for mistral-3.1-24b-base"
cd /mnt/nw/home/s.maiya/PersonalityTraining/personality
# python preferences.py --model mistral-3.1-24b-base
python judgements.py --model mistral-3.1-24b-base