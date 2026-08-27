#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  METATRON — commit_gh.sh
#  Vérifie que « gh » (GitHub CLI) est installé (sinon l'installe),
#  vérifie l'authentification (sinon login par token),
#  puis commit + push le projet.
#  Usage  : ./commit_gh.sh
# ═══════════════════════════════════════════════════════════════════
set -uo pipefail

# ── Couleurs ───────────────────────────────────────────────────────
if [[ -t 1 ]]; then
    C_GREEN=$'\033[32m'; C_RED=$'\033[31m'; C_YELLOW=$'\033[33m'
    C_CYAN=$'\033[36m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'; C_RESET=$'\033[0m'
else
    C_GREEN=''; C_RED=''; C_YELLOW=''; C_CYAN=''; C_BOLD=''; C_DIM=''; C_RESET=''
fi

ok()      { printf "${C_GREEN}  [✓]${C_RESET} %s\n" "$1"; }
fail()    { printf "${C_RED}  [✗]${C_RESET} %s\n" "$1"; }
warn()    { printf "${C_YELLOW}  [!]${C_RESET} %s\n" "$1"; }
info()    { printf "${C_CYAN}  › %s${C_RESET}\n" "$1"; }
section() { printf "\n${C_BOLD}${C_CYAN}═══ %s ═══${C_RESET}\n" "$1"; }

