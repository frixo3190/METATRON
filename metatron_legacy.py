#!/usr/bin/env python3
"""
METATRON - metatron_legacy.py
Legacy CLI (line-by-line). Wires db.py + tools.py + search.py + llm.py together.
Run with: python metatron.py --legacy   (or python metatron_legacy.py)
"""
import os
import sys

try:
    from export import export_menu
    from db import (
        get_connection,
        create_session,
        save_vulnerability,
        save_fix,
        save_exploit,
        save_summary,
        get_all_history,
        get_session,
        get_vulnerabilities,
        get_fixes,
        get_exploits,
        edit_vulnerability,
        edit_fix,
        edit_exploit,
        edit_summary_risk,
        delete_vulnerability,
        delete_exploit,
        delete_fix,
        delete_full_session,
        clear_session_results,
        print_history,
        print_session
    )
    from tools import interactive_tool_run, format_recon_for_llm, run_default_recon
    from llm import (analyse_target, ask_openrouter, fetch_openrouter_models,
                     get_openrouter_credits, openrouter_model_exists)
    import config
except ImportError as e:
    print()
    print("\033[91m  [✗] Dépendances Python manquantes :\033[0m")
    print(f"\033[91m      {e}\033[0m")
    print()
    print("\033[93m  [!] L'installation de METATRON est incomplète.\033[0m")
    print()
    print("\033[96m  Corrige avec :\033[0m")
    print("      ./venv/bin/python metatron.py")
    print("      (ou) ./install_audit.sh")
    print()
    sys.exit(1)


# ─────────────────────────────────────────────
# BANNER
# ─────────────────────────────────────────────

def banner():
    os.system("clear")
    provider = config.get("provider", "ollama")
    model    = config.get("model", "metatron-qwen")
    label    = "OpenRouter" if provider == "openrouter" else "Ollama (local)"
    print(f"""
\033[91m
    ███╗   ███╗███████╗████████╗ █████╗ ████████╗██████╗  ██████╗ ███╗   ██╗
    ████╗ ████║██╔════╝╚══██╔══╝██╔══██╗╚══██╔══╝██╔══██╗██╔═══██╗████╗  ██║
    ██╔████╔██║█████╗     ██║   ███████║   ██║   ██████╔╝██║   ██║██╔██╗ ██║
    ██║╚██╔╝██║██╔══╝     ██║   ██╔══██║   ██║   ██╔══██╗██║   ██║██║╚██╗██║
    ██║ ╚═╝ ██║███████╗   ██║   ██║  ██║   ██║   ██║  ██║╚██████╔╝██║ ╚████║
    ╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
\033[0m
    \033[90mAI Penetration Testing Assistant  |  Provider: {label}  |  Model: {model}  |  Parrot OS\033[0m
    \033[90m─────────────────────────────────────────────────────────────────────\033[0m
""")


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def divider(label=""):
    if label:
        print(f"\n\033[33m{'─'*20} {label} {'─'*20}\033[0m")
    else:
        print(f"\033[90m{'─'*60}\033[0m")


def prompt(text):
    return input(f"\033[36m{text}\033[0m").strip()


def success(text):
    print(f"\033[92m[+] {text}\033[0m")


def warn(text):
    print(f"\033[93m[!] {text}\033[0m")


def error(text):
    print(f"\033[91m[✗] {text}\033[0m")


def info(text):
    print(f"\033[94m[*] {text}\033[0m")


def confirm(question: str) -> bool:
    ans = prompt(f"{question} [y/N]: ").lower()
    return ans == "y"


# ─────────────────────────────────────────────
# NEW SCAN
# ─────────────────────────────────────────────

def new_scan():
    divider("NEW SCAN")
    target = prompt("[?] Enter target IP or domain: ")
    if not target:
        warn("No target entered.")
        return

    # check if target was scanned before
    history = get_all_history()
    past = [row for row in history if row[1] == target]
    if past:
        warn(f"Target '{target}' has been scanned before ({len(past)} time(s)).")
        if not confirm("Continue with a new scan?"):
            return

    # create session in history table first
    sl_no = create_session(target)
    success(f"Session created — SL# {sl_no}")

    # run recon tools
    divider("RECON")
    info("Choose recon tools to run:")
    raw_scan = interactive_tool_run(target)

    if not raw_scan.strip():
        warn("No scan data collected. Aborting.")
        delete_full_session(sl_no)
        return

    # send to AI
    divider("AI ANALYSIS")
    result = analyse_target(target, raw_scan)

    # ── save everything to DB ──────────────────
    save_analysis_results(sl_no, result)
    divider()

    # show results and offer edit/delete
    data = get_session(sl_no)
    print_session(data)

    if confirm("Edit or delete anything in this session?"):
        edit_delete_menu(sl_no)


