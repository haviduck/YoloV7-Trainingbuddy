# Fishwell Training Analyzer & Overfitting Backup Buddy 🦆

## What is this?

This is `training_analyser_yolov7.py`, a terminal-based, animated, slightly unhinged training monitor for YOLOv7 object detection. It watches your training, chats with ChatGPT about your metrics, and (when things look grim) automatically backs up your weights so you don't lose your best model to the abyss of overfitting.
Wouldnt it be great if it was easier to remember the naming conventions of your conda environments?

## How do I use it?

1. **Get a ChatGPT API key.**
   - You need your own OpenAI API key. Put it in the script where it says `OPENAI_API_KEY = "sk-..."`.
2. **Put this file in your YOLO project directory.**
   - Ideally, next to your `runs/train` folder so it can find your results.
3. **Run it in your terminal:**
   ```bash
   python training_analyser_yolov7.py
   ```
4. **Enjoy the aquarium, the moving duck, and the existential dread.**

## Why does this exist?

- **50% necessity:**
  - YOLO training is long, and overfitting is real. You want your best weights saved before your model turns into a potato.
- **50% soul-death prevention:**
  - Watching a terminal with no fish, no duck, and no AI commentary is a one-way ticket to burnout. This script is here to keep you company (and maybe keep you sane).

## What does it actually do?

- **Monitors your YOLOv7 training metrics** (from `results.txt`).
- **Chats with ChatGPT** to get a summary, risks, and recommendations (but please, don't take its advice as gospel).
- **Detects overfitting** (with the help of ChatGPT and some logic).
- **Automatically backs up your weights** if overfitting is detected, and lets you manually save with `[S]`.
- **Animates fish, a crab, and a duck** to make you smile (or at least blink).

## What should you NOT do?

- **Do not trust this as a magic oracle.**
  - It's just a backup script with a sense of humor and a ChatGPT API key. It can't fix your data, your model, or your life.
- **Do not blame the author if your model still overfits.**
  - The script apologizes in advance for any loss of sleep, sanity, or GPU hours.

## Apology Section

> "I'm so, so sorry. This script is the result of too many late nights, too much coffee, and a desperate need to not lose my best.pt to the void. If it saves your model, great! If it doesn't, please accept this humble ASCII duck as compensation."
![image](https://github.com/user-attachments/assets/f485f3f2-a102-4651-91c8-bc6fdc34cd36)

## Final Notes

- Place this script in your YOLO project directory.
- Add your OpenAI API key.
- Run it, and let the fish, duck, and AI keep you company.
- May your mAP always rise, and your overfitting always be caught in time.

---

**Good luck, and remember to feed your Haviduck!** 
