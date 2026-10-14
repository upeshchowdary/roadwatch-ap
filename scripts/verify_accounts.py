"""Verify that account keys in .env actually WORK (live API calls). Never prints secret values.

Usage: uv run --extra kaggle python scripts/verify_accounts.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
DINOV3 = "facebook/dinov3-vitl16-pretrain-sat493m"
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def kaggle_checks() -> None:
    env = {k: v for k, v in os.environ.items() if v}
    try:
        out = subprocess.run(
            [sys.executable, "-m", "kaggle", "datasets", "list", "-s", "deepglobe road", "--csv"],
            capture_output=True, text=True, timeout=120, env=env,
        )
        ok = out.returncode == 0 and "ref" in out.stdout
        refs = [ln.split(",")[0] for ln in out.stdout.splitlines()[1:] if "/" in ln.split(",")[0]]
        if ok:
            detail = f"{len(refs)} DeepGlobe datasets visible, e.g. {refs[:2]}"
        else:
            msg = (out.stderr or out.stdout or "no output").strip().splitlines()
            detail = msg[-1][:200] if msg else "no output"
        check("Kaggle API auth", ok, detail)
    except Exception as e:  # noqa: BLE001
        check("Kaggle API auth", False, repr(e)[:200])


def hf_checks() -> None:
    from huggingface_hub import HfApi
    from huggingface_hub.utils import GatedRepoError, HfHubHTTPError

    api = HfApi(token=os.environ.get("HF_TOKEN"))
    try:
        me = api.whoami()
        role = me.get("auth", {}).get("accessToken", {}).get("role", "?")
        check("Hugging Face token", True, f"user={me['name']} token_role={role}")
        orgs = [o["name"] for o in me.get("orgs", [])]
        want = os.environ.get("HF_ORG", "")
        check("Hugging Face org membership", want in orgs, f"HF_ORG={want} member_of={orgs}")
    except Exception as e:  # noqa: BLE001
        check("Hugging Face token", False, repr(e)[:200])
        return
    try:
        from huggingface_hub import hf_hub_download

        hf_hub_download(DINOV3, "config.json", token=os.environ.get("HF_TOKEN"),
                        cache_dir=str(ROOT / ".cache" / "hf"))
        check("DINOv3 sat licence access", True, "config.json downloaded")
    except GatedRepoError:
        check("DINOv3 sat licence access", False, "gated: request pending or not submitted")
    except HfHubHTTPError as e:
        check("DINOv3 sat licence access", False, str(e)[:200])


def main() -> int:
    kaggle_checks()
    hf_checks()
    print()
    for name, ok, detail in results:
        print(f"  {'OK  ' if ok else 'FAIL'}  {name:<30} {detail}")
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