ask_fix() {
    local ans
    read -r -p "  ${C_YELLOW}→${C_RESET} $1 ? [y/N] " ans
    [[ "$ans" =~ ^[Yy]$ ]]
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Détection de sudo
SUDO=""
if [[ $EUID -eq 0 ]]; then
    SUDO=""
elif command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
fi

# ═══════════════════════════════════════════════════════════════════
#  1. GITHUB CLI (gh) — installation si nécessaire
# ═══════════════════════════════════════════════════════════════════
install_gh() {
    info "Installation de GitHub CLI (dépôt officiel)..."
    if [[ -z "$SUDO" ]]; then
        fail "sudo requis pour installer gh — relance avec : sudo $0"
        return 1
    fi
    "$SUDO" mkdir -p -m 755 /etc/apt/keyrings
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | "$SUDO" tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
    "$SUDO" chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        | "$SUDO" tee /etc/apt/sources.list.d/github-cli.list >/dev/null
    "$SUDO" apt-get update -qq
    "$SUDO" apt-get install -y gh
}

section "GitHub CLI (gh)"
if command -v gh >/dev/null 2>&1; then
    ok "gh installé ($(gh --version | head -1))"
else
    fail "gh non installé"
    if ask_fix "Installer GitHub CLI maintenant"; then
        install_gh && ok "gh installé" || { fail "Installation échouée."; exit 1; }
    else
        fail "gh est requis pour commiter — abandon."
        exit 1
    fi
fi

# ═══════════════════════════════════════════════════════════════════
#  2. AUTHENTIFICATION
# ═══════════════════════════════════════════════════════════════════
section "Authentification GitHub"
if gh auth status >/dev/null 2>&1; then
    ok "Déjà authentifié sur GitHub"
else
    warn "Non authentifié — authentification par token requise."
    info "Crée un token ici : https://github.com/settings/tokens (scopes: repo)"
    read -r -s -p "  ${C_CYAN}Token GitHub:${C_RESET} " GH_TOKEN
    echo
    if [[ -z "$GH_TOKEN" ]]; then
        fail "Token vide — abandon."
        exit 1
    fi
    if printf '%s\n' "$GH_TOKEN" | gh auth login --with-token >/dev/null 2>&1; then
        ok "Authentification réussie."
    else
        fail "Authentification échouée — token invalide ?"
        exit 1
    fi
fi

# S'assurer que git utilise les identifiants gh pour les opérations HTTPS
if gh auth setup-git >/dev/null 2>&1; then
    info "Git configuré pour utiliser les identifiants gh."
fi

# ═══════════════════════════════════════════════════════════════════
#  3. COMMIT
# ═══════════════════════════════════════════════════════════════════
section "Commit du projet"

if ! git -C "$SCRIPT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    fail "Ce n'est pas un dépôt git."
    exit 1
fi

# config utilisateur git (requise pour commiter)
if [[ -z "$(git -C "$SCRIPT_DIR" config user.email 2>/dev/null)" ]]; then
    warn "git user.name / user.email non configurés — commit impossible."
    info "Configure-les : git config --global user.email \"toi@example.com\""
    exit 1
fi

git -C "$SCRIPT_DIR" add -A
if git -C "$SCRIPT_DIR" diff --cached --quiet; then
    warn "Aucun changement à commiter."
    exit 0
fi

echo
git -C "$SCRIPT_DIR" status --short
echo

read -r -p "  ${C_CYAN}Message de commit:${C_RESET} " MSG
MSG="${MSG:-Update}"
if git -C "$SCRIPT_DIR" commit -m "$MSG"; then
    ok "Commit effectué : $MSG"
else
    fail "Commit échoué."
    exit 1
fi

# ═══════════════════════════════════════════════════════════════════
#  4. PUSH
# ═══════════════════════════════════════════════════════════════════
section "Push"

BRANCH="$(git -C "$SCRIPT_DIR" branch --show-current 2>/dev/null)"

# Remote de push : « origin » (votre fork) si présent, sinon le remote suivi.
PUSH_REMOTE=""
if git -C "$SCRIPT_DIR" remote get-url origin >/dev/null 2>&1; then
    PUSH_REMOTE="origin"
fi

do_push() {
    if [[ -n "$PUSH_REMOTE" ]]; then
        info "Pousser la branche « $BRANCH » vers $PUSH_REMOTE ..."
        git -C "$SCRIPT_DIR" push "$PUSH_REMOTE" "$BRANCH"
    else
        info "Pousser la branche « $BRANCH » (remote suivi) ..."
        git -C "$SCRIPT_DIR" push
    fi
}

do_force_push() {
    if [[ -n "$PUSH_REMOTE" ]]; then
        git -C "$SCRIPT_DIR" push --force-with-lease "$PUSH_REMOTE" "$BRANCH"
    else
        git -C "$SCRIPT_DIR" push --force-with-lease
    fi
}

remote_ahead_count() {
    # Nombre de commits présents sur le remote mais ABSENTS en local.
    git -C "$SCRIPT_DIR" rev-list --count "HEAD..$1" 2>/dev/null || echo "0"
}

verify_push() {
    # Vérifie que HEAD est bien présent sur le remote poussé.
    local remote head
    head="$(git -C "$SCRIPT_DIR" rev-parse HEAD)"
    remote="${PUSH_REMOTE:-$(git -C "$SCRIPT_DIR" config --get "branch.$BRANCH.remote" 2>/dev/null)}"
    [[ -z "$remote" ]] && return 1
    git -C "$SCRIPT_DIR" ls-remote "$remote" "refs/heads/$BRANCH" 2>/dev/null | grep -q "$head"
}

# Récupère l'état du remote pour détecter un éventuel écrasement.
REMOTE_ONLY="0"
if [[ -n "$PUSH_REMOTE" ]]; then
    git -C "$SCRIPT_DIR" fetch "$PUSH_REMOTE" "$BRANCH" >/dev/null 2>&1
    REMOTE_ONLY="$(remote_ahead_count "$PUSH_REMOTE/$BRANCH")"
fi

# ── Cas 1 : le remote a une version plus récente (risque d'écrasement) ──
if [[ "${REMOTE_ONLY:-0}" -gt 0 ]]; then
    warn "ATTENTION : le remote « ${PUSH_REMOTE:-distant} » possède ${REMOTE_ONLY} commit(s) ABSENT(S) en local."
    warn "Un push normal sera rejeté (non-fast-forward)."
    warn "Un push forcé ÉCRASERA cette version plus récente sur GitHub."
    echo
    if ask_fix "Forcer le push malgré tout (écrase la version distante)"; then
        if do_force_push; then
            ok "Push forcé réussi."
        else
            fail "Push forcé échoué (voir erreur git ci-dessus)."
            info "Dernier recours manuel : git push --force ${PUSH_REMOTE:-} ${BRANCH:-}"
        fi
    else
        info "Push forcé annulé — le commit local est conservé."
    fi
else
    # ── Cas 2 : push normal ──
    if ask_fix "Pousser vers le dépôt distant"; then
        if do_push; then
            if verify_push; then
                ok "Push réussi et vérifié (HEAD présent sur le remote)."
            else
                ok "Push réussi (sortie git OK)."
            fi
        else
            fail "Le push a échoué (voir erreur git ci-dessus)."
            while true; do
                echo
                warn "Causes possibles :"
                warn "  - Pas de droit d'écriture sur ce remote (ex: upstream d'un fork)."
                warn "  - URL du remote incorrecte ou dépôt inexistant."
                warn "  - Remote en avance (non-fast-forward) → force push nécessaire."
                if [[ -n "$PUSH_REMOTE" ]]; then
                    info "Remote « $PUSH_REMOTE » : $(git -C "$SCRIPT_DIR" remote get-url "$PUSH_REMOTE" 2>/dev/null)"
                    info "Corrige l'URL : git remote set-url $PUSH_REMOTE <URL>"
                fi

                # Re-vérifier si le remote est passé en avance entre-temps
                if [[ -n "$PUSH_REMOTE" ]]; then
                    git -C "$SCRIPT_DIR" fetch "$PUSH_REMOTE" "$BRANCH" >/dev/null 2>&1
                    REMOTE_ONLY="$(remote_ahead_count "$PUSH_REMOTE/$BRANCH")"
                fi
                if [[ "${REMOTE_ONLY:-0}" -gt 0 ]]; then
                    warn "Le remote a ${REMOTE_ONLY} commit(s) absent(s) en local."
                    if ask_fix "Forcer le push (écrase la version distante)"; then
                        if do_force_push; then ok "Push forcé réussi."; break; fi
                        fail "Push forcé échoué (voir erreur git ci-dessus)."
                        continue
                    fi
                fi

                if ask_fix "Réessayer le push normal"; then
                    if do_push; then ok "Push réussi."; break; fi
                    fail "Nouvel échec du push (voir erreur git ci-dessus)."
                else
                    warn "Push non effectué — le commit local est conservé."
                    break
                fi
            done
        fi
    fi
fi

echo
info "Terminé."
