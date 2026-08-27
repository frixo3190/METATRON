# METATRON
AI-powered penetration testing assistant using local LLM on linux (Parrot OS)
# 🔱 METATRON
### AI-Powered Penetration Testing Assistant

<p align="center">
  <img src="screenshots/banner.png" alt="Metatron Banner" width="800"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python"/>
  <img src="https://img.shields.io/badge/OS-Parrot%20Linux-green?style=for-the-badge&logo=linux"/>
  <img src="https://img.shields.io/badge/AI-metatron--qwen-red?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/DB-MariaDB-orange?style=for-the-badge&logo=mariadb"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge"/>
</p>

---

## 📌 What is Metatron?

**Metatron** is a CLI-based AI penetration testing assistant.

You give it a target IP or domain. It runs real recon tools (nmap, whois, whatweb, curl, dig, nikto), feeds all results to an AI model, and the AI analyzes the target, identifies vulnerabilities, suggests exploits, and recommends fixes. Everything gets saved to a MariaDB database with full scan history.

The AI backend is **configurable** from the CLI: use a **local Ollama** model (fully offline) **or** an **OpenRouter** model via API (cloud). Switch anytime from the *Settings* menu.

---

## ✨ Features

- 🖥️ **Modern TUI** — Textual full-screen interface (menus, tableaux, onglets, chat)
- 🤖 **Dual AI backend** — local `metatron-qwen` via Ollama (offline) **or** OpenRouter (cloud)
- ⚙️ **CLI/TUI settings** — switch provider, set/edit OpenRouter API key, pick model (cost shown), view remaining credits, language (fr/en)
- 🔍 **Automated Recon** — nmap, whois, whatweb, curl headers, dig DNS, nikto
- 🌐 **Web Search** — DuckDuckGo search + CVE lookup (no API key needed)
- 🗄️ **MariaDB Backend** — full scan history (vulns, fixes, exploits, summary, chat)
- 💬 **AI Chat** — discuss any vulnerability/exploit with the AI (context-aware, persisted)
- ⚔️ **Attack blocks** — the AI generates a Kali attack procedure (commands); test it (editable) from the history
- ✏️ **Edit / Delete** — modify or delete any result directly
- 🔁 **Agentic Loop** — AI can request more tool runs mid-analysis
- 🛠️ **Self-audit installer** — `install_audit.sh` checks everything and proposes fixes
- 📤 **Export Reports** — PDF / HTML

Metatron allows you to export scan results into clean, shareable report formats by selecting '2.view history'->select slno and export

📄 PDF — professional vulnerability reports
🌐 HTML — browser-viewable reports
---

## 🖥️ Screenshots

<p align="center">
  <img src="screenshots/main_menu.png" alt="Main Menu" width="700"/>
  <br><i>Main Menu</i>
</p>

<p align="center">
  <img src="screenshots/scan_running.png" alt="Scan Running" width="700"/>
  <br><i>Recon tools running on target</i>
</p>

<p align="center">
  <img src="screenshots/ai_analysis.png" alt="AI Analysis" width="700"/>
  <br><i>metatron-qwen analyzing scan results</i>
</p>

<p align="center">
  <img src="screenshots/results.png" alt="Results" width="700"/>
  <br><i>Vulnerabilities saved to database</i>
</p>
<p align="center"> <img src="screenshots/export_menu.png" alt="Export Menu" width="700"/> <br><i>Export scan results as PDF and or HTML</i> </p>
---

## 🧱 Tech Stack

| Component  | Technology                          |
|------------|-------------------------------------|
| Language   | Python 3                            |
| AI Model   | metatron-qwen (fine-tuned Qwen 3.5) |
| Base Model | huihui_ai/qwen3.5-abliterated:9b    |
| LLM Runner | Ollama **or** OpenRouter API        |
| Database   | MariaDB                             |
| OS         | Parrot OS (Debian-based)            |
| Search     | DuckDuckGo (free, no key)           |

---

## ⚙️ Installation

### 🚀 Quick start (recommended)

The `install_audit.sh` script audits your system, prints a colored ✅/❌ report, and **offers** to fix anything missing (sudo, Python, venv, dependencies, system tools, MariaDB). Nothing is installed without your confirmation.

```bash
cd METATRON
./install_audit.sh
```

Then launch:

```bash
./venv/bin/python metatron.py
```