# ─────────────────────────────────────────────
# SAVE / RE-RUN ANALYSIS HELPERS
# ─────────────────────────────────────────────

def save_analysis_results(sl_no: int, result: dict):
    """Persist the analysis result (vulns, fixes, exploits, summary)."""
    divider("SAVING TO DATABASE")

    for vuln in result["vulnerabilities"]:
        vuln_id = save_vulnerability(
            sl_no,
            vuln["vuln_name"],
            vuln["severity"],
            vuln["port"],
            vuln["service"],
            vuln["description"],
            vuln.get("attack", "")
        )
        if vuln.get("fix"):
            save_fix(sl_no, vuln_id, vuln["fix"], source="ai")
        success(f"Saved vuln: {vuln['vuln_name']} [{vuln['severity']}]")

    for exp in result["exploits"]:
        save_exploit(
            sl_no,
            exp["exploit_name"],
            exp["tool_used"],
            exp["payload"],
            exp["result"],
            exp["notes"]
        )
        success(f"Saved exploit: {exp['exploit_name']}")

    save_summary(
        sl_no,
        result["raw_scan"],
        result["full_response"],
        result["risk_level"]
    )

    success(f"All data saved. SL# {sl_no} | Risk: {result['risk_level']}")


def _is_ai_error(data: dict) -> bool:
    """Détecte si l'analyse IA enregistrée est en fait un message d'erreur."""
    s = data.get("summary")
    if not s:
        return False
    text = str(s[3] or "").strip()
    if not text:
        return True
    return (text.startswith("[!]")
            or "[!] OpenRouter" in text
            or "[!] Ollama" in text)


def rerun_analysis(sl_no: int, data: dict):
    """Relance l'analyse IA à partir du raw_scan déjà enregistré."""
    target   = data["history"][1]
    raw_scan = data["summary"][2] if data["summary"] else ""

    if not str(raw_scan or "").strip():
        error("Aucune donnée de scan brute enregistrée — impossible de relancer.")
        return

    divider("AI RE-ANALYSIS")
    result = analyse_target(target, str(raw_scan))

    clear_session_results(sl_no)
    save_analysis_results(sl_no, result)
    divider()

    print_session(get_session(sl_no))


# ─────────────────────────────────────────────
# VIEW HISTORY
# ─────────────────────────────────────────────

def view_history():
    divider("SCAN HISTORY")
    rows = get_all_history()

    if not rows:
        warn("No scans in database yet.")
        return

    print_history(rows)

    sl_no_str = prompt("Enter SL# to view details (or press Enter to go back): ")
    if not sl_no_str:
        return

    try:
        sl_no = int(sl_no_str)
    except ValueError:
        error("Invalid SL#.")
        return

    data = get_session(sl_no)
    if not data["history"]:
        error(f"SL# {sl_no} not found.")
        return

    print_session(data)

    if _is_ai_error(data):
        warn("L'analyse IA de cette session contient une erreur "
             "(ex: OpenRouter error).")
        if confirm("Relancer l'analyse IA avec les données de scan existantes ?"):
            rerun_analysis(sl_no, data)

    if confirm("Export this session?"):
        export_menu(data)

    if confirm("Edit or delete anything in this session?"):
        edit_delete_menu(sl_no)


# ─────────────────────────────────────────────
# EDIT / DELETE MENU
# ─────────────────────────────────────────────

