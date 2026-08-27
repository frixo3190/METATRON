"""Internationalisation (fr/en) du TUI METATRON."""

import config

STRINGS = {
    # Application
    "app.subtitle": {
        "fr": "Assistant de test d'intrusion IA",
        "en": "AI Penetration Testing Assistant",
    },
    # Menu principal
    "menu.scan":     {"fr": "Nouveau scan", "en": "New scan"},
    "menu.history":  {"fr": "Historique", "en": "History"},
    "menu.settings": {"fr": "Paramètres (IA)", "en": "Settings (AI)"},
    "menu.quit":     {"fr": "Quitter", "en": "Quit"},
    "menu.tagline": {
        "fr": "Recon automatisée · Analyse IA · Rapports",
        "en": "Automated recon · AI analysis · Reports",
    },
    # Paramètres
    "settings.title": {
        "fr": "Paramètres (IA)",
        "en": "Settings (AI)",
    },
    "settings.provider_label": {
        "fr": "Basculer fournisseur (actuel : {p})",
        "en": "Switch provider (current: {p})",
    },
    "settings.key": {
        "fr": "Clé API OpenRouter (saisir / modifier)",
        "en": "OpenRouter API key (set / edit)",
    },
    "settings.model": {
        "fr": "Choisir le modèle OpenRouter (coût affiché)",
        "en": "Choose OpenRouter model (cost shown)",
    },
    "settings.credits": {
        "fr": "Rafraîchir le crédit restant",
        "en": "Refresh remaining credits",
    },
    "settings.test": {
        "fr": "Tester OpenRouter (envoyer un prompt)",
        "en": "Test OpenRouter (send a prompt)",
    },
    "settings.lang": {
        "fr": "Langue (actuel : {l})",
        "en": "Language (current: {l})",
    },
    "settings.back": {"fr": "Retour", "en": "Back"},
    # Champs de l'en-tête d'information
    "field.provider": {"fr": "Fournisseur", "en": "Provider"},
    "field.model":    {"fr": "Modèle", "en": "Model"},
    "field.lang":     {"fr": "Langue", "en": "Language"},
    "field.key":      {"fr": "Clé", "en": "Key"},
    "field.credits":  {"fr": "Crédit", "en": "Credits"},
    "credits.fetching": {"fr": "récupération…", "en": "fetching…"},
    "credits.no_key":   {"fr": "clé non configurée", "en": "no key set"},
    "credits.invalid":  {"fr": "clé invalide (401)", "en": "invalid key (401)"},
    "credits.used":     {"fr": "utilisé", "en": "used"},
    "credits.unavailable": {"fr": "indisponible", "en": "unavailable"},
    # Noms de langues (dans la langue courante)
    "lang.fr": {"fr": "Français", "en": "French"},
    "lang.en": {"fr": "Anglais", "en": "English"},
    # Descriptions de raccourcis (footer)
    "binding.back":    {"fr": "Retour", "en": "Back"},
    "binding.quit":    {"fr": "Quitter", "en": "Quit"},
    "binding.scan":    {"fr": "Nouveau scan", "en": "New scan"},
    "binding.history": {"fr": "Historique", "en": "History"},
    "binding.settings": {"fr": "Paramètres", "en": "Settings"},
    "binding.credits": {"fr": "Crédits", "en": "Credits"},
    # Modèles
    "model.title": {
        "fr": "Choisir le modèle OpenRouter",
        "en": "Choose OpenRouter model",
    },
    "model.subtitle": {
        "fr": "Trié du moins cher au plus cher — coût (input / output) par 1M tokens",
        "en": "Sorted cheapest first — cost (input / output) per 1M tokens",
    },
    "model.search": {
        "fr": "Rechercher un modèle (tapez des lettres)…",
        "en": "Search a model (type letters)…",
    },
    "model.loading": {
        "fr": "Récupération de la liste des modèles…",
        "en": "Fetching the model list…",
    },
    "model.none": {
        "fr": "Aucun modèle récupéré. Vérifie ta connexion / ta clé.",
        "en": "No models fetched. Check your connection / key.",
    },
    "model.count": {"fr": "{n} modèles disponibles", "en": "{n} models available"},
    "model.results": {
        "fr": "{n} résultat(s) pour « {q} » sur {total} modèles",
        "en": "{n} result(s) for \"{q}\" out of {total} models",
    },
    # Test OpenRouter
    "test.title": {"fr": "Tester OpenRouter", "en": "Test OpenRouter"},
    "test.sending": {
        "fr": "Envoi d'un prompt de test à « {m} »…",
        "en": "Sending a test prompt to \"{m}\"…",
    },
    "test.reply": {"fr": "Réponse", "en": "Reply"},
    "test.no_key": {
        "fr": "Aucune clé API OpenRouter configurée.",
        "en": "No OpenRouter API key configured.",
    },
    "test.no_model": {
        "fr": "Aucun modèle OpenRouter sélectionné.",
        "en": "No OpenRouter model selected.",
    },
    # Clé API
    "key.title": {"fr": "Clé API OpenRouter", "en": "OpenRouter API key"},
    "key.current": {"fr": "Clé actuelle", "en": "Current key"},
    "key.hint": {
        "fr": "Entrée pour valider · Échap pour annuler",
        "en": "Enter to save · Esc to cancel",
    },
    # Notifications
    "notify.provider.openrouter": {"fr": "Fournisseur : OpenRouter", "en": "Provider: OpenRouter"},
    "notify.provider.ollama": {"fr": "Fournisseur : Ollama (local)", "en": "Provider: Ollama (local)"},
    "notify.key_missing": {
        "fr": "Clé API OpenRouter manquante (voir Clé API)",
        "en": "OpenRouter API key missing (see API key)",
    },
    "notify.lang": {"fr": "Langue : {l}", "en": "Language: {l}"},
    "notify.key_saved": {"fr": "Clé API OpenRouter enregistrée", "en": "OpenRouter API key saved"},
    "notify.model_selected": {"fr": "Modèle sélectionné : {m}", "en": "Model selected: {m}"},
    "notify.model_found": {"fr": "Modèle « {m} » trouvé sur OpenRouter", "en": "Model \"{m}\" found on OpenRouter"},
    "notify.model_missing": {
        "fr": "Modèle « {m} » introuvable sur OpenRouter — resélectionne-le",
        "en": "Model \"{m}\" not found on OpenRouter — reselect it",
    },
    "notify.no_credits": {
        "fr": "Fournisseur actuel : Ollama — pas de crédit OpenRouter",
        "en": "Current provider: Ollama — no OpenRouter credits",
    },
    # Historique
    "history.title": {"fr": "Historique", "en": "History"},
    "history.empty": {"fr": "Aucun scan dans la base.", "en": "No scans in the database."},
    "history.col.target": {"fr": "Cible", "en": "Target"},
    "history.col.date": {"fr": "Date", "en": "Date"},
    "history.col.status": {"fr": "Statut", "en": "Status"},
    "history.col.tools": {"fr": "Outils lancés", "en": "Tools run"},
    "history.count": {"fr": "{n} session(s)", "en": "{n} session(s)"},
    # Session
    "session.title": {"fr": "Session SL# {sl} — {target}", "en": "Session SL# {sl} — {target}"},
    "session.tab.vulns": {"fr": "Vulnérabilités", "en": "Vulnerabilities"},
    "session.tab.fixes": {"fr": "Fixes", "en": "Fixes"},
    "session.tab.exploits": {"fr": "Exploits", "en": "Exploits"},
    "session.tab.analysis": {"fr": "Analyse", "en": "Analysis"},
    "session.risk": {"fr": "Risque", "en": "Risk"},
    "session.generated": {"fr": "Généré", "en": "Generated"},
    "session.none": {"fr": "Aucun enregistré.", "en": "None recorded."},
    "session.ai_error": {
        "fr": "L'analyse IA de cette session contient une erreur — relance-la (r).",
        "en": "The AI analysis of this session contains an error — re-run it (r).",
    },
    # Exports
    "export.title": {"fr": "Exporter la session", "en": "Export session"},
    "export.pdf": {"fr": "Rapport PDF", "en": "PDF report"},
    "export.html": {"fr": "Rapport HTML", "en": "HTML report"},
    "export.both": {"fr": "Les deux", "en": "Both"},
    "export.saved": {"fr": "Exporté : {p}", "en": "Exported: {p}"},
    "export.failed": {"fr": "Échec de l'export : {e}", "en": "Export failed: {e}"},
    # Suppression
    "delete.confirm": {
        "fr": "Supprimer définitivement la session SL# {sl} ?",
        "en": "Permanently delete session SL# {sl}?",
    },
    "delete.done": {"fr": "Session SL# {sl} supprimée.", "en": "Session SL# {sl} deleted."},
    "confirm.yes": {"fr": "Oui", "en": "Yes"},
    "confirm.no": {"fr": "Non", "en": "No"},
    # Relance d'analyse
    "rerun.title": {"fr": "Relance de l'analyse", "en": "Re-running analysis"},
    "rerun.no_scan": {
        "fr": "Pas de données de scan brutes — impossible de relancer.",
        "en": "No raw scan data — cannot re-run.",
    },
    "rerun.done": {
        "fr": "Analyse relancée. SL# {sl} | Risque : {risk}",
        "en": "Analysis re-run. SL# {sl} | Risk: {risk}",
    },
    "rerun.failed": {"fr": "Échec de l'analyse.", "en": "Analysis failed."},
    # Raccourcis
    "binding.export": {"fr": "Exporter", "en": "Export"},
    "binding.rerun": {"fr": "Relancer", "en": "Re-run"},
    "binding.delete": {"fr": "Supprimer", "en": "Delete"},
    "binding.chat": {"fr": "Discuter", "en": "Chat"},
    # Sévérités (traduites)
    "sev.critical": {"fr": "CRITIQUE", "en": "CRITICAL"},
    "sev.high": {"fr": "ÉLEVÉ", "en": "HIGH"},
    "sev.medium": {"fr": "MOYEN", "en": "MEDIUM"},
    "sev.low": {"fr": "FAIBLE", "en": "LOW"},
    "sev.unknown": {"fr": "INCONNU", "en": "UNKNOWN"},
    # Libellés des items de session
    "session.port": {"fr": "Port", "en": "Port"},
    "session.service": {"fr": "Service", "en": "Service"},
    "session.tool": {"fr": "Outil", "en": "Tool"},
    "session.result": {"fr": "Résultat", "en": "Result"},
    "session.payload": {"fr": "Payload", "en": "Payload"},
    "session.notes": {"fr": "Notes", "en": "Notes"},
    "session.vuln_id": {"fr": "Vulnérabilité", "en": "Vulnerability"},
    "session.attack": {"fr": "Attaque", "en": "Attack"},
    "session.select_hint": {
        "fr": "Entrée = discuter avec l'IA · A = tester l'attaque · Échap = retour",
        "en": "Enter = chat with AI · A = test attack · Esc = back",
    },
    # Chat IA
    "chat.title": {"fr": "Discussion IA", "en": "AI chat"},
    "chat.input.placeholder": {
        "fr": "Pose ta question sur cette vulnérabilité…",
        "en": "Ask a question about this vulnerability…",
    },
    "chat.context.title": {"fr": "Contexte du scan", "en": "Scan context"},
    "chat.thinking": {"fr": "Réflexion…", "en": "Thinking…"},
    "chat.you": {"fr": "Toi", "en": "You"},
    "chat.ai": {"fr": "Metatron", "en": "Metatron"},
    "chat.welcome": {
        "fr": "Pose-moi tes questions sur cette cible et ce résultat.",
        "en": "Ask me your questions about this target and result.",
    },
    # Test d'attaque
    "attack.title": {"fr": "Tester l'attaque", "en": "Test the attack"},
    "attack.hint": {
        "fr": "Éditez les commandes puis Ctrl+S pour lancer · Échap pour annuler",
        "en": "Edit commands then Ctrl+S to run · Esc to cancel",
    },
    "attack.warning": {
        "fr": "Ces commandes vont s'exécuter sur VOTRE machine. Vérifiez-les !",
        "en": "These commands will run on YOUR machine. Review them!",
    },
    "attack.no_commands": {
        "fr": "Aucune commande d'attaque disponible.",
        "en": "No attack commands available.",
    },
    "attack.done": {"fr": "Attaque terminée.", "en": "Attack finished."},
    "attack.failed": {"fr": "Échec de l'attaque.", "en": "Attack failed."},
    "binding.attack": {"fr": "Attaquer", "en": "Attack"},
    "binding.run": {"fr": "Lancer", "en": "Run"},
    "binding.scan_run": {"fr": "Lancer", "en": "Run"},
    "binding.chat": {"fr": "Discuter", "en": "Chat"},
    "binding.session": {"fr": "Session", "en": "Session"},
    # Nouveau scan
    "scan.title": {"fr": "Nouveau scan", "en": "New scan"},
    "scan.target.placeholder": {"fr": "Cible (IP ou domaine)…", "en": "Target (IP or domain)…"},
    "scan.tools": {"fr": "Outils de recon", "en": "Recon tools"},
    "scan.hint": {
        "fr": "Entrée = lancer · Espace = cocher · Échap = retour",
        "en": "Enter = run · Space = check · Esc = back",
    },
    "scan.no_target": {"fr": "Saisis une cible.", "en": "Enter a target."},
    "scan.no_tools": {
        "fr": "Sélectionne au moins un outil.",
        "en": "Select at least one tool.",
    },
    "scan.done": {
        "fr": "Scan terminé — SL# {sl} | Risque : {risk}",
        "en": "Scan done — SL# {sl} | Risk: {risk}",
    },
    "scan.analyzing": {"fr": "Analyse IA en cours…", "en": "AI analysis running…"},
    "scan.tours.explain": {
        "fr": "« Tours » = l'IA analyse les données, lance des outils supplémentaires si besoin, puis re-analyse avec les nouveaux résultats. Chaque itération est un tour.",
        "en": "\"Rounds\" = the AI analyzes the data, launches extra tools if needed, then re-analyzes with the new results. Each iteration is a round.",
    },
    "scan.running": {"fr": "Scan en cours", "en": "Scan running"},
    "scan.finished": {
        "fr": "Scan terminé — c = discuter · s = session · échap = retour",
        "en": "Scan done — c = chat · s = session · esc = back",
    },
    "scan.not_done": {
        "fr": "Le scan n'est pas encore terminé.",
        "en": "The scan is not finished yet.",
    },
    # Descriptions des outils de recon
    "tool.nmap": {
        "fr": "Nmap — ports ouverts + versions des services",
        "en": "Nmap — open ports + service versions",
    },
    "tool.whois": {
        "fr": "Whois — propriétaire du domaine, registrar, IP",
        "en": "Whois — domain owner, registrar, IP",
    },
    "tool.whatweb": {
        "fr": "WhatWeb — CMS, frameworks, technologies web",
        "en": "WhatWeb — CMS, frameworks, web tech",
    },
    "tool.curl": {
        "fr": "Curl — en-têtes HTTP, serveur, cookies, sécurité",
        "en": "Curl — HTTP headers, server, cookies, security",
    },
    "tool.dig": {
        "fr": "Dig — enregistrements DNS (A, MX, NS, TXT)",
        "en": "Dig — DNS records (A, MX, NS, TXT)",
    },
    "tool.nikto": {
        "fr": "Nikto — vulnérabilités serveur web, fichiers sensibles",
        "en": "Nikto — web server vulns, sensitive files",
    },
    # Édition / suppression
    "binding.edit": {"fr": "Éditer", "en": "Edit"},
    "edit.title.vuln": {"fr": "Éditer la vulnérabilité", "en": "Edit vulnerability"},
    "edit.title.exploit": {"fr": "Éditer l'exploit", "en": "Edit exploit"},
    "edit.title.fix": {"fr": "Éditer le correctif", "en": "Edit fix"},
    "edit.field.name": {"fr": "Nom", "en": "Name"},
    "edit.field.severity": {"fr": "Sévérité", "en": "Severity"},
    "edit.field.port": {"fr": "Port", "en": "Port"},
    "edit.field.service": {"fr": "Service", "en": "Service"},
    "edit.field.description": {"fr": "Description", "en": "Description"},
    "edit.field.attack": {"fr": "Attaque", "en": "Attack"},
    "edit.field.tool": {"fr": "Outil", "en": "Tool"},
    "edit.field.payload": {"fr": "Payload", "en": "Payload"},
    "edit.field.result": {"fr": "Résultat", "en": "Result"},
    "edit.field.notes": {"fr": "Notes", "en": "Notes"},
    "edit.value.prompt": {"fr": "Nouvelle valeur", "en": "New value"},
    "edit.fixes": {"fr": "Correctifs", "en": "Fixes"},
    "edit.delete.vuln": {"fr": "Supprimer la vulnérabilité", "en": "Delete vulnerability"},
    "edit.delete.exploit": {"fr": "Supprimer l'exploit", "en": "Delete exploit"},
    "edit.delete.fix": {"fr": "Supprimer ce correctif", "en": "Delete this fix"},
    "edit.confirm.delete": {"fr": "Supprimer « {t} » ?", "en": "Delete \"{t}\"?"},
    "edit.done": {"fr": "Modifié.", "en": "Updated."},
}

