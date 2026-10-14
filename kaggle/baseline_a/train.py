"""RoadWatch AP — Baseline A: U-Net (ResNet34) road segmentation on DeepGlobe Roads.

Runs on Kaggle (T4/P100). Self-contained: the push script injects RUN_CONFIG below.
Rules (PROJECT_PROMPT.md 7.5): AMP, checkpoint every epoch, resume, early stopping,
fixed seeds, config hash logged, timing run first.

Outputs in /kaggle/working:
  ckpt_last.pt, ckpt_best.pt, train_log.csv, metrics.json, timing.json,
  per_image_<split>.csv (for bootstrap CIs), model_best.onnx (final runs only)
"""

# --- RUN_CONFIG (injected by scripts/kaggle_push.py; do not edit by hand) ---
RUN_CONFIG = {
    "run_id": "local-debug",
    "arch": "Unet",
    "encoder": "resnet34",
    "encoder_weights": "imagenet",
    "epochs": 1,
    "timing_only": True,
    "seed": 0,
    "crop": 512,
    "batch_size": 16,
    "lr": 3e-4,
    "weight_decay": 1e-4,
    "subset_ratio": 1.0,
    "patience": 5,
    "num_workers": 4,
    "max_train_batches": 0,
    "eval_test": False,
    "export_onnx": False,
    "resume_dir": "",
    "crops_per_image": 4,
    "val_every": 2,
    "max_hours": 3.0,
    "config_hash": "none",
}
# --- END RUN_CONFIG ---

import csv
import glob
import hashlib
import json
import os
import random
import subprocess
import sys
import time

import numpy as np

OUT = "/kaggle/working" if os.path.isdir("/kaggle/working") else os.path.abspath("./out")
os.makedirs(OUT, exist_ok=True)
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:8.1f}s] {msg}", flush=True)


def pip_install(pkg: str) -> None:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", pkg], check=False)


try:
    import segmentation_models_pytorch as smp
except ImportError:
    pip_install("segmentation-models-pytorch==0.3.4")
    import segmentation_models_pytorch as smp

import cv2  # noqa: E402
import torch  # noqa: E402
import torch.nn as nn  # noqa: E402
from torch.utils.data import DataLoader, Dataset  # noqa: E402

C = RUN_CONFIG


# ---------------------------------------------------------------- data
def find_root() -> str:
    if os.environ.get("ROADWATCH_DATA_ROOT"):  # local smoke tests
        return os.environ["ROADWATCH_DATA_ROOT"]
    hits = glob.glob("/kaggle/input/**/metadata.csv", recursive=True)
    hits = [h for h in hits if "deepglobe" in h.lower()] or hits
    if not hits:
        raise FileNotFoundError("DeepGlobe metadata.csv not found under /kaggle/input")
    return os.path.dirname(hits[0])