def edit_delete_menu(sl_no: int):
    while True:
        divider(f"EDIT / DELETE — SL# {sl_no}")
        print("  [1] Edit a vulnerability")
        print("  [2] Edit a fix")
        print("  [3] Edit an exploit")
        print("  [4] Edit risk level")
        print("  [5] Delete a vulnerability")
        print("  [6] Delete a fix")
        print("  [7] Delete an exploit")
        print("  [8] Delete FULL session (all tables)")
        print("  [9] Back")
        divider()

        choice = prompt("Choice: ")

        # ── EDIT VULNERABILITY ─────────────────
        if choice == "1":
            vulns = get_vulnerabilities(sl_no)
            if not vulns:
                warn("No vulnerabilities recorded for this session.")
                continue

            print("\n[ VULNERABILITIES ]")
            for v in vulns:
                print(f"  id={v[0]} | {v[2]} | {v[3]} | port {v[4]} | {v[5]}")

            vid = prompt("Enter vulnerability id to edit: ")
            if not vid.isdigit():
                error("Invalid id.")
                continue

            print("  Fields: vuln_name / severity / port / service / description")
            field = prompt("Field to edit: ").strip()
            value = prompt(f"New value for '{field}': ")
            edit_vulnerability(int(vid), field, value)

        # ── EDIT FIX ──────────────────────────
        elif choice == "2":
            fixes = get_fixes(sl_no)
            if not fixes:
                warn("No fixes recorded for this session.")
                continue

            print("\n[ FIXES ]")
            for f in fixes:
                print(f"  id={f[0]} | vuln_id={f[2]} | {f[3][:80]}")

            fid = prompt("Enter fix id to edit: ")
            if not fid.isdigit():
                error("Invalid id.")
                continue

            new_text = prompt("New fix text: ")
            edit_fix(int(fid), new_text)

        # ── EDIT EXPLOIT ──────────────────────
        elif choice == "3":
            exploits = get_exploits(sl_no)
            if not exploits:
                warn("No exploits recorded for this session.")
                continue

            print("\n[ EXPLOITS ]")
            for e in exploits:
                print(f"  id={e[0]} | {e[2]} | tool: {e[3]} | result: {e[5]}")

            eid = prompt("Enter exploit id to edit: ")
            if not eid.isdigit():
                error("Invalid id.")
                continue

            print("  Fields: exploit_name / tool_used / payload / result / notes")
            field = prompt("Field to edit: ").strip()
            value = prompt(f"New value for '{field}': ")
            edit_exploit(int(eid), field, value)

        # ── EDIT RISK LEVEL ───────────────────
        elif choice == "4":
            print("  Options: CRITICAL / HIGH / MEDIUM / LOW")
            risk = prompt("New risk level: ").upper()
            if risk not in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
                error("Invalid risk level.")
                continue
            edit_summary_risk(sl_no, risk)

        # ── DELETE VULNERABILITY ──────────────
        elif choice == "5":
            vulns = get_vulnerabilities(sl_no)
            if not vulns:
                warn("No vulnerabilities to delete.")
                continue

            print("\n[ VULNERABILITIES ]")
            for v in vulns:
                print(f"  id={v[0]} | {v[2]} | {v[3]}")

            vid = prompt("Enter vulnerability id to delete: ")
            if not vid.isdigit():
                error("Invalid id.")
                continue

            if confirm(f"Delete vulnerability id={vid} and its linked fixes?"):
                delete_vulnerability(int(vid))

        # ── DELETE FIX ────────────────────────
        elif choice == "6":
            fixes = get_fixes(sl_no)
            if not fixes:
                warn("No fixes to delete.")
                continue

            print("\n[ FIXES ]")
            for f in fixes:
                print(f"  id={f[0]} | vuln_id={f[2]} | {f[3][:80]}")

            fid = prompt("Enter fix id to delete: ")
            if not fid.isdigit():
                error("Invalid id.")
                continue

            if confirm(f"Delete fix id={fid}?"):
                delete_fix(int(fid))

        # ── DELETE EXPLOIT ────────────────────
        elif choice == "7":
            exploits = get_exploits(sl_no)
            if not exploits:
                warn("No exploits to delete.")
                continue

            print("\n[ EXPLOITS ]")
            for e in exploits:
                print(f"  id={e[0]} | {e[2]} | result: {e[5]}")

            eid = prompt("Enter exploit id to delete: ")
            if not eid.isdigit():
                error("Invalid id.")
                continue

            if confirm(f"Delete exploit id={eid}?"):
                delete_exploit(int(eid))

        # ── DELETE FULL SESSION ───────────────
        elif choice == "8":
            if confirm(f"\n\033[91mPermanently delete ENTIRE session SL# {sl_no} from all tables?\033[0m"):
                delete_full_session(sl_no)
                success(f"Session SL# {sl_no} wiped.")
                return   # go back to main menu

        # ── BACK ──────────────────────────────
        elif choice == "9":
            break

        else:
            warn("Invalid choice.")


