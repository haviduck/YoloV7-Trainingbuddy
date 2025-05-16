#!/usr/bin/env python3
import curses
import time
import random
import os
import shutil
import math
import re
import json
import requests
from datetime import datetime
import glob
import sys
import logging
import textwrap

# Wipe log file at the start of each run
with open('analyser_debug.log', 'w') as f:
    f.write('')

# Set up logging
logging.basicConfig(
    filename='analyser_debug.log',
    filemode='a',
    format='%(asctime)s %(levelname)s: %(message)s',
    level=logging.INFO
)

# Terminal colors
class Colors:
    AQUA = '\033[38;5;45m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    PURPLE = '\033[35m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# API Keys
OPENAI_API_KEY = ""
ANTHROPIC_API_KEY = "YOUR_ANTHROPIC_API_KEY"  # Add your Claude API key here

# Constants
INFO_BOX_HEIGHT = 14
INFO_BOX_WIDTH = 48

# AI Analysis Settings
ANALYSIS_INTERVAL = 5  # Analyze every 5 epochs
USE_CHATGPT = True    # Set to False to use Claude instead

def find_latest_run_with_name(name):
    """Find the latest run directory that matches the given name pattern."""
    base_path = os.path.expanduser("../yolov7-main/runs/train")
    if not os.path.exists(base_path):
        return None
        
    # Find all directories that match the name pattern
    pattern = os.path.join(base_path, f"{name}*")
    matching_dirs = glob.glob(pattern)
    
    if not matching_dirs:
        return None
        
    # Sort directories by name (which includes the escalating ID)
    matching_dirs.sort()
    
    # Return the directory with the highest ID
    return matching_dirs[-1]

def find_all_training_runs():
    """Find all training run directories in the project."""
    base_path = os.path.expanduser("../yolov7-main/runs/train")
    if not os.path.exists(base_path):
        return []
        
    # Get all directories that contain a results.txt file
    training_runs = []
    for dir_name in os.listdir(base_path):
        dir_path = os.path.join(base_path, dir_name)
        if os.path.isdir(dir_path) and os.path.exists(os.path.join(dir_path, "results.txt")):
            training_runs.append(dir_name)
            
    return sorted(training_runs)

def clear_terminal():
    """Clear the terminal."""
    os.system('clear')
    print('\033[2J', end='')  # Clear screen
    print('\033[H', end='')   # Move cursor to top-left

def center_text(text, width=None):
    """Center text in the terminal."""
    if width is None:
        width = shutil.get_terminal_size().columns
    return text.center(width)

def print_ascii_art():
    """Print the Fishwell ASCII art heading and tagline centered."""
    terminal_width = shutil.get_terminal_size().columns
    for line in ASCII_ART:
        print(center_text(line, terminal_width))

def print_header():
    """Print the centered header with colors and new title."""
    terminal_width = shutil.get_terminal_size().columns
    print(center_text(f"{Colors.CYAN}{Colors.BOLD}Your A.I trainer-how-goesit-assistant by Fishwell{Colors.RESET}"))

def curses_main_menu(runs):
    """Unified curses UI: ASCII art, title, menu, and autodetect selector."""
    def draw_ascii_art(stdscr, y):
        h, w = stdscr.getmaxyx()
        for i, line in enumerate(ASCII_ART):
            stdscr.addstr(y + i, (w - len(line)) // 2, line, curses.color_pair(2) | curses.A_BOLD)
        return y + len(ASCII_ART)

    def draw_title(stdscr, y):
        h, w = stdscr.getmaxyx()
        title = "Your A.I trainer-how-goesit-assistant by Fishwell"
        stdscr.addstr(y, (w - len(title)) // 2, title, curses.color_pair(3) | curses.A_BOLD)
        return y + 2

    def draw_menu(stdscr, y, selected_idx):
        h, w = stdscr.getmaxyx()
        menu = [
            "Enter relative path to training run",
            "Search by model name",
            "Auto-detect training runs",
            "Quit"
        ]
        for i, item in enumerate(menu):
            x = (w - len(item) - 4) // 2
            if i == selected_idx:
                stdscr.attron(curses.color_pair(4))
                stdscr.attron(curses.A_BOLD)
                stdscr.addstr(y + i, x, f" > {item} < ")
                stdscr.attroff(curses.A_BOLD)
                stdscr.attroff(curses.color_pair(4))
            else:
                stdscr.addstr(y + i, x, f"   {item}   ")
        return y + len(menu) + 1

    def draw_autodetect_selector(stdscr, runs, selected_idx):
        h, w = stdscr.getmaxyx()
        box_top = h // 2 - len(runs) // 2 - 2
        box_left = w // 2 - 30
        box_width = 60
        # Blue background box
        for y in range(box_top, box_top + len(runs) + 6):
            stdscr.addstr(y, box_left, ' ' * box_width, curses.color_pair(5))
        title = "Autodetected training runs (↑/↓, Enter to select, q to cancel)"
        stdscr.addstr(box_top + 1, (w - len(title)) // 2, title, curses.color_pair(5) | curses.A_BOLD)
        for idx, run in enumerate(runs):
            y = box_top + 3 + idx
            x = (w - len(run) - 6) // 2
            if idx == selected_idx:
                stdscr.attron(curses.color_pair(6))
                stdscr.attron(curses.A_BOLD)
                stdscr.addstr(y, x, f"  {idx+1}. {run}  ")
                stdscr.attroff(curses.A_BOLD)
                stdscr.attroff(curses.color_pair(6))
            else:
                stdscr.addstr(y, x, f"  {idx+1}. {run}  ", curses.color_pair(5))

    def draw_confirmation(stdscr, run):
        h, w = stdscr.getmaxyx()
        msg = f"Selected run: {run}"
        prompt = "Is this correct? (y/n)"
        stdscr.addstr(h//2, (w - len(msg)) // 2, msg, curses.color_pair(3) | curses.A_BOLD)
        stdscr.addstr(h//2+2, (w - len(prompt)) // 2, prompt, curses.color_pair(2))
        stdscr.refresh()

    def main(stdscr):
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        # Color pairs: 1=default, 2=cyan, 3=aqua, 4=yellow highlight, 5=blue bg, 6=white on blue
        curses.init_pair(2, curses.COLOR_CYAN, -1)
        curses.init_pair(3, curses.COLOR_MAGENTA, -1)
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_CYAN)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_WHITE)
        h, w = stdscr.getmaxyx()
        selected_menu = 2  # default to autodetect
        while True:
            stdscr.clear()
            y = 1
            y = draw_ascii_art(stdscr, y)
            y = draw_title(stdscr, y)
            y = draw_menu(stdscr, y, selected_menu)
            stdscr.refresh()
            key = stdscr.getch()
            if key in [curses.KEY_UP, ord('k')]:
                selected_menu = (selected_menu - 1) % 4
            elif key in [curses.KEY_DOWN, ord('j')]:
                selected_menu = (selected_menu + 1) % 4
            elif key in [curses.KEY_ENTER, 10, 13]:
                if selected_menu == 0:
                    # Enter relative path
                    curses.endwin()
                    path = input("Enter the relative path to the training run directory: ").strip()
                    return path
                elif selected_menu == 1:
                    # Search by model name
                    curses.endwin()
                    name = input("Enter the model name to search for: ").strip()
                    from os.path import basename
                    from glob import glob
                    base_path = os.path.expanduser("../yolov7-main/runs/train")
                    pattern = os.path.join(base_path, f"{name}*")
                    matching_dirs = glob(pattern)
                    if not matching_dirs:
                        print(f"No training runs found matching '{name}'")
                        input("Press Enter to continue...")
                        return None
                    matching_dirs.sort()
                    return basename(matching_dirs[-1])
                elif selected_menu == 2:
                    # Auto-detect
                    sel = 0
                    while True:
                        stdscr.clear()
                        y = 1
                        y = draw_ascii_art(stdscr, y)
                        y = draw_title(stdscr, y)
                        draw_autodetect_selector(stdscr, runs, sel)
                        stdscr.refresh()
                        key2 = stdscr.getch()
                        if key2 in [curses.KEY_UP, ord('k')]:
                            sel = (sel - 1) % len(runs)
                        elif key2 in [curses.KEY_DOWN, ord('j')]:
                            sel = (sel + 1) % len(runs)
                        elif key2 in [curses.KEY_ENTER, 10, 13]:
                            # Confirmation
                            while True:
                                stdscr.clear()
                                draw_confirmation(stdscr, runs[sel])
                                key3 = stdscr.getch()
                                if key3 in [ord('y'), ord('Y')]:
                                    return runs[sel]
                                elif key3 in [ord('n'), ord('N')]:
                                    break
                        elif key2 in [ord('q'), 27]:
                            break
                elif selected_menu == 3:
                    # Quit
                    curses.endwin()
                    print("No training run selected. Exiting...")
                    exit(0)
    return curses.wrapper(main)

def get_run_by_autodetect():
    runs = find_all_training_runs()
    if not runs:
        print(center_text(f"{Colors.RED}No training runs found!{Colors.RESET}"))
        return None
    return curses_main_menu(runs)

def get_run_directory():
    # Use the new curses menu for everything
    runs = find_all_training_runs()
    return curses_main_menu(runs)

def set_paths(run_name):
    """Set all paths based on the run directory name."""
    base_path = os.path.expanduser("../yolov7-main/runs/train")
    run_path = os.path.join(base_path, run_name)
    
    global RESULTS_FILE, WEIGHTS_DIR, BEST_PT
    RESULTS_FILE = os.path.join(run_path, "results.txt")
    WEIGHTS_DIR = os.path.join(run_path, "weights")
    BEST_PT = os.path.join(WEIGHTS_DIR, "best.pt")

# --- Embedded Fish Art ---
FISH_ART_DATA = '''
12
FISH 1
3,18,-3,R,T
0,1,2,1
STAGE 1
   ,-.       _.-=-._
    \ `,..-"    __  `.
     >  . _     \_`   )
    /_.'    "=.____.-'  
STAGE 2
   ,.       _.-=-._
    \`..-"     _   `.
     > .%_      \'   )
    |.'    "=.____.-'  
STAGE 3
      .      _.-=-._
      |\.  -"       `.
      : .   _       |  )
      |/    "=.____.-'  
FISH 2
3,18,-3,L,T
0,1,2,1
STAGE 1
      _.-=-._       .-,
    .'       __    "-  .,' /
   (      '_     _  .  <
    `-.____.="    `._\  
STAGE 2
      _.-=-._       .,
    .'       _     "-  ..'/
   (      '/      _  . <
    `-.____.="    `.|  
STAGE 3
      _.-=-._      .
    .'           "-  ./|
   (      |       _  . :
    `-.____.="    \|  
FISH 3
3,38,-8,R,F
0,0,0,1,1,1,2,2,2,1,1,1
STAGE 1
                    |`.
    \\              |  \\
  \\ \\             |   \\
  {  \\           /     `~~~--__
  {   \\___----~~'              `~~-_
   \\                           /// 0 `~.  
 / /~~~~-, ,__.    ,      ///  _,,,,_)
 \\/      \\/    `~~~;   ,---~~--`=
                  /   /
                 '._.'  
STAGE 2
                  |`.
    |\\            |  \\
    | |           |   \\
    : |          /     `~~~--__
    :  \\__----~~'              `~~-_
     |                         /// 0  `~.  
  / /~~~-, ,__.    ,      ///  _,,,,_)
  \\/     \\/    `~~~;   ,---~~--`=
                  /   /
                 '._.'  
STAGE 3
                  |`.
       ||         |  \\
       ||         |   \\
       ||        /     `~~~--__
       | \\----~~'              `~~-_
       \\                       /// 0 `~.  
     /|~-, ,__.    ,      ///  _,,,,_)
     \\|  \\/    `~~~;   ,---~~--`=
                  /   /
                 '._.'
FISH 4
3,38,-8,L,F
0,0,0,1,1,1,2,2,2,1,1,1
STAGE 1
                     .'|
                    /  |              /|
                   /   |             / /
           __--~~~'     \\           /  }
      _-~~'              `~~----___/   }
   .~'    ///                          /  
(_,,,,_  ///           .__,  ,~~~~\\ \\
     ='--~~---.   ;~~~'    \\/      \\/
               \\   \\
                `._.`
STAGE 2
                     .'|
                    /  |            /|
                   /   |           | |
           __--~~~'     \\          | :
      _-~~'              `~~----__/  :
  .~'     ///                        /
(_,,,,_  ///           .__,  ,~~\\ \\
     ='--~~---.   ;~~~'    \\/    \\/
               \\   \\
                `._.`
STAGE 3
                     .'|
                    /  |         ||
                   /   |         ||
           __--~~~'     \\        ||
      _-~~'              `~~----/ |
   .~'    ///                      /  
(_,,,,_  ///           .__,  ,~|\\
     ='--~~---.   ;~~~'    \\/  |/
               \\   \\
                `._.`
FISH 5
5,16,0,R,F
0,1,2,1,3,4,4,4,4,3
STAGE 1
  -._.-._.-|``-,
  _.-._.-._|    \\
  -._.-._.-|    /
  .-._.-._.|,.-'  
STAGE 2
    _.-._.-.|`-,
   -._.-._.-|   \\
   .-._.-._.|   /
   -._.-._.-|.-'  
STAGE 3
    __..._.-\\`-,
    .-._.-._.|  \\
    ._.-._.-.|  /
    --.._.-./.-'  
STAGE 4
  .-.-.-.-.|``-,
  -.-.-.-.-|    \\
  -.-.-.-.-|    /
  .-.-.-.-.|,.-'  
STAGE 5
   ---------|`'-,
   ---------|    \\
   ---------|    /
   ---------|,.-'  
FISH 6
5,16,0,L,F
0,1,2,1,3,4,4,4,4,3
STAGE 1
   ,-``|-._.-._.-
  /    |_.-._.-._
  \\    |-._.-._.-
   `-.,|._.-._.-.  
STAGE 2
   ,-'|.-._.-._
  /   |-._.-._.-
  \\   |._.-._.-.
   `-.|-._.-._.-  
STAGE 3
   ,-'/-._...__
  /  |._.-._.-.
  \\  |.-._.-._.
   `-.\.-._..--  
STAGE 4
   ,-``|.-.-.-.-.
  /    |-.-.-.-.-
  \\    |-.-.-.-.-
   `-.,|.-.-.-.-.  
STAGE 5
   ,-'`|---------
  /    |---------
  \\    |---------
   `-.,|---------  
FISH 7
2,14,0,R,F
0,0,1,1
STAGE 1
><> :<>
  ><>  :<>
 :<> :<> <><
:<> <>< <><
  ><> :<> :<>
:<> <>< :<>
 :<>  <><
STAGE 2
:<> <><
  :<>  <><
 ><> <>< :<>
><> :<> :<>
  :<> <>< <><
><> :<> <><
 ><>  :<>
FISH 8
2,14,0,L,F
0,0,1,1
STAGE 1
      <>: <><
   <>:  <><
 <>< <>: <>:
  <>< <>< <>:
<>: <>: <><
  <>: <>< <>:
    <><  <>:
STAGE 2
      <>< <>:
   <><  <>:
 <>: <>< <><
  <>: <>: <><
<>< <>< <>:
  <>< <>: <><
    <>:  <><
'\\
'''

ASCII_ART = [
    "______ _     _                 _ _   _____         _       _             ",
    "|  ___(_)   | |               | | | |_   _|       (_)     (_)            ",
    "| |_   _ ___| |____      _____| | |   | | '__/ _` | | '_ \\| | '_ \\ / _` |",
    "|  _| | / __| '_ \\ \\ /\\ / / _ \\ | |   | | '__/ _` | | '_ \\| | '_ \\ / _` |",
    "| |   | \\__ \\ | | \\ V  V /  __/ | |   | | | | (_| | | | | | | | | | (_| |",
    "\_|   |_|___/_| |_|\_\/_/ \___|_|_|   \_/_|  \__,_|_|_| |_|_|_| |_|\__, |",
    "                                                                    __/ |",
    "                                                                   |___/ ",
    "                  Remember to feed your Haviduck                         "
]

# --- Fish Art Parsing ---
def parse_fish_art_from_string(content):
    fish_defs = []
    lines = content.strip().splitlines()
    num_fish = int(lines[0])
    i = 1
    while i < len(lines):
        if lines[i].startswith('FISH '):
            fish = {}
            i += 1
            # Parse header
            header = lines[i].split(',')
            fish['length'] = int(header[0])
            fish['width'] = int(header[1])
            fish['y_offset'] = int(header[2])
            fish['dir'] = header[3]
            fish['bubble'] = (header[4] == 'T')
            i += 1
            # Parse anim order
            fish['anim_order'] = [int(x) for x in lines[i].split(',')]
            i += 1
            # Parse stages
            stages = []
            while i < len(lines) and lines[i].startswith('STAGE'):
                i += 1
                stage = []
                while i < len(lines) and not lines[i].startswith('STAGE') and not lines[i].startswith('FISH '):
                    stage.append(lines[i])
                    i += 1
                stages.append(stage)
            fish['stages'] = stages
            fish_defs.append(fish)
        else:
            i += 1
    return fish_defs

SEAWEED = ["(( ", " ))"]

# --- Helper functions ---
def parse_results(results_file):
    """Parse the results file and return metrics."""
    metrics = {
        "epoch": [],
        "gflops": [],
        "map": [],
        "loss": [],
        "box_loss": [],
        "cls_loss": [],
        "total": [],
        "labels": [],
        "precision": [],
        "recall": []
    }
    try:
        with open(results_file, 'r') as f:
            for line in f:
                if line.startswith('epoch'):
                    logging.debug(f"Skipping header line: {line.strip()}")
                    continue
                values = line.strip().split()
                if len(values) >= 10:
                    epoch_str = values[0]
                    try:
                        if '/' in epoch_str:
                            current_epoch = int(epoch_str.split('/')[0])
                        else:
                            current_epoch = int(epoch_str)
                        metrics["epoch"].append(current_epoch)
                        gflops = float(values[1].replace('G',''))
                        metrics["gflops"].append(gflops)
                        metrics["map"].append(float(values[2]))
                        metrics["loss"].append(float(values[3]))
                        metrics["box_loss"].append(float(values[4]))
                        metrics["cls_loss"].append(float(values[5]))
                        metrics["total"].append(float(values[5]))
                        metrics["labels"].append(int(values[6]))
                        metrics["precision"].append(float(values[8]))
                        metrics["recall"].append(float(values[9]))
                        logging.debug(f"Parsed line: {line.strip()}")
                    except Exception as e:
                        logging.error(f"Error parsing line: '{line.strip()}': {e}")
                        continue
                else:
                    logging.warning(f"Skipping short line: {line.strip()}")
    except Exception as e:
        logging.error(f"Error opening or reading results file: {e}")
    #logging.info(f"Parsed metrics: { {k: len(v) for k,v in metrics.items()} }")
    return metrics

def detect_overfitting(map_history, patience=5):
    """Return True if mAP@.5 has dropped for 'patience' consecutive epochs."""
    if len(map_history) < patience + 1:
        return False
    drops = 0
    for i in range(-patience, 0):
        if map_history[i] < map_history[i-1]:
            drops += 1
    return drops == patience

def backup_best_weight():
    if not os.path.exists(WEIGHTS_DIR):
        os.makedirs(WEIGHTS_DIR)
    dst = os.path.join(WEIGHTS_DIR, "best.pt")
    if os.path.exists(BEST_PT):
        shutil.copy2(BEST_PT, dst)
        return True
    return False

def analyze_trend(map_hist, window=8):
    if len(map_hist) < window:
        return "Not enough data yet!", "🤔"
    diffs = [map_hist[i] - map_hist[i-1] for i in range(-window+1, 0)]
    avg_diff = sum(diffs)/len(diffs)
    if all(d > 0 for d in diffs):
        return "mAP rising!", "🚀"
    elif all(d < 0 for d in diffs):
        return "mAP dropping!", "😱"
    elif abs(avg_diff) < 0.0005:
        return "Plateau...", "😐"
    elif avg_diff > 0:
        return "Improving!", "😃"
    else:
        return "Getting worse...", "😬"

def get_training_feedback(stats, map_history, loss_history, box_loss_history, cls_loss_history, patience=8):
    feedback = []
    explanations = []
    emoji = ""
    color = curses.color_pair(2)  # green by default
    # Use latest values for all stats
    latest_labels = stats['labels'][-1] if stats['labels'] else 0
    latest_total = stats['total'][-1] if stats['total'] else 0.0
    # Check for no labels
    if latest_labels == 0:
        feedback.append("⚠️ No labels detected! Check your dataset.")
        explanations.append(
            "No labels were found in your data.\n"
            "Why it matters: The model can't learn to detect anything without labels.\n"
            "What to do: Check your dataset paths and annotation format."
        )
        color = curses.color_pair(3)
        emoji = "🚨"
    # Check for NaN or very high loss
    if math.isnan(latest_total) or latest_total > 10.0:
        feedback.append("⚠️ Loss is NaN or very high! Check your data/learning rate.")
        explanations.append(
            "Loss is either not a number (NaN) or extremely high.\n"
            "Why it matters: This usually means a data or configuration problem, and the model isn't learning.\n"
            "What to do: Check your images, labels, and try lowering the learning rate."
        )
        color = curses.color_pair(3)
        emoji = "🔥"
    # Check for mAP not improving
    if len(map_history) > patience:
        recent = map_history[-patience:]
        if all(abs(recent[i] - recent[i-1]) < 1e-4 for i in range(1, len(recent))):
            feedback.append(f"😐 mAP hasn't improved in {patience} epochs. Try more augmentation or lower lr.")
            explanations.append(
                "Your model's mAP (mean Average Precision) has plateaued.\n"
                "Why it matters: The model is no longer getting better at detecting objects on your validation set.\n"
                "What to do: Try increasing data augmentation, lowering the learning rate, or adding more labeled data.\n"
                "If you ignore this: The model may not improve further, and you could be overfitting."
            )
            color = curses.color_pair(3)
            emoji = "😐"
        elif recent[-1] < max(recent[:-1]):
            since = len(recent) - 1 - recent[:-1][::-1].index(max(recent[:-1]))
            feedback.append(f"📉 No new best mAP in {since} epochs.")
            explanations.append(
                "You haven't achieved a new best mAP in several epochs.\n"
                "Why it matters: The model may be plateauing or starting to overfit.\n"
                "What to do: Consider early stopping, more data, or regularization."
            )
            color = curses.color_pair(4)
            emoji = "📉"
    # Check for loss not decreasing
    if len(loss_history) > patience:
        recent = loss_history[-patience:]
        if all(abs(recent[i] - recent[i-1]) < 1e-4 for i in range(1, len(recent))):
            feedback.append(f"😬 Loss hasn't decreased in {patience} epochs.")
            explanations.append(
                "Your model's loss has stopped decreasing.\n"
                "Why it matters: The model may not be learning or could be stuck.\n"
                "What to do: Try adjusting your learning rate, optimizer, or data."
            )
            color = curses.color_pair(3)
            emoji = "😬"
    # Check for box_loss or cls_loss rising after stability/decline
    if len(box_loss_history) > patience:
        recent = box_loss_history[-patience:]
        if all(recent[i] >= recent[i-1] for i in range(1, len(recent))):
            feedback.append(f"🔺 box_loss has been rising for {patience} epochs. Possible overfitting!")
            explanations.append(
                "Your model's box_loss (bounding box regression loss) is increasing after a period of stability or decline.\n"
                "Why it matters: This is a classic sign of overfitting—your model is starting to perform worse on validation data.\n"
                "What to do: Consider early stopping, stronger regularization, or saving the best weights now."
            )
            color = curses.color_pair(3)
            emoji = "🔺"
    if len(cls_loss_history) > patience:
        recent = cls_loss_history[-patience:]
        if all(recent[i] >= recent[i-1] for i in range(1, len(recent))):
            feedback.append(f"🔺 cls_loss has been rising for {patience} epochs. Possible overfitting!")
            explanations.append(
                "Your model's cls_loss (classification loss) is increasing after a period of stability or decline.\n"
                "Why it matters: This is a classic sign of overfitting—your model is starting to perform worse on validation data.\n"
                "What to do: Consider early stopping, stronger regularization, or saving the best weights now."
            )
            color = curses.color_pair(3)
            emoji = "🔺"
    # If everything looks good
    if not feedback:
        feedback.append("✅ Training is progressing well! Keep going! 🚀")
        explanations.append(
            "Your model is learning and improving.\n"
            "Why it matters: You're on track for a good model!\n"
            "What to do: Keep training and monitor for plateaus or overfitting."
        )
        color = curses.color_pair(2)
        emoji = "🎉"
    return feedback, explanations, color, emoji

class Fish:
    def __init__(self, y, x, fish_def):
        self.y = y
        self.x = x
        self.fish_def = fish_def
        self.dir = 1 if fish_def['dir'] == 'R' else -1
        self.length = fish_def['length']
        self.bubble = fish_def['bubble']
        self.anim_order = fish_def['anim_order']
        self.stages = fish_def['stages']
        self.frame_idx = 0
        self.anim_idx = 0
        self.bubble_timer = random.randint(5, 20)
        self.bubble_x = x
        self.bubble_y = y-1
        self.bubble_active = False
        # Ensure animation order indices are valid
        self.anim_order = [idx % len(self.stages) for idx in self.anim_order]

    def move(self, max_x, max_y):
        self.x += self.dir
        # Bounce at edges
        if self.x < 0:
            self.dir = 1
            self.x = 0
        elif self.x > max_x - self.length:
            self.dir = -1
            self.x = max_x - self.length
        # Animation frame cycling
        self.anim_idx = (self.anim_idx + 1) % len(self.anim_order)
        self.frame_idx = self.anim_order[self.anim_idx]
        # Bubble logic
        if self.bubble and self.bubble_active:
            self.bubble_y -= 1
            if self.bubble_y < 1:
                self.bubble_active = False
        elif self.bubble:
            self.bubble_timer -= 1
            if self.bubble_timer <= 0:
                self.bubble_active = True
                self.bubble_x = self.x + (self.length//2 if self.dir==1 else 0)
                self.bubble_y = self.y-1
                self.bubble_timer = random.randint(10, 30)

    def get_frame(self):
        # Ensure frame_idx is within bounds
        if not self.stages or self.frame_idx >= len(self.stages):
            self.frame_idx = 0
        return self.stages[self.frame_idx]

def draw_line_chart(stdscr, box_y, box_x, box_height, box_width, values, color_pair=2, label="mAP"):
    """Draw a Unicode/ASCII line chart for the given values inside the info box."""
    if not values:
        return
    chart_height = box_height - 3
    chart_width = box_width - 6
    min_val = min(values)
    max_val = max(values)
    if max_val == min_val:
        max_val += 1e-6
    # Always show the full history, scaled to fit chart_width
    if len(values) > chart_width:
        idxs = [int(i * (len(values) - 1) / (chart_width - 1)) for i in range(chart_width)]
        scaled_values = [values[i] for i in idxs]
    else:
        scaled_values = values[:]
        scaled_values += [values[-1]] * (chart_width - len(values))
    scaled = [int((v - min_val) / (max_val - min_val) * (chart_height-1)) for v in scaled_values]
    # Draw axes
    for h in range(chart_height):
        stdscr.addstr(box_y+1+h, box_x+2, '|', curses.color_pair(color_pair))
    stdscr.addstr(box_y+chart_height+1, box_x+2, '+', curses.color_pair(color_pair))
    for x in range(chart_width):
        stdscr.addstr(box_y+chart_height+1, box_x+3+x, '-', curses.color_pair(color_pair))
    # Draw line
    for x, y in enumerate(scaled):
        y_pos = box_y+chart_height - y
        if 0 <= y_pos < box_y+box_height-1:
            stdscr.addstr(y_pos, box_x+3+x, '•', curses.color_pair(color_pair))
    # Draw label
    stdscr.addstr(box_y, box_x+2, f"{label} trend", curses.color_pair(color_pair) | curses.A_BOLD)

def wrap_lines(lines, width):
    """Wrap each string in lines to the given width."""
    wrapped = []
    for line in lines:
        wrapped.extend(textwrap.wrap(line, width=width))
    return wrapped

def aquarium(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_YELLOW, -1)  # Fish
    curses.init_pair(2, curses.COLOR_CYAN, -1)    # Info, seaweed
    curses.init_pair(3, curses.COLOR_MAGENTA, -1) # Crab
    curses.init_pair(4, curses.COLOR_WHITE, -1)   # Bubbles
    curses.init_pair(5, curses.COLOR_GREEN, -1)   # Info box border
    curses.init_pair(6, curses.COLOR_RED, -1)     # Warnings/errors
    min_height = INFO_BOX_HEIGHT + 8
    min_width = INFO_BOX_WIDTH * 3 + 8
    pause = 0.12
    map_history = []
    loss_history = []
    box_loss_history = []
    cls_loss_history = []
    overfit_notified = False
    info_message = "Training in progress..."
    last_backup_epoch = None
    best_map = 0.0
    fish_list = []
    animated_fish_defs = parse_fish_art_from_string(FISH_ART_DATA)
    ai_feedback = None
    ai_last_epoch = -1000
    AI_FEEDBACK_INTERVAL = 5  # epochs
    backup_message = None
    advice_message = None
    backup_message_time = 0
    advice_message_time = 0
    message_display_duration = 4  # seconds
    last_key_time = time.time()
    # In aquarium(), add a flag to track if we've already auto-backed up for this overfitting event
    overfit_auto_backup_epoch = None
    # Duck animation state
    duck_art = [
        "   __",
        "<(o )___",
        " ( ._> /",
        "  `---' "
    ]
    duck_x = 0
    duck_dir = 1

    def spawn_fish(max_x, max_y, avoid_boxes):
        for _ in range(20):
            fish_def = random.choice(animated_fish_defs)
            y = random.randint(4, max_y-INFO_BOX_HEIGHT-6)
            x = 0 if fish_def['dir']=='R' else max_x-fish_def['length']-1
            fish_area = set((y+i, x+j) for i in range(fish_def['length']) for j in range(fish_def['width']))
            overlap = False
            for (box_y, box_x, box_h, box_w) in avoid_boxes:
                for fy, fx in fish_area:
                    if box_y <= fy < box_y+box_h and box_x <= fx < box_x+box_w:
                        overlap = True
                        break
                if overlap:
                    break
            if not overlap:
                return Fish(y, x, fish_def)

    MAX_INFO_BOX_HEIGHT = 18
    INFO_BOX_GAP = 4
    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        if max_y < min_height or max_x < min_width:
            warning = f"Terminal too small! Resize to at least {min_width}x{min_height}."
            stdscr.addstr(0, 0, warning[:max_x-1])
            stdscr.refresh()
            time.sleep(0.5)
            continue
        # Draw ASCII art (logo) at the top
        for i, line in enumerate(ASCII_ART):
            y = i+1
            x = (max_x - len(line))//2
            if 0 <= y < max_y and 0 <= x < max_x:
                stdscr.addstr(y, x, line[:max_x-x], curses.A_BOLD)
        # Info box positions
        box_w = INFO_BOX_WIDTH
        box_h = INFO_BOX_HEIGHT
        left_box_y = max_y//2 - box_h//2 + len(ASCII_ART)//2 - 2
        left_box_x = max_x//6 - box_w//2
        center_box_y = left_box_y
        center_box_x = max_x//2 - box_w//2
        right_box_y = left_box_y
        right_box_x = max_x*5//6 - box_w//2
        box_areas = [
            (left_box_y, left_box_x, box_h, box_w),
            (center_box_y, center_box_x, box_h, box_w),
            (right_box_y, right_box_x, box_h, box_w)
        ]
        # Animate seaweed (avoid info box area)
        for y in range(max_y-2, max_y):
            for x in range(0, max_x, 4):
                in_box = False
                for (by, bx, bh, bw) in box_areas:
                    if by <= y < by+bh and bx <= x < bx+bw:
                        in_box = True
                        break
                if not in_box and 0 <= y < max_y and 0 <= x < max_x-3:
                    stdscr.addstr(y, x, SEAWEED[(x//4 + int(time.time()*2))%2][:max_x-x], curses.color_pair(2))
        # Animate fish (avoid info box area, but not logo)
        if len(fish_list) < 4:
            fish_list.append(spawn_fish(max_x, max_y, box_areas))
        for fish in fish_list:
            fish.move(max_x, max_y)
            frame = fish.get_frame()
            for i, line in enumerate(frame):
                draw_y = fish.y + i
                draw_x = fish.x
                in_box = False
                for (by, bx, bh, bw) in box_areas:
                    if by <= draw_y < by+bh and bx <= draw_x < bx+bw:
                        in_box = True
                        break
                if not in_box and 0 <= draw_y < max_y and 0 <= draw_x < max_x - len(line):
                    stdscr.addstr(draw_y, draw_x, line[:max_x-draw_x], curses.color_pair(1))
            if fish.bubble and fish.bubble_active and 0 < fish.bubble_y < max_y and 0 < fish.bubble_x < max_x:
                stdscr.addstr(fish.bubble_y, fish.bubble_x, "o", curses.color_pair(4))
        # Animate a crab (optional)
        crab = [
            "      ,~~.",
            " ,   (  - )>",
            " )`~~'   (",
            "(  .__)   )",
            " `-.____,' "
        ]
        crab_y = max_y-7
        crab_x = (max_x//2)-8
        for i, line in enumerate(crab):
            if 0 <= crab_y+i < max_y and 0 <= crab_x < max_x:
                stdscr.addstr(crab_y+i, crab_x, line[:max_x-crab_x], curses.color_pair(3))
        # --- Info/analysis box drawing ---
        stats = parse_results(RESULTS_FILE)
        current_epoch = stats['epoch'][-1] if stats and stats['epoch'] else 0
        # Call AI feedback every N epochs
        if stats and stats['epoch'] and (current_epoch - ai_last_epoch >= AI_FEEDBACK_INTERVAL):
            try:
                ai_feedback = get_ai_analysis(stats)
                ai_last_epoch = current_epoch
            except Exception as e:
                logging.error(f"AI feedback error: {e}")
                ai_feedback = None
        # LEFT BOX: mAP line chart + stats
        left_lines = []
        if stats and stats['map']:
            map_history.append(stats['map'][-1])
            loss_history.append(stats['loss'][-1])
            box_loss_history.append(stats['box_loss'][-1])
            cls_loss_history.append(stats['cls_loss'][-1])
            if stats['map'][-1] > best_map:
                best_map = stats['map'][-1]
            try:
                epoch_num = stats['epoch'][-1]
                epoch_total = len(stats['epoch'])
            except Exception:
                epoch_num, epoch_total = 0, 200
            # COMPACT SUMMARY: Only show latest values
            left_lines.append(f"Epoch: {epoch_num}  mAP@.5: {stats['map'][-1]:.4f} (Best: {best_map:.4f})")
            left_lines.append(f"Loss: {stats['loss'][-1]:.4f}  Labels: {stats['labels'][-1] if stats['labels'] else 0}")
            left_lines.append(f"P: {stats['precision'][-1]:.4f}  R: {stats['recall'][-1]:.4f}")
            left_lines.append("")
        else:
            left_lines = ["No results yet or results.txt is empty."]
        # Draw left info box border
        for i in range(box_w):
            if 0 <= left_box_y < max_y and 0 <= left_box_x + i < max_x:
                stdscr.addch(left_box_y, left_box_x + i, ord('-'), curses.color_pair(5))
            if 0 <= left_box_y + box_h - 1 < max_y and 0 <= left_box_x + i < max_x:
                stdscr.addch(left_box_y + box_h - 1, left_box_x + i, ord('-'), curses.color_pair(5))
        for i in range(box_h):
            if 0 <= left_box_y + i < max_y and 0 <= left_box_x < max_x:
                stdscr.addch(left_box_y + i, left_box_x, ord('|'), curses.color_pair(5))
            if 0 <= left_box_y + i < max_y and 0 <= left_box_x + box_w - 1 < max_x:
                stdscr.addch(left_box_y + i, left_box_x + box_w - 1, ord('|'), curses.color_pair(5))
        # Corners
        if 0 <= left_box_y < max_y and 0 <= left_box_x < max_x:
            stdscr.addch(left_box_y, left_box_x, ord('+'), curses.color_pair(5))
        if 0 <= left_box_y < max_y and 0 <= left_box_x + box_w - 1 < max_x:
            stdscr.addch(left_box_y, left_box_x + box_w - 1, ord('+'), curses.color_pair(5))
        if 0 <= left_box_y + box_h - 1 < max_y and 0 <= left_box_x < max_x:
            stdscr.addch(left_box_y + box_h - 1, left_box_x, ord('+'), curses.color_pair(5))
        if 0 <= left_box_y + box_h - 1 < max_y and 0 <= left_box_x + box_w - 1 < max_x:
            stdscr.addch(left_box_y + box_h - 1, left_box_x + box_w - 1, ord('+'), curses.color_pair(5))
        # Draw left info text (leave more room for chart)
        max_info_lines = box_h - 10  # leave more space for chart
        for idx, line in enumerate(wrap_lines(left_lines, box_w-4)[:max_info_lines]):
            y = left_box_y + 1 + idx
            x = left_box_x + 2
            if 0 <= y < max_y and 0 <= x < max_x:
                stdscr.addstr(y, x, line[:max_x-x][:box_w-4], curses.color_pair(2))
        # Draw mAP line chart (use more vertical space)
        draw_line_chart(stdscr, left_box_y+box_h-9, left_box_x, 8, box_w, map_history, color_pair=2, label="mAP")

        # --- Restore right info box drawing ---
        right_lines = []
        if ai_feedback and not ai_feedback.get('error'):
            if ai_feedback.get('risks'):
                right_lines.append('Risks:')
                right_lines.extend(wrap_lines([f"- {r}" for r in ai_feedback['risks']], box_w-4))
            if ai_feedback.get('trends'):
                right_lines.append('Trends:')
                right_lines.extend(wrap_lines([f"- {t}" for t in ai_feedback['trends']], box_w-4))
            if ai_feedback.get('recommendations'):
                right_lines.append('Recommendations:')
                right_lines.extend(wrap_lines([f"* {rec}" for rec in ai_feedback['recommendations']], box_w-4))
            if ai_feedback.get('metrics'):
                right_lines.append('Metrics:')
                right_lines.extend(wrap_lines([f"• {m}" for m in ai_feedback['metrics']], box_w-4))
        elif ai_feedback and ai_feedback.get('error'):
            right_lines.append("AI Feedback unavailable.")
        elif not ai_feedback:
            right_lines.append("Waiting for AI feedback...")
        # Draw right info box border
        for i in range(box_w):
            if 0 <= right_box_y < max_y and 0 <= right_box_x + i < max_x:
                stdscr.addch(right_box_y, right_box_x + i, ord('-'), curses.color_pair(5))
            if 0 <= right_box_y + box_h - 1 < max_y and 0 <= right_box_x + i < max_x:
                stdscr.addch(right_box_y + box_h - 1, right_box_x + i, ord('-'), curses.color_pair(5))
        for i in range(box_h):
            if 0 <= right_box_y + i < max_y and 0 <= right_box_x < max_x:
                stdscr.addch(right_box_y + i, right_box_x, ord('|'), curses.color_pair(5))
            if 0 <= right_box_y + i < max_y and 0 <= right_box_x + box_w - 1 < max_x:
                stdscr.addch(right_box_y + i, right_box_x + box_w - 1, ord('|'), curses.color_pair(5))
        # Corners
        if 0 <= right_box_y < max_y and 0 <= right_box_x < max_x:
            stdscr.addch(right_box_y, right_box_x, ord('+'), curses.color_pair(5))
        if 0 <= right_box_y < max_y and 0 <= right_box_x + box_w - 1 < max_x:
            stdscr.addch(right_box_y, right_box_x + box_w - 1, ord('+'), curses.color_pair(5))
        if 0 <= right_box_y + box_h - 1 < max_y and 0 <= right_box_x < max_x:
            stdscr.addch(right_box_y + box_h - 1, right_box_x, ord('+'), curses.color_pair(5))
        if 0 <= right_box_y + box_h - 1 < max_y and 0 <= right_box_x + box_w - 1 < max_x:
            stdscr.addch(right_box_y + box_h - 1, right_box_x + box_w - 1, ord('+'), curses.color_pair(5))
        # Draw right info text
        for idx, line in enumerate(right_lines[:box_h-2]):
            y = right_box_y + 1 + idx
            x = right_box_x + 2
            if 0 <= y < max_y and 0 <= x < max_x:
                stdscr.addstr(y, x, line[:max_x-x][:box_w-4], curses.color_pair(2))

        # --- Center box drawing (centered, list-like) ---
        center_lines = []
        overfitting_detected = False
        if ai_feedback and not ai_feedback.get('error'):
            summary = ai_feedback.get('summary', 'No summary.')
            if ai_feedback.get('isoverfitted', False):
                overfitting_detected = True
                if (overfit_auto_backup_epoch != current_epoch):
                    backup_dir = WEIGHTS_DIR
                    if not os.path.exists(backup_dir):
                        os.makedirs(backup_dir)
                    latest_weight = BEST_PT if os.path.exists(BEST_PT) else None
                    if latest_weight:
                        backup_path = os.path.join(backup_dir, f"overfit_{int(time.time())}.pt")
                        shutil.copy2(latest_weight, backup_path)
                        backup_message = f"✅ Weights auto-saved to {backup_path} (overfitting)"
                        backup_message_time = time.time()
                        logging.info(f"Auto overfitting backup completed: {backup_path}")
                        overfit_auto_backup_epoch = current_epoch
                    else:
                        backup_message = "❌ No weight file found to auto-save."
                        backup_message_time = time.time()
                        logging.warning("No weight file found for auto overfitting save")
            # Center and listify summary
            summary_lines = wrap_lines([summary], box_w-10)
            # Add bullet points if summary has sentences
            summary_bullets = []
            for line in summary_lines:
                for sent in line.split('. '):
                    sent = sent.strip()
                    if sent:
                        summary_bullets.append(f"• {sent}")
            # Add vertical padding to center
            pad_top = (box_h - len(summary_bullets)) // 2
            center_lines.extend([''] * pad_top)
            for line in summary_bullets:
                # Center horizontally
                center_lines.append(line.center(box_w-4))
            pad_bottom = box_h - len(center_lines)
            center_lines.extend([''] * pad_bottom)
        elif ai_feedback and ai_feedback.get('error'):
            center_lines.append("AI Feedback unavailable.")
        elif not ai_feedback:
            center_lines.append("Waiting for AI feedback...")
        if overfitting_detected:
            center_lines.append("")
            center_lines.append("🚨 Overfitting detected! [S] Save weights now".center(box_w-4))
        center_lines.append("")
        # Show backup or advice message if set
        now = time.time()
        if backup_message and now - backup_message_time < message_display_duration:
            center_lines.append("")
            center_lines.append(backup_message.center(box_w-4))
        if advice_message and now - advice_message_time < message_display_duration:
            center_lines.append("")
            for l in wrap_lines([advice_message], box_w-10):
                center_lines.append(l.center(box_w-4))
        for i in range(box_w):
            if 0 <= center_box_y-1 < max_y and 0 <= center_box_x + i < max_x:
                stdscr.addch(center_box_y-1, center_box_x + i, ord('='), curses.color_pair(5) | curses.A_BOLD)
            if 0 <= center_box_y + box_h < max_y and 0 <= center_box_x + i < max_x:
                stdscr.addch(center_box_y + box_h, center_box_x + i, ord('='), curses.color_pair(5) | curses.A_BOLD)
        if 0 <= center_box_y-1 < max_y and 0 <= center_box_x-1 < max_x:
            stdscr.addch(center_box_y-1, center_box_x-1, ord('#'), curses.color_pair(5) | curses.A_BOLD)
        if 0 <= center_box_y-1 < max_y and 0 <= center_box_x + box_w < max_x:
            stdscr.addch(center_box_y-1, center_box_x + box_w, ord('#'), curses.color_pair(5) | curses.A_BOLD)
        if 0 <= center_box_y + box_h < max_y and 0 <= center_box_x-1 < max_x:
            stdscr.addch(center_box_y + box_h, center_box_x-1, ord('#'), curses.color_pair(5) | curses.A_BOLD)
        if 0 <= center_box_y + box_h < max_y and 0 <= center_box_x + box_w < max_x:
            stdscr.addch(center_box_y + box_h, center_box_x + box_w, ord('#'), curses.color_pair(5) | curses.A_BOLD)
        for idx, line in enumerate(center_lines[:box_h]):
            y = center_box_y + idx
            x = center_box_x + 2
            if 0 <= y < max_y and 0 <= x < max_x:
                stdscr.addstr(y, x, line[:max_x-x][:box_w-4], curses.color_pair(2) | curses.A_BOLD)
        stdscr.refresh()

        # --- Restore right info box drawing (add paragraph spacing) ---
        right_lines = []
        if ai_feedback and not ai_feedback.get('error'):
            if ai_feedback.get('risks'):
                right_lines.append('Risks:')
                right_lines.extend(wrap_lines([f"- {r}" for r in ai_feedback['risks']], box_w-4))
                right_lines.append('')
            if ai_feedback.get('trends'):
                right_lines.append('Trends:')
                right_lines.extend(wrap_lines([f"- {t}" for t in ai_feedback['trends']], box_w-4))
                right_lines.append('')
            if ai_feedback.get('recommendations'):
                right_lines.append('Recommendations:')
                right_lines.extend(wrap_lines([f"* {rec}" for rec in ai_feedback['recommendations']], box_w-4))
                right_lines.append('')
            if ai_feedback.get('metrics'):
                right_lines.append('Metrics:')
                right_lines.extend(wrap_lines([f"• {m}" for m in ai_feedback['metrics']], box_w-4))
        elif ai_feedback and ai_feedback.get('error'):
            right_lines.append("AI Feedback unavailable.")
        elif not ai_feedback:
            right_lines.append("Waiting for AI feedback...")
        # Draw right info box border and text as before
        for i in range(box_w):
            if 0 <= right_box_y < max_y and 0 <= right_box_x + i < max_x:
                stdscr.addch(right_box_y, right_box_x + i, ord('-'), curses.color_pair(5))
            if 0 <= right_box_y + box_h - 1 < max_y and 0 <= right_box_x + i < max_x:
                stdscr.addch(right_box_y + box_h - 1, right_box_x + i, ord('-'), curses.color_pair(5))
        for i in range(box_h):
            if 0 <= right_box_y + i < max_y and 0 <= right_box_x < max_x:
                stdscr.addch(right_box_y + i, right_box_x, ord('|'), curses.color_pair(5))
            if 0 <= right_box_y + i < max_y and 0 <= right_box_x + box_w - 1 < max_x:
                stdscr.addch(right_box_y + i, right_box_x + box_w - 1, ord('|'), curses.color_pair(5))
        # Corners
        if 0 <= right_box_y < max_y and 0 <= right_box_x < max_x:
            stdscr.addch(right_box_y, right_box_x, ord('+'), curses.color_pair(5))
        if 0 <= right_box_y < max_y and 0 <= right_box_x + box_w - 1 < max_x:
            stdscr.addch(right_box_y, right_box_x + box_w - 1, ord('+'), curses.color_pair(5))
        if 0 <= right_box_y + box_h - 1 < max_y and 0 <= right_box_x < max_x:
            stdscr.addch(right_box_y + box_h - 1, right_box_x, ord('+'), curses.color_pair(5))
        if 0 <= right_box_y + box_h - 1 < max_y and 0 <= right_box_x + box_w - 1 < max_x:
            stdscr.addch(right_box_y + box_h - 1, right_box_x + box_w - 1, ord('+'), curses.color_pair(5))
        # Draw right info text
        for idx, line in enumerate(right_lines[:box_h-2]):
            y = right_box_y + 1 + idx
            x = right_box_x + 2
            if 0 <= y < max_y and 0 <= x < max_x:
                stdscr.addstr(y, x, line[:max_x-x][:box_w-4], curses.color_pair(2))

        # Remove seaweed at the bottom (do not draw it)
        # Animate duck at the bottom, moving left/right
        duck_y = max_y - len(duck_art) - 1
        if duck_x + len(duck_art[1]) >= max_x:
            duck_dir = -1
        if duck_x <= 0:
            duck_dir = 1
        for i, line in enumerate(duck_art):
            if 0 <= duck_y + i < max_y and 0 <= duck_x < max_x:
                stdscr.addstr(duck_y + i, duck_x, line[:max_x-duck_x], curses.color_pair(3))
        duck_x += duck_dir

        # Handle keypresses for backup, save, and life advice
        key = stdscr.getch()
        logging.debug(f"Aquarium keypress: {key}")
        if key in [ord('b'), ord('B')]:
            logging.info("[B] key pressed for backup")
            backup_dir = WEIGHTS_DIR
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            latest_weight = BEST_PT if os.path.exists(BEST_PT) else None
            if latest_weight:
                backup_path = os.path.join(backup_dir, f"backup_{int(time.time())}.pt")
                shutil.copy2(latest_weight, backup_path)
                backup_message = f"✅ Weights backed up to {backup_path}"
                backup_message_time = time.time()
                logging.info(f"Backup completed: {backup_path}")
            else:
                backup_message = "❌ No weight file found to backup."
                backup_message_time = time.time()
                logging.warning("No weight file found for backup")
        elif key in [ord('s'), ord('S')]:
            logging.info("[S] key pressed for overfitting/manual save")
            backup_dir = WEIGHTS_DIR
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            latest_weight = BEST_PT if os.path.exists(BEST_PT) else None
            if latest_weight:
                backup_path = os.path.join(backup_dir, f"manual_{int(time.time())}.pt")
                shutil.copy2(latest_weight, backup_path)
                backup_message = f"✅ Weights saved to {backup_path} (manual)"
                backup_message_time = time.time()
                logging.info(f"Manual backup completed: {backup_path}")
            else:
                backup_message = "❌ No weight file found to save."
                backup_message_time = time.time()
                logging.warning("No weight file found for manual save")
        elif key in [ord('l'), ord('L')]:
            logging.info("[L] key pressed for life advice")
            advice_prompt = (
                "Give me a funny, ML-themed life advice for a machine learning engineer, related to model training, overfitting, or debugging. Make it fit the context of someone training YOLOv7 or deep learning models in a terminal aquarium UI. 2-3 lines, with emojis."
            )
            try:
                advice_data = {
                    "model": "gpt-4-turbo-preview",
                    "messages": [{"role": "user", "content": advice_prompt}],
                    "temperature": 0.7,
                    "max_tokens": 100
                }
                advice_headers = {
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                }
                advice_response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=advice_headers,
                    json=advice_data,
                    timeout=30
                )
                advice_response.raise_for_status()
                advice_content = advice_response.json()["choices"][0]["message"]["content"]
                advice_message = advice_content
                advice_message_time = time.time()
                logging.info(f"Life advice received: {advice_content}")
            except Exception as e:
                advice_message = f"❌ Failed to get life advice: {e}"
                advice_message_time = time.time()
                logging.error(f"Failed to get life advice: {e}")
        elif key != -1:
            # Any other key clears messages
            backup_message = None
            advice_message = None
        time.sleep(pause)
        try:
            key = stdscr.getch()
            if key == ord('q'):
                break
        except Exception:
            pass

def get_ai_analysis(metrics_data):
    """Get AI analysis of training metrics using either ChatGPT or Claude."""
    
    # Prepare the metrics data
    metrics_str = json.dumps(metrics_data, indent=2)
    
    if USE_CHATGPT:
        return get_chatgpt_analysis(metrics_str)
    else:
        return get_claude_analysis(metrics_str)

def get_chatgpt_analysis(metrics_str):
    """Get analysis from ChatGPT."""
    # Parse metrics to get current epoch
    try:
        metrics = json.loads(metrics_str)
        current_epoch = metrics.get('epoch', [0])[-1]
        logging.info(f"Current epoch: {current_epoch}")
    except Exception as e:
        logging.error(f"Error parsing metrics for epoch: {e}")
        current_epoch = 0

    prompt = f"""Analyze these YOLOv7 training metrics and provide a detailed, actionable, and emoji-rich response for a terminal UI with three info boxes. For each field, wrap lines at 48 characters or less so nothing overflows. Use these fields:

1. summary: 3-4 sentences summarizing training status (with emoji/icons, line-wrapped). If overfitting is detected, make it clear and urgent.
2. risks: List of 4-5 key risks/issues (each 1-2 lines, with emoji/icons, line-wrapped).
3. trends: List of 4-5 key metric trends (each 1-2 lines, with emoji/icons, line-wrapped).
4. recommendations: 4-5 actionable recommendations (each 1-2 lines, with emoji/icons, line-wrapped).
5. metrics: List of key numbers (epoch, mAP, loss, precision, recall, etc), line-wrapped.
6. isoverfitted: true/false (boolean, not string). This must be true ONLY if the model is clearly overfitting (see below).

IMPORTANT: The model is currently at epoch {current_epoch}. Do not mention overfitting or set isoverfitted true unless the epoch is above 50 and the signs are very clear (see below). Overfitting detection rules:
- DO NOT flag overfitting or set isoverfitted true before epoch 50
- Only set isoverfitted true if ALL of these are true:
  * Model is past epoch 50
  * Validation metrics (mAP, precision, recall) have been consistently declining for at least 10 epochs
  * Training metrics continue to improve while validation metrics decline
  * The gap between training and validation performance is growing significantly
- For early training (before epoch 50), focus on:
  * Learning rate effectiveness
  * Data quality and augmentation
  * Model convergence
  * General training stability

Format your response as JSON with these exact keys:
{{{{
  \"summary\": \"...\",
  \"risks\": [\"...\", ...],
  \"trends\": [\"...\", ...],
  \"recommendations\": [\"...\", ...],
  \"metrics\": [\"...\", ...],
  \"isoverfitted\": false
}}}}

Be concise but informative, use only the most relevant information, and always use emojis/icons for clarity and fun. Do not use markdown or code blocks.

Metrics data:
{metrics_str}"""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4-turbo-preview",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 900
    }
    try:
        logging.info(f"ChatGPT prompt length: {len(prompt)}")
        logging.info(f"ChatGPT payload: {json.dumps(data)[:1000]}... (truncated)")
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        logging.info(f"ChatGPT API HTTP status: {response.status_code}")
        logging.info(f"ChatGPT API raw response: {response.text[:1000]}... (truncated)")
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        logging.info(f"ChatGPT API parsed content: {content}")
        # Strip markdown formatting if present
        if content.startswith("```json"):
            content = content.split("```json")[1]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()
        logging.info(f"Cleaned content for JSON parsing: {content}")
        analysis = json.loads(content)
        # Ensure all expected fields are present, defaulting if missing
        expected_fields = {
            "summary": "No summary.",
            "risks": [],
            "trends": [],
            "recommendations": [],
            "metrics": [],
            "isoverfitted": False
        }
        for key, default in expected_fields.items():
            if key not in analysis:
                analysis[key] = default
        return analysis
    except Exception as e:
        logging.error(f"Failed to get ChatGPT analysis: {str(e)}")
        return {
            "error": f"Failed to get ChatGPT analysis: {str(e)}",
            "summary": "No summary.",
            "risks": [],
            "trends": [],
            "recommendations": [],
            "metrics": [],
            "isoverfitted": False
        }

def get_claude_analysis(metrics_str):
    """Get analysis from Claude."""
    # Similar implementation for Claude API
    # Add your Claude API implementation here
    pass

def analyze_training(stdscr):
    """Main training analysis loop with AI integration."""
    curses.curs_set(0)
    stdscr.clear()
    
    # Initialize windows
    height, width = stdscr.getmaxyx()
    center_box = curses.newwin(INFO_BOX_HEIGHT, INFO_BOX_WIDTH, 2, (width - INFO_BOX_WIDTH) // 2)
    right_box = curses.newwin(INFO_BOX_HEIGHT, INFO_BOX_WIDTH, 2, width - INFO_BOX_WIDTH - 2)
    
    last_analysis_epoch = 0
    ai_analysis = None
    
    while True:
        # Parse current results
        metrics = parse_results(RESULTS_FILE)
        # Check for empty metrics
        if not metrics["epoch"] or not metrics["map"] or not metrics["loss"] or not metrics["precision"] or not metrics["recall"]:
            center_box.clear()
            center_box.box()
            center_box.addstr(2, 2, "No results yet or results.txt is empty.")
            center_box.refresh()
            right_box.clear()
            right_box.box()
            right_box.addstr(2, 2, "AI Analysis:")
            right_box.refresh()
            time.sleep(1)
            continue
        current_epoch = metrics["epoch"][-1]
        # Get AI analysis every ANALYSIS_INTERVAL epochs
        if current_epoch - last_analysis_epoch >= ANALYSIS_INTERVAL:
            ai_analysis = get_ai_analysis(metrics)
            last_analysis_epoch = current_epoch
            # Backup weights if AI suggests
            if ai_analysis.get("should_backup_weights", False):
                backup_best_weight()
        # Update center box with current metrics
        center_box.clear()
        center_box.box()
        center_box.addstr(1, 2, f"Epoch: {current_epoch}")
        center_box.addstr(2, 2, f"mAP: {metrics['map'][-1]:.4f}")
        center_box.addstr(3, 2, f"Loss: {metrics['loss'][-1]:.4f}")
        center_box.addstr(4, 2, f"Precision: {metrics['precision'][-1]:.4f}")
        center_box.addstr(5, 2, f"Recall: {metrics['recall'][-1]:.4f}")
        center_box.refresh()
        # Update right box with AI insights
        right_box.clear()
        right_box.box()
        right_box.addstr(1, 2, "AI Analysis:")
        if ai_analysis:
            right_box.addstr(2, 2, f"Risk: {ai_analysis['overfitting_risk']}")
            right_box.addstr(3, 2, f"Stability: {ai_analysis['training_stability']}")
            for i, trend in enumerate(ai_analysis['key_trends'][:2]):
                right_box.addstr(4 + i, 2, f"• {trend}")
        right_box.refresh()
        time.sleep(1)

def loading_spinner_and_ai(run_name):
    import itertools
    import threading
    import queue
    import curses
    import signal
    
    # Flag to control the spinner thread
    spinner_running = threading.Event()
    spinner_running.set()
    
    def spinner_curses(stdscr, status_queue):
        curses.curs_set(0)
        stdscr.nodelay(True)
        h, w = stdscr.getmaxyx()
        spinner = itertools.cycle(['|', '/', '-', '\\'])
        status = "Asking A.I."
        
        while spinner_running.is_set():
            try:
                stdscr.clear()
                msg = "Loading..."
                spin = next(spinner)
                stdscr.addstr(h//2-2, (w-len(msg))//2, msg, curses.A_BOLD)
                stdscr.addstr(h//2, (w-1)//2, spin, curses.A_BOLD)
                stdscr.addstr(h//2+2, (w-len(status))//2, status)
                stdscr.refresh()
                
                try:
                    new_status = status_queue.get_nowait()
                    if isinstance(new_status, str):
                        if new_status == 'done':
                            break
                        status = new_status
                    elif isinstance(new_status, tuple) and new_status[0] == 'result':
                        # Store result but keep showing spinner
                        continue
                except queue.Empty:
                    pass
                
                time.sleep(0.1)
            except (curses.error, KeyboardInterrupt):
                break

    def fetch_ai_first_response(status_queue, run_name):
        try:
            # Prepare metrics for the selected run
            set_paths(run_name)
            stats = parse_results(RESULTS_FILE)
            status_queue.put("Asking A.I.")
            
            response = get_ai_analysis(stats)
            status_queue.put("Analyzing training data...")
            status_queue.put(('result', response))
            status_queue.put("Done!")
        except Exception as e:
            status_queue.put(f"Error: {e}")
            status_queue.put(('result', None))
        finally:
            status_queue.put('done')
            spinner_running.clear()

    # Use a thread to fetch AI while spinner runs
    status_queue = queue.Queue()
    ai_result = [None]
    
    def ai_thread():
        fetch_ai_first_response(status_queue, run_name)
    
    t = threading.Thread(target=ai_thread)
    t.daemon = True  # Make thread daemon so it exits when main thread exits
    t.start()
    
    try:
        curses.wrapper(spinner_curses, status_queue)
    except KeyboardInterrupt:
        spinner_running.clear()
        print("\nOperation cancelled by user.")
        return None
    except Exception as e:
        logging.error(f"Spinner error: {e}")
        spinner_running.clear()
    
    # Get the result with timeout
    try:
        while True:
            try:
                item = status_queue.get(timeout=1.0)  # 1 second timeout
                if isinstance(item, tuple) and item[0] == 'result':
                    ai_result[0] = item[1]
                    break
            except queue.Empty:
                if not t.is_alive():
                    break
    except KeyboardInterrupt:
        spinner_running.clear()
        print("\nOperation cancelled by user.")
        return None
    
    return ai_result[0]

def overfit_prompt(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    h, w = stdscr.getmaxyx()
    msg = "🚨 Overfitting detected! Back up model? (y/n)"
    logging.info("Showing overfit prompt")
    stdscr.addstr(h//2, (w-len(msg))//2, msg, curses.A_BOLD)
    stdscr.refresh()
    start = time.time()
    
    while True:
        try:
            key = stdscr.getch()
            logging.debug(f"Key pressed: {key}")
            if key != -1:  # Only process if a key was pressed
                if key in [ord('y'), ord('Y')]:
                    logging.info("User chose to backup")
                    backup_dir = WEIGHTS_DIR
                    if not os.path.exists(backup_dir):
                        os.makedirs(backup_dir)
                    latest_weight = BEST_PT if os.path.exists(BEST_PT) else None
                    if latest_weight:
                        backup_path = os.path.join(backup_dir, f"backup_{int(time.time())}.pt")
                        shutil.copy2(latest_weight, backup_path)
                        confirm = f"✅ Weights backed up to {backup_path}"
                        logging.info(f"Backup successful: {backup_path}")
                    else:
                        confirm = "❌ No weight file found to backup."
                        logging.warning("No weight file found for backup")
                    stdscr.clear()
                    stdscr.addstr(h//2, (w-len(confirm))//2, confirm, curses.A_BOLD)
                    stdscr.refresh()
                    time.sleep(2)
                    return True
                elif key in [ord('n'), ord('N')]:
                    logging.info("User chose not to backup")
                    return False
            elif time.time() - start > 120:
                logging.info("Auto-backup triggered after timeout")
                backup_dir = WEIGHTS_DIR
                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir)
                latest_weight = BEST_PT if os.path.exists(BEST_PT) else None
                if latest_weight:
                    backup_path = os.path.join(backup_dir, f"backup_{int(time.time())}.pt")
                    shutil.copy2(latest_weight, backup_path)
                    confirm = f"⏰ Auto-backup: Weights saved to {backup_path}"
                    logging.info(f"Auto-backup successful: {backup_path}")
                else:
                    confirm = "❌ No weight file found to backup."
                    logging.warning("No weight file found for auto-backup")
                stdscr.clear()
                stdscr.addstr(h//2, (w-len(confirm))//2, confirm, curses.A_BOLD)
                stdscr.refresh()
                time.sleep(2)
                return True
            time.sleep(0.1)
        except KeyboardInterrupt:
            logging.info("KeyboardInterrupt in overfit prompt")
            return False
        except Exception as e:
            logging.error(f"Error in overfit prompt: {e}")
            return False

def main():
    # Clear terminal
    clear_terminal()
    try:
        # Use the new curses UI for everything
        runs = find_all_training_runs()
        run_name = curses_main_menu(runs)  # This ends curses before returning
        if not run_name:
            print(center_text(f"\n{Colors.RED}No training run selected. Exiting...{Colors.RESET}"))
            return
        # Show loading spinner and get first AI reply
        ai_first_reply = loading_spinner_and_ai(run_name)
        if ai_first_reply is None:  # User cancelled
            print(center_text(f"\n{Colors.YELLOW}Operation cancelled by user. Exiting...{Colors.RESET}"))
            return
        set_paths(run_name)
        # No more blocking overfitting prompt here!
        # Clear terminal again to remove lingering y/n prompt
        clear_terminal()
        print(Colors.RESET, end='')
        # Start the aquarium/analysis UI with a fresh curses screen
        try:
            logging.info("Starting aquarium UI")
            curses.wrapper(aquarium)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            logging.info("Aquarium UI cancelled by user")
            return
        except Exception as e:
            logging.error(f"Aquarium UI error: {e}")
            print(f"\nError in aquarium UI: {e}")
            print("Please check the logs for more details.")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        logging.info("Main operation cancelled by user")
        return
    except Exception as e:
        logging.error(f"Main error: {e}")
        print(f"\nAn error occurred: {e}")
        print("Please check the logs for more details.")

if __name__ == "__main__":
    try:
        main()
    finally:
        # Ensure terminal colors are reset on exit
        print(Colors.RESET, end='') 