def fixed_split(image_id: str) -> str:
    """Frozen DeepGlobe split by hash of image id: 80% train / 10% val / 10% test (ADR-012)."""
    u = int(hashlib.sha256(f"deepglobe:{image_id}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "test" if u < 0.10 else ("val" if u < 0.20 else "train")


def load_items(root: str) -> dict[str, list[tuple[str, str, str]]]:
    items: dict[str, list] = {"train": [], "val": [], "test": []}
    with open(os.path.join(root, "metadata.csv"), newline="") as f:
        for r in csv.DictReader(f):
            if r.get("split") != "train" or not r.get("mask_path"):
                continue  # only the official train split has masks
            iid = str(r["image_id"])
            items[fixed_split(iid)].append(
                (iid, os.path.join(root, r["sat_image_path"]), os.path.join(root, r["mask_path"]))
            )
    for k in items:
        items[k].sort()
    return items


class RoadDS(Dataset):
    MEAN = np.array([0.485, 0.456, 0.406], np.float32)
    STD = np.array([0.229, 0.224, 0.225], np.float32)

    def __init__(self, items, train: bool, crop: int, crops_per_image: int = 1):
        self.items, self.train, self.crop, self.k = items, train, crop, crops_per_image

    def __len__(self):
        return len(self.items)

    def _norm(self, img, m):
        x = (img.astype(np.float32) / 255.0 - self.MEAN) / self.STD
        return (torch.from_numpy(np.ascontiguousarray(x.transpose(2, 0, 1))),
                torch.from_numpy(np.ascontiguousarray(m))[None])

    def __getitem__(self, i):
        iid, ip, mp = self.items[i]
        img = cv2.cvtColor(cv2.imread(ip, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
        m = (cv2.imread(mp, cv2.IMREAD_GRAYSCALE) > 127).astype(np.float32)
        if not self.train:
            x, y = self._norm(img, m)
            return x, y, iid
        # several random crops per decoded image: JPEG decoding was the bottleneck (timing run)
        xs, ys = [], []
        h, w = m.shape
        for _ in range(self.k):
            r, c = random.randint(0, h - self.crop), random.randint(0, w - self.crop)
            ci, cm = img[r:r + self.crop, c:c + self.crop], m[r:r + self.crop, c:c + self.crop]
            if random.random() < 0.5:
                ci, cm = ci[:, ::-1], cm[:, ::-1]
            if random.random() < 0.5:
                ci, cm = ci[::-1], cm[::-1]
            rot = random.randint(0, 3)
            x, y = self._norm(np.rot90(ci, rot), np.rot90(cm, rot))
            xs.append(x)
            ys.append(y)
        return torch.stack(xs), torch.stack(ys), iid


# ---------------------------------------------------------------- model / loss / metrics
def build_model():
    arch = getattr(smp, C["arch"])
    return arch(encoder_name=C["encoder"], encoder_weights=C["encoder_weights"] or None,
                in_channels=3, classes=1)


class BCEDice(nn.Module):
    def __init__(self):
        super().__init__()
        self.bce = nn.BCEWithLogitsLoss()

    def forward(self, logits, y):
        p = torch.sigmoid(logits)
        inter = (p * y).sum((1, 2, 3))
        dice = 1 - (2 * inter + 1) / (p.sum((1, 2, 3)) + y.sum((1, 2, 3)) + 1)
        return self.bce(logits, y) + dice.mean()


@torch.no_grad()
def evaluate(model, loader, device, split: str, write_per_image: bool):
    """Global pixel IoU/F1 + per-image counts (for bootstrap CIs in the KPI report)."""
    model.eval()
    tp = fp = fn = 0
    rows = []
    for x, y, ids in loader:
        x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
        with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
            pred = (model(x) > 0).float()
        t = (pred * y).sum((1, 2, 3))
        f_p = (pred * (1 - y)).sum((1, 2, 3))
        f_n = ((1 - pred) * y).sum((1, 2, 3))
        for i, iid in enumerate(ids):
            rows.append((iid, int(t[i]), int(f_p[i]), int(f_n[i])))
        tp, fp, fn = tp + int(t.sum()), fp + int(f_p.sum()), fn + int(f_n.sum())
    iou = tp / max(tp + fp + fn, 1)
    prec, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
    if write_per_image:
        with open(os.path.join(OUT, f"per_image_{split}.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["image_id", "tp", "fp", "fn"])
            w.writerows(rows)
    model.train()
    return {"iou": iou, "f1": f1, "precision": prec, "recall": rec, "n_images": len(rows)}


# ---------------------------------------------------------------- main
def main():
    random.seed(C["seed"])
    np.random.seed(C["seed"])
    torch.manual_seed(C["seed"])
    torch.backends.cudnn.benchmark = True
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    n_gpu = torch.cuda.device_count()
    gpus = [torch.cuda.get_device_name(i) for i in range(n_gpu)]
    log(f"config_hash={C['config_hash']} run_id={C['run_id']} gpus={gpus} torch={torch.__version__}")

    root = find_root()
    items = load_items(root)
    if C["subset_ratio"] < 1.0:
        rng = random.Random(1564)
        items["train"] = sorted(rng.sample(items["train"], int(len(items["train"]) * C["subset_ratio"])))
    log(f"data root={root} sizes={ {k: len(v) for k, v in items.items()} }")

    bs = C["batch_size"]  # in crops
    nw = C["num_workers"]
    k = C["crops_per_image"]
    tr = DataLoader(RoadDS(items["train"], True, C["crop"], k), batch_size=max(bs // k, 1),
                    shuffle=True, num_workers=nw, pin_memory=True, drop_last=True,
                    persistent_workers=nw > 0)
    va = DataLoader(RoadDS(items["val"], False, C["crop"]), batch_size=4, num_workers=nw,
                    pin_memory=True)

    model = build_model().to(device)
    if n_gpu > 1:
        model = nn.DataParallel(model)
    opt = torch.optim.AdamW(model.parameters(), lr=C["lr"], weight_decay=C["weight_decay"])
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(C["epochs"], 1))
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    loss_fn = BCEDice()

    start_epoch, best, bad = 0, -1.0, 0
    resume = ""
    for cand in (os.path.join(OUT, "ckpt_last.pt"),
                 *(glob.glob(os.path.join(C["resume_dir"], "**", "ckpt_last.pt"), recursive=True)
                   if C["resume_dir"] else [])):
        if os.path.exists(cand):
            resume = cand
            break
    if resume:
        ck = torch.load(resume, map_location=device, weights_only=False)
        (model.module if n_gpu > 1 else model).load_state_dict(ck["model"])
        opt.load_state_dict(ck["opt"])
        sched.load_state_dict(ck["sched"])
        scaler.load_state_dict(ck["scaler"])
        start_epoch, best, bad = ck["epoch"] + 1, ck["best"], ck["bad"]
        log(f"resumed from {resume} at epoch {start_epoch}, best={best:.4f}")

    log_path = os.path.join(OUT, "train_log.csv")
    if not os.path.exists(log_path):
        with open(log_path, "w", newline="") as f:
            csv.writer(f).writerow(["epoch", "train_loss", "val_iou", "val_f1", "lr",
                                    "epoch_sec", "train_sec", "val_sec", "imgs_per_sec"])

    epoch_times = []
    stop_reason = "completed"
    budget_sec = C["max_hours"] * 3600
    for ep in range(start_epoch, C["epochs"]):
        # time guard: Kaggle free GPU quota is 6 h/week/account — stop cleanly, resumable
        if epoch_times and (time.time() - T0) + 1.3 * max(epoch_times) > budget_sec:
            stop_reason = f"time_budget_{C['max_hours']}h"
            log(f"stopping before epoch {ep}: time budget reached (resume from ckpt_last.pt)")
            break
        t_ep = time.time()
        model.train()
        tot, n = 0.0, 0
        for bi, (x, y, _) in enumerate(tr):
            if C["max_train_batches"] and bi >= C["max_train_batches"]:
                break
            x, y = x.flatten(0, 1), y.flatten(0, 1)  # (imgs, k, ...) -> (imgs*k, ...)
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
                loss = loss_fn(model(x), y)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            tot, n = tot + loss.item() * x.size(0), n + x.size(0)
            if bi % 50 == 0:
                log(f"ep{ep} batch {bi}/{len(tr)} loss={loss.item():.4f}")
        sched.step()
        t_train = time.time() - t_ep
        t_v = time.time()
        last = ep == C["epochs"] - 1
        if (ep + 1) % C["val_every"] == 0 or last or ep == start_epoch:
            vm = evaluate(model, va, device, "val", write_per_image=False)
        else:
            vm = {"iou": float("nan"), "f1": float("nan")}
        t_val = time.time() - t_v
        ep_sec = time.time() - t_ep
        epoch_times.append(ep_sec)
        log(f"epoch {ep}: loss={tot / max(n, 1):.4f} val_iou={vm['iou']:.4f} val_f1={vm['f1']:.4f} "
            f"train={t_train:.0f}s val={t_val:.0f}s")
        with open(log_path, "a", newline="") as f:
            csv.writer(f).writerow([ep, tot / max(n, 1), vm["iou"], vm["f1"], sched.get_last_lr()[0],
                                    round(ep_sec, 1), round(t_train, 1), round(t_val, 1),
                                    round(n / max(t_train, 1e-9), 2)])
        validated = not np.isnan(vm["iou"])
        improved = validated and vm["iou"] > best
        if validated:
            best, bad = (vm["iou"], 0) if improved else (best, bad + 1)
        state = {"model": (model.module if n_gpu > 1 else model).state_dict(), "opt": opt.state_dict(),
                 "sched": sched.state_dict(), "scaler": scaler.state_dict(), "epoch": ep,
                 "best": best, "bad": bad, "config": C}
        torch.save(state, os.path.join(OUT, "ckpt_last.pt"))
        if improved:
            torch.save(state, os.path.join(OUT, "ckpt_best.pt"))
        if bad >= C["patience"]:  # patience counts validations, not epochs
            stop_reason = f"early_stop_epoch_{ep}"
            log(f"early stop at epoch {ep}")
            break

    timing = {
        "run_id": C["run_id"], "config_hash": C["config_hash"], "gpus": gpus,
        "epochs_run": len(epoch_times), "sec_per_epoch": epoch_times,
        "mean_sec_per_epoch": float(np.mean(epoch_times)) if epoch_times else None,
        "train_images": len(items["train"]), "batch_size": bs, "crop": C["crop"],
        "crops_per_image": k, "wall_sec": time.time() - T0, "stop_reason": stop_reason,
    }
    if epoch_times:
        per_ep_h = timing["mean_sec_per_epoch"] / 3600
        # Kaggle quota is billed per session hour (T4x2 = same rate as one GPU), so quota = wall time
        timing["est_quota_hours"] = {f"{e}_epochs": round(per_ep_h * e, 2) for e in (20, 40, 60)}
    with open(os.path.join(OUT, "timing.json"), "w") as f:
        json.dump(timing, f, indent=2)
    log(f"timing: {json.dumps(timing)}")

    metrics = {"run_id": C["run_id"], "config_hash": C["config_hash"], "best_val_iou": best,
               "stop_reason": stop_reason}
    if C["eval_test"] and os.path.exists(os.path.join(OUT, "ckpt_best.pt")):
        ck = torch.load(os.path.join(OUT, "ckpt_best.pt"), map_location=device, weights_only=False)
        (model.module if n_gpu > 1 else model).load_state_dict(ck["model"])
        te = DataLoader(RoadDS(items["test"], False, C["crop"]), batch_size=4, num_workers=nw)
        metrics["val"] = evaluate(model, va, device, "val", write_per_image=True)
        metrics["test"] = evaluate(model, te, device, "test", write_per_image=True)
        log(f"TEST: {metrics['test']}")
    with open(os.path.join(OUT, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    if C["export_onnx"] and os.path.exists(os.path.join(OUT, "ckpt_best.pt")):
        try:
            m = build_model()
            m.load_state_dict(torch.load(os.path.join(OUT, "ckpt_best.pt"),
                                         map_location="cpu", weights_only=False)["model"])
            m.eval()
            kw = dict(input_names=["image"], output_names=["logits"], opset_version=17,
                      dynamic_axes={"image": {0: "b", 2: "h", 3: "w"},
                                    "logits": {0: "b", 2: "h", 3: "w"}})
            dst = os.path.join(OUT, "model_best.onnx")
            try:  # classic TorchScript exporter; torch>=2.9 defaults to dynamo (needs onnxscript)
                torch.onnx.export(m, torch.zeros(1, 3, 512, 512), dst, dynamo=False, **kw)
            except TypeError:  # older torch without the `dynamo` kwarg
                torch.onnx.export(m, torch.zeros(1, 3, 512, 512), dst, **kw)
            log(f"exported model_best.onnx ({os.path.getsize(dst) / 1e6:.0f} MB)")
        except Exception as e:  # noqa: BLE001
            log(f"ONNX export failed: {e!r}")
    log("done")


if __name__ == "__main__":
    main()