# ─────────────────────────────────────────────
# PREFLIGHT CHECK (installation)
# ─────────────────────────────────────────────

def preflight_check() -> bool:
    """Vérifie les prérequis au lancement et affiche un rapport coloré."""
    import shutil
    import requests as _requests

    print("\n\033[1m\033[36m" + "─"*18 + " VÉRIFICATION DE L'INSTALLATION " + "─"*18 + "\033[0m")

    ok = True

    # 1) MariaDB (critique)
    try:
        conn = get_connection()
        conn.close()
        success("MariaDB      : connexion OK")
    except Exception as e:
        error(f"MariaDB      : connexion impossible ({e})")
        error("               → sudo systemctl start mariadb   (ou ./install_audit.sh)")
        ok = False

    # 2) Outils système (non bloquant)
    missing = [t for t in ("nmap", "whois", "whatweb", "curl", "dig", "nikto")
               if shutil.which(t) is None]
    if missing:
        warn(f"Outils recon : manquants → {', '.join(missing)}")
        warn(f"               → sudo apt install{' '.join(missing)}")
    else:
        success("Outils recon : tous présents")

    # 3) Backend IA
    provider = config.get("provider", "ollama")
    if provider == "openrouter":
        key   = config.get("api_key", "").strip()
        model = config.get("model", "").strip()
        if not key or not model:
            warn("Backend IA   : OpenRouter configuré mais clé/modèle manquant(s)")
            warn("               → menu [3] Settings pour les renseigner")
        else:
            res = openrouter_model_exists(model)
            if res.get("exists"):
                success(f"Backend IA   : OpenRouter ({model})")
            elif res.get("error") == "not_found":
                warn(f"Backend IA   : OpenRouter — le modèle « {model} » n'existe plus")
                warn("               → menu [3] Settings → choisir un modèle")
            elif res.get("error") in ("network", "timeout"):
                warn(f"Backend IA   : OpenRouter ({model}) — vérification du modèle impossible (réseau)")
            elif res.get("error") == "unauthorized":
                warn("Backend IA   : OpenRouter — clé API invalide (401)")
                warn("               → menu [3] Settings → clé API")
            else:
                warn(f"Backend IA   : OpenRouter ({model})")
    else:
        try:
            _requests.get("http://localhost:11434", timeout=3)
            success("Backend IA   : Ollama joignable")
        except Exception:
            warn("Backend IA   : Ollama injoignable (lance « ollama serve »)")
            warn("               → ou bascule sur OpenRouter : menu [3] Settings")

    print("\033[90m" + "─"*60 + "\033[0m")
    if ok:
        success("Installation OK — bon scan.")
    else:
        error("Problème(s) critique(s) détecté(s) — corrige avant de continuer.")
        error("Lance : ./install_audit.sh")
    print()
    return ok


# ─────────────────────────────────────────────
# SETTINGS MENU (AI provider / OpenRouter)
# ─────────────────────────────────────────────

def _fmt_cost(v):
    if v is None:
        return "n/a"
    if v == 0:
        return "$0.00"
    return f"${v:.2f}"


def _display_credits(credits: dict, prefix: str = "  "):
    """Affiche le crédit OpenRouter (ou l'erreur correspondante)."""
    if not credits:
        print(f"{prefix}Crédit restant: \033[91mimpossible à récupérer\033[0m")
        return

    err    = credits.get("error")
    rem    = credits.get("remaining")
    usg    = credits.get("usage")
    source = credits.get("source")

    if err == "no_key":
        print(f"{prefix}Crédit restant: \033[90mclé non configurée\033[0m")
        return
    if err == "unauthorized":
        print(f"{prefix}Crédit restant: \033[91mclé API invalide (401)\033[0m")
        return
    if err in ("network", "timeout"):
        print(f"{prefix}Crédit restant: \033[91mOpenRouter injoignable ({err})\033[0m")
        return
    if err == "parse":
        print(f"{prefix}Crédit restant: \033[91mréponse illisible\033[0m")
        return
    if err == "forbidden":
        print(f"{prefix}Crédit restant: \033[91mindisponible (403)\033[0m")
        return
    if err == "management_required":
        if usg is not None:
            print(f"{prefix}Usage          : ${usg:.2f}")
        print(f"{prefix}Crédit restant: \033[93mnon exposé par cette clé (management key requise)\033[0m")
        if credits.get("is_free_tier"):
            print(f"{prefix}\033[93m[!] Compte en tier gratuit (rate limits actifs).\033[0m")
        return

    if rem is not None:
        line = f"{prefix}Crédit restant: \033[92m${rem:.2f}\033[0m"
        if usg is not None:
            line += f"   (utilisé : ${usg:.2f})"
        print(line)
        if source == "key":
            print(f"{prefix}\033[93m[!] Solde per-clé — le solde complet requiert une management key.\033[0m")
    elif usg is not None:
        print(f"{prefix}Usage          : ${usg:.2f}")

    if credits.get("is_free_tier"):
        print(f"{prefix}\033[93m[!] Compte en tier gratuit (rate limits actifs).\033[0m")


