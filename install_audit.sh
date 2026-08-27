#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  METATRON — install_audit.sh
#  Audit de l'installation + corrections optionnelles.
#  Vérifie : sudo, python, venv, dépendances, outils système,
#            MariaDB (base + tables), Ollama (optionnel).
#  Usage  : ./install_audit.sh
# ═══════════════════════════════════════════════════════════════════
set -uo pipefail

# ── Couleurs ───────────────────────────────────────────────────────
if [[ -t 1 ]]; then
    C_GREEN=$'\033[32m'; C_RED=$'\033[31m'; C_YELLOW=$'\033[33m'
    C_CYAN=$'\033[36m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'; C_RESET=$'\033[0m'
else
    C_GREEN=''; C_RED=''; C_YELLOW=''; C_CYAN=''; C_BOLD=''; C_DIM=''; C_RESET=''
fi

# ── Helpers d'affichage ────────────────────────────────────────────
ok()      { printf "${C_GREEN}  [✓]${C_RESET} %s\n" "$1"; }
fail()    { printf "${C_RED}  [✗]${C_RESET} %s\n" "$1"; }
warn()    { printf "${C_YELLOW}  [!]${C_RESET} %s\n" "$1"; }
info()    { printf "${C_CYAN}  › %s${C_RESET}\n" "$1"; }
section() { printf "\n${C_BOLD}${C_CYAN}═══ %s ═══${C_RESET}\n" "$1"; }

# Compteurs globaux
OK_COUNT=0
FAIL_COUNT=0

# Drapeaux de correction (remplis pendant les vérifs)
NEED_VENV=""
NEED_PIP=""
MISSING_TOOLS=""
NEED_DB_START=""
NEED_DB_PROVISION=""
NEED_GH=""

# ── Outils / chemins ───────────────────────────────────────────────
PY=""
SUDO=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ask_fix() {
    # $1 = libellé de la correction proposée
    local ans
    read -r -p "  ${C_YELLOW}→${C_RESET} $1 ? [y/N] " ans
    [[ "$ans" =~ ^[Yy]$ ]]
}

# ═══════════════════════════════════════════════════════════════════
#  1. PRIVILÈGES (sudo)
# ═══════════════════════════════════════════════════════════════════
section "Privilèges"
if [[ $EUID -eq 0 ]]; then
    ok "Exécution en root (aucun sudo nécessaire)"
    SUDO=""
elif command -v sudo >/dev/null 2>&1; then
    ok "Commande sudo disponible"
    SUDO="sudo"
else
    fail "Ni root ni sudo — relance avec : sudo $0"
    SUDO=""
fi

# ═══════════════════════════════════════════════════════════════════
#  2. PYTHON + VENV
# ═══════════════════════════════════════════════════════════════════
section "Python & environnement virtuel"

if command -v python3 >/dev/null 2>&1; then
    PY="$(command -v python3)"
    ok "python3 trouvé ($("$PY" --version 2>&1))"
else
    fail "python3 introuvable"
fi

if [[ -n "$PY" ]] && "$PY" -c "import venv" >/dev/null 2>&1; then
    ok "Module python « venv » disponible"
else
    fail "Module python « venv » manquant (installe python3-venv)"
fi

if [[ -x "$SCRIPT_DIR/venv/bin/python" ]]; then
    ok "Environnement virtuel présent (venv/)"
else
    fail "Environnement virtuel absent (venv/)"
    NEED_VENV="1"
fi

# ═══════════════════════════════════════════════════════════════════
#  3. DÉPENDANCES PYTHON
# ═══════════════════════════════════════════════════════════════════
section "Dépendances Python"

if [[ -x "$SCRIPT_DIR/venv/bin/python" ]]; then
    if "$SCRIPT_DIR/venv/bin/python" -c \
        "import mysql.connector, requests, bs4, ddgs, reportlab, PIL" >/dev/null 2>&1; then
        ok "Toutes les dépendances Python sont installées"
    else
        fail "Dépendances Python manquantes"
        NEED_PIP="1"
    fi
else
    warn "venv absent — dépendances à installer après création (étape 2)"
fi

# ═══════════════════════════════════════════════════════════════════
#  4. OUTILS SYSTÈME
# ═══════════════════════════════════════════════════════════════════
section "Outils système (recon)"

for tool in nmap whois whatweb curl dig nikto; do
    if command -v "$tool" >/dev/null 2>&1; then
        ok "$tool"
    else
        fail "$tool"
        MISSING_TOOLS+=" $tool"
    fi
done

# ═══════════════════════════════════════════════════════════════════
#  4b. GITHUB CLI (gh) — pour commit_gh.sh
# ═══════════════════════════════════════════════════════════════════
section "GitHub CLI (gh)"
if command -v gh >/dev/null 2>&1; then
    ok "gh installé ($(gh --version 2>/dev/null | head -1))"
else
    fail "gh non installé"
    NEED_GH="1"
fi

# ═══════════════════════════════════════════════════════════════════
#  5. MARIADB
# ═══════════════════════════════════════════════════════════════════
section "MariaDB (base de données)"