DEFAULT_LANG = "en"


def lang() -> str:
    l = config.get("language", DEFAULT_LANG).lower()
    return l if l in ("fr", "en") else DEFAULT_LANG


def t(key: str, **fmt) -> str:
    d = STRINGS.get(key, {})
    s = d.get(lang(), d.get(DEFAULT_LANG, key))
    if fmt:
        try:
            s = s.format(**fmt)
        except (KeyError, ValueError):
            pass
    return s


def lang_name(code: str) -> str:
    return t(f"lang.{code}" if code in ("fr", "en") else "lang.en")


def localize_bindings(node, show_overrides=None) -> None:
    """Traduit les descriptions des raccourcis d'un écran (footer).

    `show_overrides` : dict {binding_id: bool} pour forcer la visibilité
    de certains raccourcis (ex: masquer « attaquer » si pas de commandes).
    """
    from textual.binding import Binding, BindingsMap

    show_overrides = show_overrides or {}
    keys = {}
    for b in getattr(node, "BINDINGS", []):
        desc = t(b.id) if b.id else b.description
        show = show_overrides.get(b.id, b.show)
        nb = Binding(
            b.key,
            b.action,
            description=desc,
            show=show,
            key_display=b.key_display,
            priority=b.priority,
            id=b.id,
        )
        keys.setdefault(nb.key, []).append(nb)
    node._bindings = BindingsMap.from_keys(keys)
    node.refresh_bindings()