def _verify_openrouter_model(model_id: str):
    """Vérifie que le modèle OpenRouter configuré existe. Affiche le résultat."""
    if not config.get("api_key", "").strip():
        return
    info(f"Vérification du modèle « {model_id} » sur OpenRouter...")
    res = openrouter_model_exists(model_id)
    if res.get("exists"):
        success(f"Modèle « {model_id} » trouvé sur OpenRouter.")
        return

    err = res.get("error")
    if err == "not_found":
        error(f"Le modèle « {model_id} » n'existe pas sur OpenRouter.")
        warn("Sélectionne un autre modèle : option [3].")
    elif err == "no_model":
        warn("Aucun modèle OpenRouter configuré. Choisis-en un : option [3].")
    elif err == "unauthorized":
        error("Clé API invalide (401) — impossible de vérifier le modèle.")
    elif err in ("network", "timeout"):
        warn("OpenRouter injoignable — vérification du modèle impossible.")
    else:
        warn("Vérification du modèle impossible.")


def test_openrouter():
    """Envoie un prompt de test à OpenRouter et affiche la réponse."""
    api_key = config.get("api_key", "").strip()
    model   = config.get("model", "").strip()
    if not api_key:
        error("Aucune clé API OpenRouter configurée (option [2]).")
        return
    if not model:
        error("Aucun modèle OpenRouter sélectionné (option [3]).")
        return

    info(f"Envoi d'un prompt de test à « {model} »...")
    resp = ask_openrouter([
        {"role": "user",
         "content": "Réponds en une seule phrase : es-tu opérationnel et prêt à analyser des cibles ?"}
    ], max_tokens=128, temperature=0.3)

    print("\n" + "─" * 60)
    print("\033[96m  RÉPONSE DU MODÈLE :\033[0m")
    print(f"  {resp}")
    print("─" * 60 + "\n")


