# Setup accounts — step by step

Secrets go ONLY into `E:\cap-22\.env` (git-ignored). Never paste them in chat.
Open it with: `notepad E:\cap-22\.env`. Check with: `uv run python scripts/check_env.py`.
Website button names change sometimes — if a label differs slightly, pick the closest match.

---

## 1. Kaggle (CP1 — needed for all training)   ~10 min

1. Open https://www.kaggle.com → click **Register** (top-right) → **Register with Google** (or email).
2. Phone verification (needed for GPU + internet in notebooks):
   open https://www.kaggle.com/settings → section **Phone Verification** → enter your mobile → type the SMS code.
3. API token, same page https://www.kaggle.com/settings → scroll to section **API**:
   - If you see **Generate New Token** / **Create New Token**: click it, copy the token shown.
     In `.env` paste it after `KAGGLE_API_TOKEN=` and also set `KAGGLE_USERNAME=<your kaggle username>`.
   - If you only see **Create Legacy API Key**: it downloads `kaggle.json`. Open it in Notepad; copy
     `username` → `KAGGLE_USERNAME=`, `key` → `KAGGLE_KEY=`. Then delete the downloaded file.
4. Success: `uv run python scripts/check_env.py` shows `=> KAGGLE: OK`.

If stuck: "Phone verification failed" → use a different number format (+91XXXXXXXXXX, no spaces); one number = one Kaggle account only.

## 2. Hugging Face (CP1 — checkpoints, DINOv3)   ~10 min

1. Open https://huggingface.co/join → sign up → confirm the email link.
2. Token: open https://huggingface.co/settings/tokens → **Create new token** → Token type **Write** →
   name `roadwatch` → **Create token** → copy it → paste after `HF_TOKEN=` in `.env`.
3. Shared org: open https://huggingface.co/organizations/new → Organization name e.g. `roadwatch-ap`
   (if taken, add a suffix) → type **Community / Academic** if asked → **Create**.
   Put the name after `HF_ORG=` in `.env`. Later: org page → **Settings → Members** → invite teammates.
4. DINOv3 licence (approval can take hours): open
   https://huggingface.co/facebook/dinov3-vitl16-pretrain-sat493m → fill the access form on the model
   page (name, affiliation "KL University", purpose "academic capstone research") → accept → **Submit**.
   Success: the page later shows "You have been granted access".

If stuck: no form visible → make sure you are logged in (top-right avatar).

## 3. GitHub public repo   ~5 min

1. Open https://github.com/new (log in / sign up first).
2. Repository name: `roadwatch-ap` · select **Public** · leave **Add a README**, **.gitignore**, **license** all **unticked**.
3. Click **Create repository**. Copy the HTTPS URL shown (like `https://github.com/<you>/roadwatch-ap.git`).
4. On first push a browser window "Git Credential Manager" opens → **Sign in with your browser** → **Authorize**.

## 4. Teammates A, B, C, D (do now, used from Day 3)

Each person, on their **own** phone number and account: do Section 1 steps 1–2 only (Kaggle register +
phone verification) and send you their Kaggle username. They do NOT need API tokens.