> The script also detects Ollama as **optional** — you can skip it entirely and use OpenRouter instead (see below).

### Manual install (optional)

1. Clone the repository

   ```bash
   git clone https://github.com/sooryathejas/METATRON.git
   cd METATRON
   ```

2. Create and activate a virtual environment

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install Python dependencies

   ```bash
   pip install -r requirements.txt
   ```

4. Install system tools

   ```bash
   sudo apt install nmap whois whatweb curl dnsutils nikto
   ```

5. Set up the database (see [Database Setup](#-database-setup) below).

---

## 🤖 AI Backend Setup (choose one)

Metatron supports **two** AI backends, switchable anytime from the CLI *Settings* menu (`[3] Settings (IA)`):

| Backend   | Cost     | Requires                         |
|-----------|----------|----------------------------------|
| **Ollama**    | Free, offline | Ollama + `metatron-qwen` model |
| **OpenRouter**| Pay-as-you-go | OpenRouter API key |

### Option A — Ollama (local, offline)

### Step 1 — Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Step 2 — Download the base model

```bash
ollama pull huihui_ai/qwen3.5-abliterated:9b
```

> ⚠️ This model requires at least 8.4 GB of RAM. If your system has less, use the 4b variant:
> ```bash
> ollama pull huihui_ai/qwen3.5-abliterated:4b
> ```
> Then edit `Modelfile` and change the FROM line to the 4b model.

### Step 3 — Build the custom metatron-qwen model

The repo includes a `Modelfile` that fine-tunes the base model with pentest-specific parameters:

```bash
ollama create metatron-qwen -f Modelfile
```

This creates your local `metatron-qwen` model with:
- 16,384 token context window
- Temperature: 0.7
- Top-k: 10
- Top-p: 0.9

### Step 4 — Verify the model exists

```bash
ollama list
```

You should see `metatron-qwen` in the list.

### Option B — OpenRouter (cloud)

1. Get an API key at [openrouter.ai/keys](https://openrouter.ai/keys).
2. Launch Metatron and open the Settings menu:

   ```bash
   ./venv/bin/python metatron.py
   ```

3. In `[3] Settings (IA)`:
   - `[2]` — paste your OpenRouter API key (stored in `~/.metatron/config.json`).
   - `[3]` — pick a model from the live list; **the input/output cost is shown to the right** of each model.
   - `[1]` — switch the provider to OpenRouter.

The Settings menu also displays your **remaining credits** (fetched from `GET /api/v1/credits`).

---

## 🗄️ Database Setup

> `./install_audit.sh` can create the database, user and tables automatically (reading the credentials from `db.py`). The manual steps below are provided for reference.

### Step 1 — Make sure MariaDB is running

```bash
sudo systemctl start mariadb
sudo systemctl enable mariadb
```

### Step 2 — Create the database and user

```bash
mysql -u root
```

```sql
CREATE DATABASE metatron;
CREATE USER 'metatron'@'localhost' IDENTIFIED BY '123';
GRANT ALL PRIVILEGES ON metatron.* TO 'metatron'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Step 3 — Create the tables

```bash
mysql -u metatron -p123 metatron
```

```sql
CREATE TABLE history (
  sl_no     INT AUTO_INCREMENT PRIMARY KEY,
  target    VARCHAR(255) NOT NULL,
  scan_date DATETIME NOT NULL,
  status    VARCHAR(50) DEFAULT 'active'
);

CREATE TABLE vulnerabilities (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  sl_no       INT,
  vuln_name   TEXT,
  severity    VARCHAR(50),
  port        VARCHAR(20),
  service     VARCHAR(100),
  description TEXT,
  FOREIGN KEY (sl_no) REFERENCES history(sl_no)
);

CREATE TABLE fixes (
  id       INT AUTO_INCREMENT PRIMARY KEY,
  sl_no    INT,
  vuln_id  INT,
  fix_text TEXT,
  source   VARCHAR(50),
  FOREIGN KEY (sl_no) REFERENCES history(sl_no),
  FOREIGN KEY (vuln_id) REFERENCES vulnerabilities(id)
);

CREATE TABLE exploits_attempted (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  sl_no        INT,
  exploit_name TEXT,
  tool_used    TEXT,
  payload      LONGTEXT,
  result       TEXT,
  notes        TEXT,
  FOREIGN KEY (sl_no) REFERENCES history(sl_no)
);

CREATE TABLE summary (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  sl_no        INT,
  raw_scan     LONGTEXT,
  ai_analysis  LONGTEXT,
  risk_level   VARCHAR(50),
  generated_at DATETIME,
  FOREIGN KEY (sl_no) REFERENCES history(sl_no)
);
```

---

## 🚀 Usage

Metatron now launches a **modern Textual TUI** by default. The legacy line-by-line CLI is still available with `--legacy`.

```bash
./venv/bin/python metatron.py          # interface TUI (moderne)
./venv/bin/python metatron.py --legacy # ancienne interface
```

Metatron needs **two terminal tabs** to run **only if you use Ollama**. With OpenRouter, a single tab is enough.

### Terminal 1 (Ollama only) — Load the AI model

```bash
ollama run metatron-qwen
```

Wait until you see the `>>>` prompt. This means the model is loaded into memory and ready. You can leave this terminal running in the background.

### Terminal 2 — Launch Metatron

```bash
cd ~/METATRON
./venv/bin/python metatron.py
```

---

### Walkthrough (TUI)

**1. Main menu** — `1` Nouveau scan · `2` Historique · `3` Paramètres · `q` Quitter.

**2. `1` Nouveau scan** — entre la cible, coche les outils (nmap, whois, whatweb, curl, dig, nikto — chacun avec sa description), `Entrée` pour lancer. Recon + analyse IA en direct, puis ouverture de la session.

**3. Historique** — `2` : liste des scans (cible, date, statut, outils lancés). `Entrée` pour ouvrir une session.

**4. Session** — onglets Vulnérabilités / Exploits / Analyse. Chaque vulnérabilité est **groupée avec sa description et ses correctifs**, colorée selon la sévérité. Raccourcis :
   - `Entrée` — discuter avec l'IA (chat persisté, contexte du scan)
   - `a` — tester le bloc d'attaque (éditable avant lancement)
   - `x` — éditer / supprimer l'élément
   - `e` — exporter (PDF/HTML)
    - `r` — relancer l'analyse
    - `d` — supprimer la session

---

## 📁 Project Structure

```
METATRON/
├── metatron.py         ← lanceur (TUI par défaut, --legacy)
├── metatron_legacy.py  ← ancienne interface ligne par ligne
├── config.py           ← AI provider / API key / model / language
├── logs.py             ← hook de log (capturé par le TUI)
├── install_audit.sh    ← self-audit installer (checks + optional fixes)
├── commit_gh.sh        ← commit + push via GitHub CLI
├── db.py               ← MariaDB connection and all CRUD operations
├── tools.py            ← recon tool runners (nmap, whois, etc.)
├── llm.py              ← Ollama/OpenRouter interface + parser (VULN/DESC/FIX/ATTACK)
├── search.py           ← DuckDuckGo web search and CVE lookup
├── export.py           ← PDF / HTML report exporter
├── tui/                ← interface Textual
│   ├── app.py          ← MetatronApp
│   ├── i18n.py         ← traductions fr/en
│   ├── angel.py        ← bannière METATRON animée
│   ├── styles.tcss     ← thème
│   └── screens/        ← menu, scan, history, session, settings, chat, edit
├── Modelfile           ← custom model config for metatron-qwen
├── requirements.txt    ← Python dependencies
├── .gitignore          ← excludes venv, pycache, db files
├── LICENSE             ← MIT License
├── README.md           ← this file
└── screenshots/        ← terminal screenshots for documentation
```

---

## 🗃️ Database Schema

All 5 tables are linked by `sl_no` (session number) from the `history` table:

```
history              ← one row per scan session (sl_no is the spine)
    │
    ├── vulnerabilities   ← vulns found, linked by sl_no
    │       │
    │       └── fixes     ← fixes per vuln, linked by vuln_id + sl_no
    │
    ├── exploits_attempted ← exploits tried, linked by sl_no
    │
    └── summary           ← full AI analysis dump, linked by sl_no
```

---

## ⚠️ Disclaimer

This tool is intended for **educational purposes and authorized penetration testing only**.

- Only use Metatron on systems you own or have **explicit written permission** to test.
- Unauthorized scanning or exploitation of systems is **illegal**.
- The author is not responsible for any misuse of this tool.

---

## 👤 Author

**Soorya Thejas**
- GitHub: [@sooryathejas](https://github.com/sooryathejas)

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
