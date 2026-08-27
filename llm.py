#!/usr/bin/env python3
"""
METATRON - llm.py
Ollama interface for metatron-qwen model.
Builds prompts, handles AI responses, runs tool dispatch loop.
Model: metatron-qwen (fine-tuned from huihui_ai/qwen3.5-abliterated:9b)
"""

import re
import requests
import json
from tools import run_tool_by_command, run_nmap, run_curl_headers
from search import handle_search_dispatch
import config

OLLAMA_URL  = "http://localhost:11434/api/chat"
OPENROUTER_URL        = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_KEY_URL    = "https://openrouter.ai/api/v1/key"
OPENROUTER_CREDITS_URL= "https://openrouter.ai/api/v1/credits"

DEFAULT_LLM_MODEL = "metatron-qwen"
MAX_TOKENS = 8192
MAX_TOOL_LOOPS = 9   # max times AI can call tools per session
OLLAMA_TIMEOUT = 600
OPENROUTER_TIMEOUT = 300

# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are METATRON, an elite AI penetration testing assistant running on Parrot OS.
You are precise, technical, and direct. No fluff.

You have access to real tools. To use them, write tags in your response:

  [TOOL: nmap -sV 192.168.1.1]       → runs nmap or any CLI tool
  [SEARCH: CVE-2021-44228 exploit]   → searches the web via DuckDuckGo

Rules:
- Always analyze scan data thoroughly before suggesting exploits
- List vulnerabilities with: name, severity (critical/high/medium/low), port, service
- For each vulnerability, suggest a concrete fix
- If you need more information, use [SEARCH:] or [TOOL:]
- Format vulnerabilities clearly so they can be saved to a database
- Be specific about CVE IDs when you know them
- Always give a final risk rating: CRITICAL / HIGH / MEDIUM / LOW

Output format for vulnerabilities (use this exactly):
VULN: <name> | SEVERITY: <level> | PORT: <port> | SERVICE: <service>
DESC: <description>
FIX: <fix recommendation>

Output format for exploits:
EXPLOIT: <name> | TOOL: <tool> | PAYLOAD: <payload or description>
RESULT: <expected result>
NOTES: <any notes>

