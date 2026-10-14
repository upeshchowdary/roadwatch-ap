# Teammate Run Card — baseline_a_full_s1_726c84a365a3

| | |
|---|---|
| Person | **A** (Spatial evidence & provenance lead) |
| Model / run | baseline_a / full_s1 (seed 1) |
| Config hash | `726c84a365a3` |
| GPU time | about **3.0 h** of your weekly 6 h Kaggle GPU quota (hard stop built in) |
| Your time | ~10 min to start + ~5 min to download at the end. Laptop can be OFF while it runs. |

## A. Start the run (~10 min)

1. Download the notebook file: open
   https://github.com/upeshchowdary/roadwatch-ap/blob/main/kaggle/cards/baseline_a_full_s1.ipynb
   → click the **Download raw file** button (down-arrow icon, top-right of the file view).
2. Open https://www.kaggle.com/code → click **+ New Notebook** (top-left).
3. In the notebook editor: menu **File → Import Notebook** → **Browse Files** → pick
   `baseline_a_full_s1.ipynb` → **Import**. (If asked "replace current notebook?" → yes.)
4. Right sidebar → **Input** section → **+ Add Input** → search `deepglobe road extraction`
   → pick **DeepGlobe Road Extraction Dataset** by *balraj98* → click the **+** → close.
5. Right sidebar → **Session options**:
   - **Accelerator** → **GPU T4 x2**
   - **Internet** → **On** (needs a phone-verified account)
6. Rename the notebook (top-left title) to: `roadwatch-baseline-a-full-s1`
7. Top-right **Save Version** → choose **Save & Run All (Commit)** → **Save**.
8. You should see "Version 1 · Running". You can close the browser and switch off the laptop.

## B. When it finishes (~3.0 h later)

1. Open https://www.kaggle.com/code → **Your Work** → `roadwatch-baseline-a-full-s1` → status **Succeeded**.
2. Click the **Output** tab → **Download All** (a zip).
3. Send the zip (Google Drive link) to the project lead, or upload it: open
   https://huggingface.co/organizations/roadwatch-ap → **New → Dataset** is NOT needed — just send the
   Drive link; the lead uploads checkpoints to Hugging Face.
4. Reply in the group: `done baseline_a_full_s1_726c84a365a3` + the **val IoU** printed at the end of the log
   (Logs tab → last lines contain `TEST:` and `best_val_iou`).

## If stuck
- "GPU quota exceeded" → you have used your 6 h this week; tell the lead (quota resets Saturday).
- "Internet must be verified" → Kaggle **Settings → Phone Verification** first.
- Red error in the log → screenshot the last 20 lines of the **Logs** tab and send it.