def settings_menu():
    while True:
        provider = config.get("provider", "ollama")
        model    = config.get("model", "metatron-qwen")
        api_key  = config.get("api_key", "")

        print("\n\033[33m" + "─"*20 + " SETTINGS — AI " + "─"*20 + "\033[0m")
        print(f"  Fournisseur  : \033[92m{provider.upper()}\033[0m")
        print(f"  Modèle       : \033[92m{model}\033[0m")
        print(f"  Langue       : \033[92m{config.LANGUAGES.get(config.get('language', 'en').lower(), config.get('language', 'en')).upper()}\033[0m")
        print(f"  Clé OpenRouter: \033[90m{config.mask_key(api_key)}\033[0m")

        if provider == "openrouter":
            _display_credits(get_openrouter_credits())

        print()
        print("  [1] Basculer fournisseur (Ollama <-> OpenRouter)")
        print("  [2] Clé API OpenRouter (saisir / modifier)")
        print("  [3] Choisir le modèle OpenRouter")
        print("  [4] Rafraîchir le crédit restant")
        print("  [5] Tester OpenRouter (envoyer un prompt)")
        print("  [6] Langue des analyses (Français / Anglais)")
        print("  [7] Retour")
        print("\033[90m" + "─"*60 + "\033[0m")

        choice = prompt("settings> ")

        # ── SWITCH PROVIDER ───────────────────
        if choice == "1":
            new = "openrouter" if provider == "ollama" else "ollama"
            if new == "openrouter":
                if not api_key.strip():
                    warn("Aucune clé API OpenRouter configurée.")
                    warn("Ajoute-la d'abord (option [2]), puis choisis un modèle (option [3]).")
                config.set("provider", "openrouter")
                success("Fournisseur : OpenRouter")
                _verify_openrouter_model(model)
            else:
                config.set("provider", "ollama")
                success("Fournisseur : Ollama (local)")

        # ── API KEY ──────────────────────────
        elif choice == "2":
            print(f"\n  Clé actuelle : {config.mask_key(api_key)}")
            new_key = prompt("Nouvelle clé API OpenRouter (Entrée pour garder): ")
            if new_key:
                config.set("api_key", new_key.strip())
                success("Clé API enregistrée.")
                if config.get("provider", "ollama") != "openrouter":
                    if confirm("Basculer sur OpenRouter maintenant ?"):
                        config.set("provider", "openrouter")
                        success("Fournisseur : OpenRouter")

        # ── SELECT MODEL ─────────────────────
        elif choice == "3":
            if not api_key.strip():
                warn("Configure d'abord une clé API (option [2]).")
                continue
            info("Récupération de la liste des modèles OpenRouter...")
            models = fetch_openrouter_models()
            if not models:
                error("Aucun modèle récupéré. Vérifie ta connexion / ta clé.")
                continue

            print("\n[ MODÈLES OPENROUTER ]")
            print(f"{'':<4}{'MODÈLE':<42}{'COÛT (input / output) par 1M tokens'}")
            print("─" * 78)
            for i, m in enumerate(models, 1):
                cost = (f"{_fmt_cost(m['prompt_usd_per_m'])} / "
                        f"{_fmt_cost(m['completion_usd_per_m'])}")
                print(f"  [{i:<3}] {m['id']:<40} {cost}")
            print("─" * 78)

            sel = prompt(f"Numéro du modèle (1-{len(models)}), ou Entrée pour annuler: ")
            if not sel:
                continue
            if not sel.isdigit() or not (1 <= int(sel) <= len(models)):
                error("Numéro invalide.")
                continue
            chosen = models[int(sel) - 1]
            config.set("model", chosen["id"])
            config.set("provider", "openrouter")
            success(f"Modèle sélectionné : {chosen['id']}")

        # ── REFRESH CREDITS ──────────────────
        elif choice == "4":
            if provider != "openrouter":
                warn("Le fournisseur actuel est Ollama — aucun crédit OpenRouter à afficher.")
                continue
            _display_credits(get_openrouter_credits())

        # ── TEST OPENROUTER ──────────────────
        elif choice == "5":
            test_openrouter()

        # ── LANGUAGE ─────────────────────────
        elif choice == "6":
            current = config.get("language", "en").lower()
            print(f"\n  Langue actuelle : {config.LANGUAGES.get(current, current)}")
            print("  [fr] Français")
            print("  [en] Anglais")
            lang = prompt("Langue [fr/en]: ").strip().lower()
            if lang in ("fr", "francais", "français"):
                config.set("language", "fr")
                success("Langue des analyses : Français")
            elif lang in ("en", "english", "anglais"):
                config.set("language", "en")
                success("Langue des analyses : Anglais")
            else:
                warn("Langue invalide (utilise fr ou en).")

        # ── BACK ─────────────────────────────
        elif choice == "7":
            break

        else:
            warn("Choix invalide.")


# ─────────────────────────────────────────────
# MAIN MENU
# ─────────────────────────────────────────────

def main_menu():
    while True:
        banner()
        print("  \033[92m[1]\033[0m  New Scan")
        print("  \033[92m[2]\033[0m  View History")
        print("  \033[92m[3]\033[0m  Settings (IA)")
        print("  \033[92m[4]\033[0m  Exit")
        divider()

        choice = prompt("metatron> ")

        if choice == "1":
            new_scan()
            input("\n\033[90mPress Enter to continue...\033[0m")

        elif choice == "2":
            view_history()
            input("\n\033[90mPress Enter to continue...\033[0m")

        elif choice == "3":
            settings_menu()

        elif choice == "4":
            print("\n\033[91m[*] Shutting down Metatron. Stay legal.\033[0m\n")
            sys.exit(0)

        else:
            warn("Invalid choice.")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def main():
    if not preflight_check():
        sys.exit(1)
    main_menu()


if __name__ == "__main__":
    main()