End your analysis with:
RISK_LEVEL: <CRITICAL|HIGH|MEDIUM|LOW>
SUMMARY: <2-3 sentence overall summary>
IMPORTANT: Never use markdown bold (**text**) or 
headers (## text). Plain text only. No exceptions.
IMPORTANT RULES FOR ACCURACY:
- nmap filtered or no-response means INCONCLUSIVE not vulnerable
- Never assert a server version without seeing it in scan output
- Never infer CVEs from guessed versions
- curl timeouts and HTTP_CODE=000 mean the host is unreachable not exploitable
- ab and stress tools are not Slowloris unless confirmed
- Only assign CRITICAL if there is direct evidence of exploitability
- If evidence is weak mark severity as LOW with note: unconfirmed"""


# ─────────────────────────────────────────────
# LLM API CALLS (Ollama or OpenRouter)
# ─────────────────────────────────────────────

def ask_llm(messages: list, max_tokens: int = MAX_TOKENS,
            temperature: float = 0.7) -> str:
    """Dispatch to the active provider (ollama or openrouter)."""
    provider = config.get("provider", "ollama")
    if provider == "openrouter":
        return ask_openrouter(messages, max_tokens, temperature)
    return ask_ollama(messages, max_tokens, temperature)


def ask_ollama(messages: list, max_tokens: int = MAX_TOKENS,
               temperature: float = 0.7) -> str:
    model = config.get("model", DEFAULT_LLM_MODEL)
    try:
        payload = {
            "model":  model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_p": 0.9,
            }
        }
        print(f"\n[*] Sending to Ollama ({model})...")
        resp = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        response = data.get("message", {}).get("content", "").strip()
        if not response:
            return "[!] Model returned empty response."
        return response
    except requests.exceptions.ConnectionError:
        return "[!] Cannot connect to Ollama. Is it running? Try: ollama serve"
    except requests.exceptions.Timeout:
        return "[!] Ollama timed out. Model may be loading, try again."
    except requests.exceptions.HTTPError as e:
        return f"[!] Ollama HTTP error: {e}"
    except Exception as e:
        return f"[!] Unexpected error: {e}"


def ask_openrouter(messages: list, max_tokens: int = MAX_TOKENS,
                   temperature: float = 0.7) -> str:
    api_key = config.get("api_key", "").strip()
    model   = config.get("model", "").strip()

    if not api_key:
        return ("[!] Aucune clé API OpenRouter configurée. "
                "Va dans Settings -> Clé API OpenRouter.")
    if not model:
        return ("[!] Aucun modèle OpenRouter sélectionné. "
                "Va dans Settings -> Modèle OpenRouter.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        print(f"\n[*] Sending to OpenRouter ({model})...")
        resp = requests.post(OPENROUTER_URL, json=payload,
                             headers=headers, timeout=OPENROUTER_TIMEOUT)

        if resp.status_code == 401:
            return "[!] Clé API OpenRouter invalide (401). Vérifie la clé dans Settings."
        if resp.status_code == 402:
            return "[!] Crédits OpenRouter insuffisants (402). Recharge ton compte."
        if resp.status_code == 404:
            return ("[!] Modèle OpenRouter introuvable (404). "
                    "Ressélectionne-le dans Settings -> Modèle OpenRouter.")
        if resp.status_code == 429:
            return "[!] Limite de débit atteinte (429). Réessaie plus tard."
        resp.raise_for_status()

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return "[!] OpenRouter: réponse sans choix (choices vide)."
        response = choices[0].get("message", {}).get("content", "").strip()
        if not response:
            return "[!] OpenRouter: le modèle a renvoyé une réponse vide."
        return response

    except requests.exceptions.ConnectionError:
        return "[!] Impossible de joindre OpenRouter. Vérifie ta connexion internet."
    except requests.exceptions.Timeout:
        return "[!] OpenRouter a mis trop de temps à répondre (timeout)."
    except requests.exceptions.HTTPError as e:
        return f"[!] OpenRouter HTTP error: {e}"
    except (json.JSONDecodeError, KeyError, TypeError):
        return "[!] OpenRouter: réponse illisible (JSON invalide)."
    except Exception as e:
        return f"[!] OpenRouter error inattendue: {e}"


# ─────────────────────────────────────────────
# OPENROUTER MODELS & CREDITS
# ─────────────────────────────────────────────

def _fetch_models_raw():
    """
    Low-level fetch of the OpenRouter models list.
    Returns (list_of_raw_model_dicts_or_None, error_str_or_None). No printing.
    """
    api_key = config.get("api_key", "").strip()
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    try:
        resp = requests.get(OPENROUTER_MODELS_URL, headers=headers, timeout=30)
        if resp.status_code == 401:
            return None, "unauthorized"
        if resp.status_code != 200:
            return None, f"http_{resp.status_code}"
        data = resp.json()
        return data.get("data", []), None
    except requests.exceptions.ConnectionError:
        return None, "network"
    except requests.exceptions.Timeout:
        return None, "timeout"
    except (requests.exceptions.RequestException,
            json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None, "error"


def fetch_openrouter_models() -> list:
    """
    Fetch available models from OpenRouter.
    Returns a list of dicts:
        {id, name, prompt_usd_per_m, completion_usd_per_m}
    Or an empty list on failure (with an error message printed).
    """
    raw, err = _fetch_models_raw()

    if err == "unauthorized":
        print("\033[91m[✗] Clé API invalide (401).\033[0m")
        return []
    if err == "network":
        print("\033[91m[✗] Impossible de joindre OpenRouter. Vérifie ta connexion.\033[0m")
        return []
    if err == "timeout":
        print("\033[91m[✗] Timeout lors de la récupération des modèles.\033[0m")
        return []
    if err:
        print(f"\033[91m[✗] Erreur lors de la récupération des modèles ({err}).\033[0m")
        return []

    def _to_per_million(val):
        try:
            v = float(val)
        except (TypeError, ValueError):
            return None
        if v < 0:      # OpenRouter uses -1 for "dynamic/varies" pricing
            return None
        return v * 1_000_000

    models = []
    for m in raw:
        mid  = m.get("id", "")
        name = m.get("name", mid)
        if not mid:
            continue
        pricing = m.get("pricing", {}) or {}
        models.append({
            "id":                    mid,
            "name":                  name,
            "prompt_usd_per_m":      _to_per_million(pricing.get("prompt")),
            "completion_usd_per_m":  _to_per_million(pricing.get("completion")),
        })

    def _cost_key(m):
        p = m["prompt_usd_per_m"]
        c = m["completion_usd_per_m"]
        p = float("inf") if p is None else p
        c = float("inf") if c is None else c
        return (p, c, m["name"].lower())

    models.sort(key=_cost_key)
    return models


def openrouter_model_exists(model_id: str) -> dict:
    """
    Check whether a model id exists on OpenRouter.
    Returns {exists: bool, error: str|None}. No printing.
    """
    result = {"exists": False, "error": None}
    model_id = (model_id or "").strip()
    if not model_id:
        result["error"] = "no_model"
        return result

    raw, err = _fetch_models_raw()
    if err:
        result["error"] = err
        return result

    if any(m.get("id") == model_id for m in raw):
        result["exists"] = True
    else:
        result["error"] = "not_found"
    return result


def get_openrouter_credits() -> dict:
    """
    Fetch remaining credits for the current OpenRouter key.
    Returns a dict:
        {remaining, usage, total_credits, is_free_tier, source, error}
    Primary: GET /api/v1/credits  ->  remaining = total_credits - total_usage.
    Fallback (403, non-management key): GET /api/v1/key for per-key info.
    """
    empty = {
        "remaining":     None,
        "usage":         None,
        "total_credits": None,
        "is_free_tier":  False,
        "source":        None,
        "error":         None,
    }

    api_key = config.get("api_key", "").strip()
    if not api_key:
        empty["error"] = "no_key"
        return empty

    headers = {"Authorization": f"Bearer {api_key}"}

    # 1) Account-wide balance (authoritative)
    try:
        resp = requests.get(OPENROUTER_CREDITS_URL, headers=headers, timeout=30)
    except requests.exceptions.ConnectionError:
        empty["error"] = "network"
        return empty
    except requests.exceptions.Timeout:
        empty["error"] = "timeout"
        return empty
    except requests.exceptions.RequestException:
        empty["error"] = "network"
        return empty

    if resp.status_code == 200:
        try:
            d = (resp.json() or {}).get("data", {})
            total = d.get("total_credits")
            used  = d.get("total_usage")
            if total is None or used is None:
                empty["error"] = "parse"
                return empty
            total_f = float(total)
            used_f  = float(used)
            empty.update({
                "remaining":     total_f - used_f,
                "usage":         used_f,
                "total_credits": total_f,
                "source":        "credits",
            })
            return empty
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            empty["error"] = "parse"
            return empty

    if resp.status_code == 401:
        empty["error"] = "unauthorized"
        return empty

    # 2) 403 = non-management key: fall back to per-key info
    if resp.status_code == 403:
        try:
            resp2 = requests.get(OPENROUTER_KEY_URL, headers=headers, timeout=30)
        except requests.exceptions.RequestException:
            empty["error"] = "network"
            return empty
        if resp2.status_code == 200:
            try:
                d = (resp2.json() or {}).get("data", {})
                remaining = d.get("limit_remaining")
                usage     = d.get("usage")
                if remaining is not None:
                    remaining = float(remaining)
                if usage is not None:
                    usage = float(usage)
                empty.update({
                    "remaining":    remaining,
                    "usage":        usage,
                    "is_free_tier": d.get("is_free_tier", False),
                    "source":       "key",
                })
                if remaining is None:
                    empty["error"] = "management_required"
                return empty
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                empty["error"] = "parse"
                return empty
        empty["error"] = "forbidden"
        return empty

    empty["error"] = f"http_{resp.status_code}"
    return empty


# ─────────────────────────────────────────────
# TOOL DISPATCH
# ─────────────────────────────────────────────

def extract_tool_calls(response: str) -> list:
    """
    Extract all [TOOL: ...] and [SEARCH: ...] tags from AI response.
    Returns list of tuples: [("TOOL", "nmap -sV x.x.x.x"), ("SEARCH", "CVE...")]
    """
    calls = []

    tool_matches   = re.findall(r'\[TOOL:\s*(.+?)\]',   response)
    search_matches = re.findall(r'\[SEARCH:\s*(.+?)\]', response)

    for m in tool_matches:
        calls.append(("TOOL", m.strip()))
    for m in search_matches:
        calls.append(("SEARCH", m.strip()))

    return calls

def summarize_tool_output(raw_output: str) -> str:
    """
    Compress raw tool output into security-relevant bullet points
    before injecting into the LLM context.
    Keeps context size manageable across rounds.
    """
    if len(raw_output) < 500:
        return raw_output

    try:
        summary = ask_llm([
    {"role": "system", "content": "You are a security data compressor. Extract only security-relevant facts. Return maximum 15 bullet points. Plain text only. No markdown."},
    {"role": "user", "content": f"Compress this tool output:\n{raw_output[:6000]}"} ],
            max_tokens=512, temperature=0.2)
        if summary.startswith("[!]"):
            return raw_output
        return summary if summary else raw_output
    except Exception:
        return raw_output
def run_tool_calls(calls: list) -> str:
    """
    Execute all tool/search calls and return combined results string.
    """
    if not calls:
        return ""

    results = ""
    for call_type, call_content in calls:
        print(f"\n  [DISPATCH] {call_type}: {call_content}")

        if call_type == "TOOL":
            output = run_tool_by_command(call_content)
        elif call_type == "SEARCH":
            output = handle_search_dispatch(call_content)
        else:
            output = f"[!] Unknown call type: {call_type}"

        compressed = summarize_tool_output(output.strip())
        results += f"\n[{call_type} RESULT: {call_content}]\n"
        results += "─" * 40 + "\n"
        results += compressed + "\n"

    return results


# ─────────────────────────────────────────────
# PARSER — extract structured data from AI output
# ─────────────────────────────────────────────
def _clean(line: str) -> str:
    return re.sub(r'\*+', '', line).strip()
def parse_vulnerabilities(response: str) -> list:
    """
    Parse VULN: lines from AI response into dicts.
    Returns list of vulnerability dicts ready for db.save_vulnerability()
    """
    vulns = []
    lines = response.splitlines()

    i = 0
    while i < len(lines):
        line = _clean(lines[i])
        if line.startswith("VULN:"):
            vuln = {
                "vuln_name":   "",
                "severity":    "medium",
                "port":        "",
                "service":     "",
                "description": "",
                "fix":         ""
            }

            # parse header line: VULN: name | SEVERITY: x | PORT: x | SERVICE: x
            parts = line.split("|")
            for part in parts:
                part = part.strip()
                if part.startswith("VULN:"):
                    vuln["vuln_name"] = part.replace("VULN:", "").strip()
                elif part.startswith("SEVERITY:"):
                    vuln["severity"] = part.replace("SEVERITY:", "").strip().lower()
                elif part.startswith("PORT:"):
                    vuln["port"] = part.replace("PORT:", "").strip()
                elif part.startswith("SERVICE:"):
                    vuln["service"] = part.replace("SERVICE:", "").strip()

            # look ahead for DESC: and FIX: lines
            j = i + 1
            while j < len(lines) and j <= i + 5:
                next_line = _clean(lines[j])
                if next_line.startswith(("VULN:", "EXPLOIT:", "RISK_LEVEL:", "SUMMARY:")):
                    break
                if next_line.startswith("DESC:"):
                    vuln["description"] = next_line.replace("DESC:", "").strip()
                elif next_line.startswith("FIX:"):
                    vuln["fix"] = next_line.replace("FIX:", "").strip()
                j += 1

            if vuln["vuln_name"]:
                vulns.append(vuln)

        i += 1

    return vulns


def parse_exploits(response: str) -> list:
    """
    Parse EXPLOIT: lines from AI response into dicts.
    Returns list of exploit dicts ready for db.save_exploit()
    """
    exploits = []
    lines = response.splitlines()

    i = 0
    while i < len(lines):
        line = _clean(lines[i])
        if line.startswith("EXPLOIT:"):
            exploit = {
                "exploit_name": "",
                "tool_used":    "",
                "payload":      "",
                "result":       "unknown",
                "notes":        ""
            }

            parts = line.split("|")
            for part in parts:
                part = part.strip()
                if part.startswith("EXPLOIT:"):
                    exploit["exploit_name"] = part.replace("EXPLOIT:", "").strip()
                elif part.startswith("TOOL:"):
                    exploit["tool_used"] = part.replace("TOOL:", "").strip()
                elif part.startswith("PAYLOAD:"):
                    exploit["payload"] = part.replace("PAYLOAD:", "").strip()

            j = i + 1
            while j < len(lines) and j <= i + 4:
                next_line = _clean(lines[j])
                if next_line.startswith(("VULN:", "EXPLOIT:", "RISK_LEVEL:", "SUMMARY:")):
                    break
                if next_line.startswith("RESULT:"):
                    exploit["result"] = next_line.replace("RESULT:", "").strip()
                elif next_line.startswith("NOTES:"):
                    exploit["notes"] = next_line.replace("NOTES:", "").strip()
                j += 1

            if exploit["exploit_name"]:
                exploits.append(exploit)

        i += 1

    return exploits


def parse_risk_level(response: str) -> str:
    """Extract RISK_LEVEL from AI response."""
    match = re.search(r'RISK_LEVEL:\s*(CRITICAL|HIGH|MEDIUM|LOW)', response, re.IGNORECASE)
    return match.group(1).upper() if match else "UNKNOWN"


def parse_summary(response: str) -> str:
    match = re.search(r'SUMMARY:\s*(.+)', response, re.IGNORECASE)
    return match.group(1).strip() if match else ""


# ─────────────────────────────────────────────
# MAIN ANALYSIS FUNCTION
# ─────────────────────────────────────────────

def analyse_target(target: str, raw_scan: str) -> dict:
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": f"""TARGET: {target}

RECON DATA:
{raw_scan}

Analyze this target completely. Use [TOOL:] or [SEARCH:] if you need more information.
List all vulnerabilities, fixes, and suggest exploits where applicable."""
        }
    ]

    final_response = ""

    for loop in range(MAX_TOOL_LOOPS):
        response = ask_llm(messages)

        print(f"\n{'─'*60}")
        print(f"[METATRON - Round {loop + 1}]")
        print(f"{'─'*60}")
        print(response)

        final_response = response

        tool_calls = extract_tool_calls(response)
        if not tool_calls:
            print("\n[*] No tool calls. Analysis complete.")
            break

        tool_results = run_tool_calls(tool_calls)

        # add assistant response and tool results as new messages
        messages.append({
            "role": "assistant",
            "content": response
        })
        messages.append({
            "role": "user",
            "content": f"""[TOOL RESULTS]
{tool_results}

Continue your analysis with this new information.
If analysis is complete, give the final RISK_LEVEL and SUMMARY."""
        })

    vulnerabilities = parse_vulnerabilities(final_response)
    exploits        = parse_exploits(final_response)
    risk_level      = parse_risk_level(final_response)
    summary         = parse_summary(final_response)

    print(f"\n[+] Parsed: {len(vulnerabilities)} vulns, {len(exploits)} exploits | Risk: {risk_level}")

    return {
        "full_response":   final_response,
        "vulnerabilities": vulnerabilities,
        "exploits":        exploits,
        "risk_level":      risk_level,
        "summary":         summary,
        "raw_scan":        raw_scan
    }
# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("[ llm.py test — direct AI query ]\n")

    provider = config.get("provider", "ollama")
    if provider == "openrouter":
        if not config.get("api_key", "").strip():
            print("[!] OpenRouter activé mais aucune clé API configurée.")
            exit(1)
        print("[+] Provider: OpenRouter")
    else:
        # test if ollama is reachable
        try:
            r = requests.get("http://localhost:11434", timeout=5)
            print("[+] Ollama is running.")
        except Exception:
            print("[!] Ollama not reachable. Run: ollama serve")
            exit(1)

    target = input("Test target: ").strip()
    test_scan = f"Test recon for {target} — nmap and whois data would appear here."
    result = analyse_target(target, test_scan)

    print(f"\nRisk Level : {result['risk_level']}")
    print(f"Summary    : {result['summary']}")
    print(f"Vulns found: {len(result['vulnerabilities'])}")
    print(f"Exploits   : {len(result['exploits'])}")