DB_HOST="localhost"; DB_USER="metatron"; DB_PASS="123"; DB_NAME="metatron"
if [[ -f "$SCRIPT_DIR/db.py" ]]; then
    DB_HOST="$(grep -oP 'host="\K[^"]+' "$SCRIPT_DIR/db.py" | head -1 || true)"
    DB_USER="$(grep -oP 'user="\K[^"]+' "$SCRIPT_DIR/db.py" | head -1 || true)"
    DB_PASS="$(grep -oP 'password="\K[^"]+' "$SCRIPT_DIR/db.py" | head -1 || true)"
    DB_NAME="$(grep -oP 'database="\K[^"]+' "$SCRIPT_DIR/db.py" | head -1 || true)"
    : "${DB_HOST:=localhost}"; : "${DB_USER:=metatron}"; : "${DB_PASS:=123}"; : "${DB_NAME:=metatron}"
fi

MYSQL_BIN=""
if command -v mariadb >/dev/null 2>&1; then MYSQL_BIN="mariadb"; ok "Client MariaDB présent"
elif command -v mysql >/dev/null 2>&1; then MYSQL_BIN="mysql"; ok "Client MySQL présent"
else fail "Client MariaDB/MySQL introuvable"; fi

if systemctl is-active --quiet mariadb 2>/dev/null || systemctl is-active --quiet mysql 2>/dev/null; then
    ok "Service MariaDB actif"
elif pgrep -x mariadbd >/dev/null 2>&1 || pgrep -x mysqld >/dev/null 2>&1; then
    ok "Service MariaDB actif (processus détecté)"
else
    fail "Service MariaDB arrêté"
    NEED_DB_START="1"
fi

if [[ -n "$MYSQL_BIN" ]]; then
    if "$MYSQL_BIN" -u"$DB_USER" -p"$DB_PASS" -h"$DB_HOST" -e "SELECT 1" >/dev/null 2>&1; then
        ok "Connexion MariaDB OK (utilisateur « $DB_USER »)"
    else
        fail "Connexion MariaDB impossible (user « $DB_USER ») — base/user à créer"
        NEED_DB_PROVISION="1"
    fi

    if [[ "$NEED_DB_PROVISION" != "1" ]]; then
        if "$MYSQL_BIN" -u"$DB_USER" -p"$DB_PASS" -h"$DB_HOST" "$DB_NAME" -e "SHOW TABLES" >/dev/null 2>&1; then
            N_TABLES=$("$MYSQL_BIN" -u"$DB_USER" -p"$DB_PASS" -h"$DB_HOST" "$DB_NAME" -N -e "SHOW TABLES" 2>/dev/null | wc -l)
            if [[ "$N_TABLES" -ge 5 ]]; then
                ok "Base « $DB_NAME » présente avec $N_TABLES tables"
            else
                fail "Base « $DB_NAME » incomplète ($N_TABLES/5 tables)"
                NEED_DB_PROVISION="1"
            fi
        else
            fail "Base « $DB_NAME » inexistante"
            NEED_DB_PROVISION="1"
        fi
    fi
fi

# ═══════════════════════════════════════════════════════════════════
#  6. OLLAMA (optionnel — OpenRouter peut le remplacer)
# ═══════════════════════════════════════════════════════════════════
section "Ollama (optionnel — alternative : OpenRouter)"

if command -v ollama >/dev/null 2>&1; then
    ok "Ollama installé"
    if curl -s --max-time 3 http://localhost:11434/api/version >/dev/null 2>&1; then
        ok "Serveur Ollama joignable"
    else
        warn "Serveur Ollama non démarré (lance « ollama serve »)"
    fi
    if ollama list 2>/dev/null | grep -q "metatron-qwen"; then
        ok "Modèle « metatron-qwen » présent"
    else
        warn "Modèle « metatron-qwen » absent (voir README — ou utilise OpenRouter)"
    fi
else
    warn "Ollama non installé (facultatif si tu utilises OpenRouter)"
fi

# ═══════════════════════════════════════════════════════════════════
#  RAPPORT + CORRECTIONS
# ═══════════════════════════════════════════════════════════════════
# (recalcule les compteurs à partir des drapeaux — simple et fiable)
FAIL_COUNT=0
[[ -n "$NEED_VENV" ]] && FAIL_COUNT=$((FAIL_COUNT+1))
[[ -n "$NEED_PIP" ]] && FAIL_COUNT=$((FAIL_COUNT+1))
[[ -n "$MISSING_TOOLS" ]] && FAIL_COUNT=$((FAIL_COUNT+1))
[[ -n "$NEED_DB_START" ]] && FAIL_COUNT=$((FAIL_COUNT+1))
[[ -n "$NEED_DB_PROVISION" ]] && FAIL_COUNT=$((FAIL_COUNT+1))
[[ -n "$NEED_GH" ]] && FAIL_COUNT=$((FAIL_COUNT+1))

section "Résultat"
if [[ "$FAIL_COUNT" -eq 0 ]]; then
    printf "${C_GREEN}  Tout est prêt ✓${C_RESET}\n"
    info "Lance Metatron : ./venv/bin/python metatron.py"
    exit 0
fi

printf "${C_RED}  %d catégorie(s) à corriger.${C_RESET}\n" "$FAIL_COUNT"

# ── Propositions de correction (toutes optionnelles) ──────────────
echo
if [[ -n "$NEED_VENV" ]] && ask_fix "Créer l'environnement virtuel (venv)"; then
    if [[ -z "$PY" ]]; then
        warn "python3 introuvable — impossible de créer le venv"
    else
        "$PY" -m venv "$SCRIPT_DIR/venv" && ok "venv créé"
        NEED_PIP="1"
    fi
fi

if [[ -n "$NEED_PIP" ]] && ask_fix "Installer les dépendances Python (requirements.txt)"; then
    if [[ -x "$SCRIPT_DIR/venv/bin/pip" ]]; then
        "$SCRIPT_DIR/venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" && ok "Dépendances installées"
    else
        warn "venv/pip absent — crée d'abord le venv"
    fi
fi

if [[ -n "$MISSING_TOOLS" ]] && ask_fix "Installer les outils manquants :${MISSING_TOOLS}"; then
    if [[ -n "$SUDO" ]]; then
        "$SUDO" apt-get update -qq && "$SUDO" apt-get install -y $MISSING_TOOLS && ok "Outils installés"
    else
        warn "Pas de sudo — exécute manuellement : sudo apt install$MISSING_TOOLS"
    fi
fi

if [[ -n "$NEED_DB_START" ]] && ask_fix "Démarrer le service MariaDB"; then
    if [[ -n "$SUDO" ]]; then
        "$SUDO" systemctl start mariadb 2>/dev/null || "$SUDO" systemctl start mysql 2>/dev/null
        ok "Service MariaDB démarré"
    else
        warn "Pas de sudo — exécute : sudo systemctl start mariadb"
    fi
fi

if [[ -n "$NEED_DB_PROVISION" ]] && ask_fix "Créer la base « $DB_NAME » + utilisateur + tables"; then
    if [[ -n "$SUDO" ]] || [[ -n "$MYSQL_BIN" ]]; then
        "$SUDO" "$MYSQL_BIN" <<SQL
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\`;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;

USE \`$DB_NAME\`;

CREATE TABLE IF NOT EXISTS history (
  sl_no     INT AUTO_INCREMENT PRIMARY KEY,
  target    VARCHAR(255) NOT NULL,
  scan_date DATETIME NOT NULL,
  status    VARCHAR(50) DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS vulnerabilities (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  sl_no       INT,
  vuln_name   TEXT,
  severity    VARCHAR(50),
  port        VARCHAR(20),
  service     VARCHAR(100),
  description TEXT,
  attack      TEXT,
  FOREIGN KEY (sl_no) REFERENCES history(sl_no)
);

CREATE TABLE IF NOT EXISTS fixes (
  id       INT AUTO_INCREMENT PRIMARY KEY,
  sl_no    INT,
  vuln_id  INT,
  fix_text TEXT,
  source   VARCHAR(50),
  FOREIGN KEY (sl_no) REFERENCES history(sl_no),
  FOREIGN KEY (vuln_id) REFERENCES vulnerabilities(id)
);

CREATE TABLE IF NOT EXISTS exploits_attempted (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  sl_no        INT,
  exploit_name TEXT,
  tool_used    TEXT,
  payload      LONGTEXT,
  result       TEXT,
  notes        TEXT,
  FOREIGN KEY (sl_no) REFERENCES history(sl_no)
);

CREATE TABLE IF NOT EXISTS summary (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  sl_no        INT,
  raw_scan     LONGTEXT,
  ai_analysis  LONGTEXT,
  risk_level   VARCHAR(50),
  generated_at DATETIME,
  FOREIGN KEY (sl_no) REFERENCES history(sl_no)
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  chat_key   VARCHAR(255),
  role       VARCHAR(20),
  content    TEXT,
  created_at DATETIME
);
SQL
        ok "Base, utilisateur et tables créés (ou déjà présents)"
    else
        warn "Pas de client SQL ni sudo — configure la base manuellement (voir README)"
    fi
fi

if [[ -n "$NEED_GH" ]] && ask_fix "Installer GitHub CLI (gh)"; then
    if [[ -n "$SUDO" ]]; then
        "$SUDO" mkdir -p -m 755 /etc/apt/keyrings
        curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
            | "$SUDO" tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
        "$SUDO" chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
            | "$SUDO" tee /etc/apt/sources.list.d/github-cli.list >/dev/null
        "$SUDO" apt-get update -qq
        "$SUDO" apt-get install -y gh && ok "gh installé"
    else
        warn "Pas de sudo — installe gh manuellement (voir README)"
    fi
fi

echo
info "Relance ce script après correction, puis : ./venv/bin/python metatron.py"
