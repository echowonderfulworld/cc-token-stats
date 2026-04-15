#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>
# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>

"""
cc-token-status — Claude Code usage dashboard in your menu bar.
https://github.com/jayson-jia-dev/cc-token-status
"""

VERSION = "1.2.1.0"
REPO_URL = "https://raw.githubusercontent.com/jayson-jia-dev/cc-token-status/main"

import json, os, glob, shlex, socket, subprocess, sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# ─── Config ──────────────────────────────────────────────────────

CONFIG_FILE = Path.home() / ".config" / "cc-token-stats" / "config.json"
ICLOUD_SYNC_DIR = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "cc-token-stats"

DEFAULTS = {
    "claude_dir": str(Path.home() / ".claude"),
    "sync_repo": "", "sync_mode": "auto",
    "subscription": 0, "subscription_label": "",
    "language": "auto", "machine_labels": {},
    "notifications": True,
    "auto_update": True,
}
NOTIFY_STATE_FILE = Path.home() / ".config" / "cc-token-stats" / ".notify_state.json"
SCAN_CACHE_FILE = Path.home() / ".config" / "cc-token-stats" / ".scan_cache.json"

def load_config():
    cfg = dict(DEFAULTS)
    if CONFIG_FILE.is_file():
        try:
            with open(CONFIG_FILE) as f: cfg.update(json.load(f))
        except Exception: pass
    for ek, ck in [("CC_STATS_CLAUDE_DIR","claude_dir"),("CC_STATS_SYNC_REPO","sync_repo"),("CC_STATS_LANG","language")]:
        if os.environ.get(ek): cfg[ck] = os.environ[ek]
    if os.environ.get("CC_STATS_SUBSCRIPTION"):
        try: cfg["subscription"] = float(os.environ["CC_STATS_SUBSCRIPTION"])
        except Exception: pass
    if cfg["language"] == "auto":
        try:
            out = subprocess.check_output(["defaults","read",".GlobalPreferences","AppleLanguages"], stderr=subprocess.DEVNULL, text=True)
            langs = [l.strip().strip('"').strip('",') for l in out.split("\n") if l.strip() and l.strip() not in ("(", ")")]
            if langs:
                fl = langs[0].lower().split("-")[0]  # "en-CN" → "en", "zh-Hans-CN" → "zh"
                supported = {"en","zh","es","fr","ja"}
                cfg["language"] = fl if fl in supported else "en"
            else:
                cfg["language"] = "en"
        except Exception: cfg["language"] = "en"
    return cfg

CFG = load_config()
LANG = CFG["language"]
MACHINE = socket.gethostname().split(".")[0]

# ─── i18n: 5 languages (EN, ZH, ES, FR, JA) ───────────────────
STRINGS = {
    "title":       {"en":"Claude Code Usage Dashboard","zh":"Claude Code 用量看板","es":"Panel de uso de Claude Code","fr":"Tableau de bord Claude Code","ja":"Claude Code 使用状況"},
    "today":       {"en":"Today","zh":"今日","es":"Hoy","fr":"Aujourd'hui","ja":"今日"},
    "live":        {"en":"live","zh":"实时","es":"en vivo","fr":"en direct","ja":"ライブ"},
    "synced":      {"en":"synced","zh":"同步","es":"sincronizado","fr":"synchronisé","ja":"同期"},
    "daily":       {"en":"Daily Details","zh":"每日明细","es":"Detalles diarios","fr":"Détails quotidiens","ja":"日別詳細"},
    "older":       {"en":"Older","zh":"更早","es":"Anteriores","fr":"Plus ancien","ja":"過去"},
    "total":       {"en":"Total","zh":"合计","es":"Total","fr":"Total","ja":"合計"},
    "models":      {"en":"Models","zh":"模型分布","es":"Modelos","fr":"Modèles","ja":"モデル"},
    "hours":       {"en":"Active Hours","zh":"活跃时段","es":"Horas activas","fr":"Heures actives","ja":"活動時間"},
    "projects":    {"en":"Top Projects","zh":"项目排行","es":"Proyectos","fr":"Projets","ja":"プロジェクト"},
    "saved":       {"en":"saved","zh":"省","es":"ahorrado","fr":"économisé","ja":"節約"},
    "msgs":        {"en":"msgs","zh":"条","es":"msgs","fr":"msgs","ja":"件"},
    "quit":        {"en":"Quit","zh":"退出","es":"Salir","fr":"Quitter","ja":"終了"},
    "refresh":     {"en":"Refresh","zh":"刷新","es":"Actualizar","fr":"Rafraîchir","ja":"更新"},
    "settings":    {"en":"Settings","zh":"设置","es":"Ajustes","fr":"Réglages","ja":"設定"},
    "notify":      {"en":"Notifications","zh":"通知提醒","es":"Notificaciones","fr":"Notifications","ja":"通知"},
    "login":       {"en":"Launch at Login","zh":"开机自启","es":"Inicio automático","fr":"Lancer au démarrage","ja":"ログイン時に起動"},
    "subscription":{"en":"Subscription","zh":"订阅方案","es":"Suscripción","fr":"Abonnement","ja":"サブスクリプション"},
    "limit_warn":  {"en":"Approaching usage limit","zh":"用量接近上限","es":"Acercándose al límite","fr":"Proche de la limite","ja":"上限に近づいています"},
    "limit_crit":  {"en":"Rate limit imminent!","zh":"即将限速！","es":"¡Límite inminente!","fr":"Limite imminente !","ja":"制限間近！"},
    "am":          {"en":"AM","zh":"早上","es":"Mañana","fr":"Matin","ja":"午前"},
    "pm":          {"en":"PM","zh":"下午","es":"Tarde","fr":"Après-midi","ja":"午後"},
    "eve":         {"en":"Eve","zh":"晚上","es":"Noche","fr":"Soir","ja":"夜"},
    "late":        {"en":"Late","zh":"凌晨","es":"Madrugada","fr":"Nuit","ja":"深夜"},
    "reset":       {"en":"Resets","zh":"重置","es":"Reinicia","fr":"Réinit.","ja":"リセット"},
    "api_equiv":   {"en":"API equiv","zh":"等价 API","es":"Equiv. API","fr":"Equiv. API","ja":"API相当"},
    "roi_note":    {"en":"{m:.1f}mo × ${s:.0f} = ${p:.0f} paid → {tc} ÷ ${p:.0f} = {x:.0f}x","zh":"{m:.1f}月 × ${s:.0f} = ${p:.0f} 已付 → {tc} ÷ ${p:.0f} = {x:.0f}x","es":"{m:.1f}m × ${s:.0f} = ${p:.0f} pagado → {tc} ÷ ${p:.0f} = {x:.0f}x","fr":"{m:.1f}m × ${s:.0f} = ${p:.0f} payé → {tc} ÷ ${p:.0f} = {x:.0f}x","ja":"{m:.1f}月 × ${s:.0f} = ${p:.0f} 支払 → {tc} ÷ ${p:.0f} = {x:.0f}x"},
    "auto_upd":    {"en":"Auto Update","zh":"自动更新","es":"Auto actualizar","fr":"Mise à jour auto","ja":"自動更新"},
    "input":       {"en":"Input","zh":"输入","es":"Entrada","fr":"Entrée","ja":"入力"},
    "output":      {"en":"Output","zh":"输出","es":"Salida","fr":"Sortie","ja":"出力"},
    "cache_w":     {"en":"Cache W","zh":"缓存写","es":"Caché E","fr":"Cache É","ja":"Cache書"},
    "cache_r":     {"en":"Cache R","zh":"缓存读","es":"Caché L","fr":"Cache L","ja":"Cache読"},
    "overview":    {"en":"Total","zh":"累计","es":"Total","fr":"Total","ja":"累計"},
    "devices":     {"en":"Devices","zh":"设备","es":"Dispositivos","fr":"Appareils","ja":"デバイス"},
    "details":     {"en":"Details","zh":"详情","es":"Detalles","fr":"Détails","ja":"詳細"},
    "level":       {"en":"Level","zh":"等级","es":"Nivel","fr":"Niveau","ja":"レベル"},
    "next_level":  {"en":"Next","zh":"下一级","es":"Siguiente","fr":"Suivant","ja":"次"},
    "no_token":    {"en":"⚠ No OAuth token — log in to Claude Code","zh":"⚠ 未找到 OAuth token — 请登录 Claude Code","es":"⚠ Sin token OAuth — inicie sesión en Claude Code","fr":"⚠ Pas de token OAuth — connectez-vous à Claude Code","ja":"⚠ OAuthトークンなし — Claude Codeにログイン"},
    "api_error":   {"en":"⚠ Cannot reach Anthropic API","zh":"⚠ 无法连接 Anthropic API","es":"⚠ No se puede conectar a la API","fr":"⚠ API Anthropic inaccessible","ja":"⚠ Anthropic APIに接続できません"},
    "first_use":   {"en":"Start a Claude Code session to see stats","zh":"启动 Claude Code 会话以查看统计","es":"Inicie una sesión de Claude Code","fr":"Démarrez une session Claude Code","ja":"Claude Codeセッションを開始してください"},
    "dim_usage":   {"en":"Usage","zh":"使用深度","es":"Uso","fr":"Utilisation","ja":"使用量"},
    "dim_context": {"en":"Context","zh":"上下文","es":"Contexto","fr":"Contexte","ja":"コンテキスト"},
    "dim_tools":   {"en":"Tools","zh":"工具生态","es":"Herramientas","fr":"Outils","ja":"ツール"},
    "dim_auto":    {"en":"Automation","zh":"自动化","es":"Automatización","fr":"Automatisation","ja":"自動化"},
    "dim_scale":   {"en":"Scale","zh":"规模化","es":"Escala","fr":"Échelle","ja":"スケール"},
    "burn_rate":   {"en":"~{0}min to rate limit","zh":"约{0}分钟后限速","es":"~{0}min al límite","fr":"~{0}min avant limite","ja":"約{0}分で制限"},
    "report":      {"en":"View Full Report","zh":"查看完整报告","es":"Ver informe","fr":"Voir le rapport","ja":"レポートを見る"},
    "trend_vs":    {"en":"vs 30d avg","zh":"对比 30 天均值","es":"vs prom. 30d","fr":"vs moy. 30j","ja":"30日平均比"},
    "extra":       {"en":"Extra","zh":"额外用量","es":"Extra","fr":"Extra","ja":"追加"},
}

def t(key):
    """Get translated string for current language."""
    s = STRINGS.get(key, {})
    return s.get(LANG, s.get("en", key))
CLAUDE_DIR = os.path.expanduser(CFG["claude_dir"])

def resolve_sync():
    mode = CFG.get("sync_mode", "auto")
    if mode == "off": return None, None
    if mode in ("icloud","auto"):
        r = Path.home()/"Library"/"Mobile Documents"/"com~apple~CloudDocs"
        if r.is_dir(): return str(ICLOUD_SYNC_DIR), "icloud"
    if mode in ("custom","auto"):
        c = CFG.get("sync_repo","")
        if c:
            e = os.path.expanduser(c)
            if os.path.isdir(e) or os.path.isdir(os.path.dirname(e)): return e, "custom"
    return None, None

SYNC_DIR, SYNC_TYPE = resolve_sync()

# ─── Pricing / Formatting ────────────────────────────────────────

# Per-model pricing (USD per 1M tokens) — https://docs.anthropic.com/en/docs/about-claude/models
# Using 1h cache write prices (Claude Code uses 1h cache ~90% of the time)
# Opus 4.0/4.1: $15/$75 (legacy)
# Sonnet 4.5/4.6: $3/$15
# Haiku 4.5: $1/$5
PRICING = {
    "opus_new":  {"input": 5,    "output": 25, "cache_write": 10,    "cache_read": 0.50},
    "opus_old":  {"input": 15,   "output": 75, "cache_write": 18.75, "cache_read": 1.50},
    "sonnet":    {"input": 3,    "output": 15, "cache_write": 6,     "cache_read": 0.30},
    "haiku":     {"input": 1,    "output": 5,  "cache_write": 2,     "cache_read": 0.10},
}
MODEL_SHORT = {
    "claude-opus-4-6":"Opus 4.6","claude-opus-4-5-20250918":"Opus 4.5",
    "claude-sonnet-4-6":"Sonnet 4.6","claude-sonnet-4-5-20250929":"Sonnet 4.5",
    "claude-haiku-4-5-20251001":"Haiku 4.5",
}

def dw(s):
    return sum(2 if ord(c)>0x2E7F else 1 for c in s)

def tk(n):
    if LANG == "zh":
        if n>=1e8: return f"{n/1e8:.2f} 亿"
        if n>=1e4: return f"{n/1e4:.1f} 万"
    elif LANG == "ja":
        if n>=1e8: return f"{n/1e8:.2f} 億"
        if n>=1e4: return f"{n/1e4:.1f} 万"
    else:
        if n>=1e9: return f"{n/1e9:.2f}B"
        if n>=1e6: return f"{n/1e6:.1f}M"
        if n>=1e3: return f"{n/1e3:.1f}K"
    return f"{n:,}"

def fc(n):
    return f"${n:,.0f}" if n>=10000 else f"${n:,.2f}"

def tier(m):
    ml = m.lower()
    if "opus" in ml:
        # Only legacy Opus (4.0/4.1) uses old pricing; all newer default to opus_new
        if "4-0" in m or "4-1" in m or "4.0" in ml or "4.1" in ml:
            return "opus_old"
        return "opus_new"
    if "haiku" in ml: return "haiku"
    return "sonnet"

# ─── User Level System ────────────────────────────────────────────

LEVELS = [
    (0,  "🌑", "Starter",      "练气期"),
    (13, "🌒", "Planner",      "筑基期"),
    (31, "🌓", "Engineer",     "金丹期"),
    (51, "🌔", "Integrator",   "元婴期"),
    (71, "🌕", "Architect",    "化神期"),
    (86, "👑", "Orchestrator", "大乘期"),
]

LEVEL_CACHE_FILE = Path.home() / ".config" / "cc-token-stats" / ".level_cache.json"

def calc_user_level():
    """Calculate user level from local data. Returns (score, level_idx, details).
    Cached for 24 hours since level changes very slowly."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        if LEVEL_CACHE_FILE.is_file():
            _lc = json.loads(LEVEL_CACHE_FILE.read_text())
            if _lc.get("date") == today_str and _lc.get("ver") == VERSION:
                return _lc["score"], _lc["level"], _lc["details"]
    except Exception: pass

    import glob as _g
    _home = os.path.expanduser("~")
    _cd = os.path.join(_home, ".claude")
    details = {}

    # 1. Usage maturity (20pts): median session length + density
    _sessions = []
    _dates = set()
    for jf in _g.glob(os.path.join(_cd, "projects/*/*.jsonl")):
        cnt = 0
        try:
            with open(jf) as f:
                for line in f:
                    d = json.loads(line)
                    if d.get("type") == "assistant": cnt += 1
                    ts = d.get("timestamp", "")
                    if ts: _dates.add(ts[:10])
        except Exception: pass
        if cnt > 0: _sessions.append(cnt)
    _sessions.sort()
    med = _sessions[len(_sessions)//2] if _sessions else 0
    _ad = len(_dates)
    if _dates:
        _fd, _ld = min(_dates), max(_dates)
        _td = (datetime.strptime(_ld, "%Y-%m-%d") - datetime.strptime(_fd, "%Y-%m-%d")).days + 1
    else:
        _td = 1
    _dens = _ad / max(_td, 1)
    s1 = 16 if med >= 80 else 10 if med >= 50 else 6 if med >= 30 else 2 if med >= 10 else 0
    s1 += 4 if _dens >= 0.6 else 2 if _dens >= 0.4 else 0
    s1 = min(s1, 20)
    details["usage"] = s1

    # 2. Context management (20pts)
    s2 = 0
    _cm = os.path.join(_cd, "CLAUDE.md")
    if os.path.isfile(_cm):
        with open(_cm) as _f: s2 += 4 if len(_f.readlines()) > 50 else 2
    _pcm = _g.glob(os.path.join(_home, "Downloads/*/CLAUDE.md"))
    s2 += 4 if len(_pcm) >= 3 else 2 if len(_pcm) >= 1 else 0
    _md = os.path.join(_cd, "projects/-Users-" + os.path.basename(_home), "memory")
    _mf = [f for f in _g.glob(os.path.join(_md, "*.md")) if "MEMORY.md" not in f] if os.path.isdir(_md) else []
    _sm = [f for f in _mf if os.path.getsize(f) > 200]
    _mr = any((datetime.now().timestamp() - os.path.getmtime(f)) < 7*86400 for f in _sm) if _sm else False
    s2 += 4 if len(_sm) >= 5 and _mr else 2 if len(_sm) >= 2 else 0
    _rd = [os.path.join(_cd, "rules"), os.path.join(_cd, ".claude/rules")]
    _rc = sum(len(_g.glob(os.path.join(d, "*"))) for d in _rd if os.path.isdir(d))
    if _rc > 0: s2 += 4
    s2 = min(s2, 20)
    details["context"] = s2

    # 3. Tool ecosystem (20pts)
    s3 = 0
    _wm = {"zentao","gitlab","jira","confluence","jenkins"}
    _pm = 0; _mc = 0
    _mf2 = os.path.join(_cd, "mcp.json")
    if os.path.isfile(_mf2):
        try:
            with open(_mf2) as _f: _md2 = json.load(_f)
            _svs = _md2.get("mcpServers", {})
            _mc = len(_svs)
            _pm = sum(1 for n in _svs if not any(w in n.lower() for w in _wm))
        except Exception: pass
    _em = _pm + (_mc - _pm) * 0.5
    s3 += 14 if _em >= 4 else 10 if _em >= 3 else 7 if _em >= 2 else 4 if _em >= 1 else 0
    _pl = _g.glob(os.path.join(_cd, "plugins/cache/*/"))
    s3 += 4 if len(_pl) >= 3 else 2 if len(_pl) >= 1 else 0
    s3 = min(s3, 20)
    details["tools"] = s3

    # 4. Automation (20pts) — self-built weighted
    _fp = ("gsd","jjx","rn-","claude-","commit-","code-review","pr-review","understand","smart-",
           "mem-","workflow-","using-","test-","systematic","verification","receiving-","requesting-",
           "writing-","log-","dispatching","executing-","finishing-","subagent","brainstorming","planning-")
    _cmddir = os.path.join(_cd, "commands")
    _ac = [f for f in os.listdir(_cmddir) if f.endswith(".md")] if os.path.isdir(_cmddir) else []
    _sc2 = [c for c in _ac if not any(c.startswith(p) for p in _fp)]
    _skdir = os.path.join(_cd, "skills")
    _ask = os.listdir(_skdir) if os.path.isdir(_skdir) else []
    _ssk = [s for s in _ask if not any(s.startswith(p) for p in _fp)]
    _hc = 0
    _sf = os.path.join(_cd, "settings.json")
    if os.path.isfile(_sf):
        try:
            with open(_sf) as _f: _sd = json.load(_f)
            for v in _sd.get("hooks", {}).values():
                if isinstance(v, list): _hc += len(v)
        except Exception: pass
    _raw = 0
    _nsc = len(_sc2)
    _raw += 14 if _nsc >= 10 else 10 if _nsc >= 5 else 6 if _nsc >= 3 else 3 if _nsc >= 1 else 0
    _raw += 6 if _hc >= 3 else 3 if _hc >= 1 else 0
    _raw = min(_raw, 20)
    _ta = len(_ac) + len(_ask)
    _sa = len(_sc2) + len(_ssk)
    _sr = _sa / max(_ta, 1)
    s4 = int(_raw * (0.3 + 0.7 * _sr))
    s4 = min(s4, 20)
    details["automation"] = s4

    # 5. Scale (20pts) — substantial projects only
    s5 = 0
    _pdir = os.path.join(_cd, "projects")
    _ps = {}
    for pd in _g.glob(os.path.join(_pdir, "*")):
        if os.path.isdir(pd):
            _ps[os.path.basename(pd)] = len(_g.glob(os.path.join(pd, "*.jsonl")))
    _sp = sum(1 for c in _ps.values() if c >= 5)
    s5 += 10 if _sp >= 8 else 7 if _sp >= 5 else 4 if _sp >= 3 else 2 if _sp >= 1 else 0
    # worktree detection (simplified)
    try:
        _dl = Path(_home) / "Downloads"
        if any(_dl.glob("*/.git/worktrees")) or any(_dl.glob("*/*/.git/worktrees")):
            s5 += 4
    except Exception: pass
    s5 += 4 if _td >= 90 else 3 if _td >= 60 else 2 if _td >= 30 else 1 if _td >= 14 else 0
    s5 = min(s5, 20)
    details["scale"] = s5

    total = s1 + s2 + s3 + s4 + s5
    lvl = 0
    for i, (threshold, *_) in enumerate(LEVELS):
        if total >= threshold: lvl = i
    try:
        LEVEL_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        LEVEL_CACHE_FILE.write_text(json.dumps({"date": today_str, "ver": VERSION, "score": total, "level": lvl, "details": details}))
    except Exception: pass
    return total, lvl, details

def mlabel(h):
    labels = CFG.get("machine_labels",{})
    if h in labels: return labels[h]
    # Truncate long hostnames
    return h[:16] + "…" if len(h) > 16 else h

def bar(val, maxval, width=12):
    """Render a mini bar chart — ▰▱ works in both dark and light mode."""
    if maxval <= 0: return "▱" * width
    filled = round(val / maxval * width)
    return "▰" * filled + "▱" * (width - filled)

# ─── Notifications ───────────────────────────────────────────────

def _notify(title, msg):
    """Send a macOS notification."""
    try:
        subprocess.run([
            "osascript", "-e",
            f'display notification "{msg}" with title "{title}" subtitle "cc-token-status"'
        ], timeout=5)
    except Exception: pass

def check_and_notify(usage):
    """Send macOS notification when limits cross 80% or 95%. Once per threshold per reset cycle."""
    if not CFG.get("notifications", True) or not usage:
        return
    # Load state
    state = {}
    try:
        if NOTIFY_STATE_FILE.is_file():
            state = json.loads(NOTIFY_STATE_FILE.read_text())
    except Exception: pass

    thresholds = [80, 95]
    checks = [
        ("Session", "five_hour"),
        ("Weekly", "seven_day"),
        ("Sonnet", "seven_day_sonnet"),
        ("Opus", "seven_day_opus"),
    ]
    current_keys = set()
    changed = False
    for name, key in checks:
        obj = usage.get(key)
        if not obj or obj.get("utilization") is None: continue
        util = obj["utilization"]
        # Truncate reset time to minute — avoid microsecond differences creating duplicate keys
        reset_raw = obj.get("resets_at", "")
        reset = reset_raw[:16] if reset_raw else ""  # "2026-04-11T06:00"
        for thresh in thresholds:
            state_key = f"{key}_{thresh}_{reset}"
            current_keys.add(state_key)
            if util >= thresh and state_key not in state:
                if thresh >= 95:
                    _notify(f"⛔ {name} {util:.0f}%", t("limit_crit"))
                else:
                    _notify(f"⚠️ {name} {util:.0f}%", t("limit_warn"))
                state[state_key] = datetime.now().isoformat()
                changed = True

    # Burn rate warning: if session >50% and will hit 100% within 30 min at current pace
    fh = usage.get("five_hour")
    if fh and fh.get("utilization") is not None and fh["utilization"] >= 50:
        try:
            reset_str = fh.get("resets_at", "")
            if reset_str:
                rt = datetime.fromisoformat(reset_str.replace("Z", "+00:00"))
                now_aware = datetime.now().astimezone()
                remaining_min = (rt - now_aware).total_seconds() / 60
                util = fh["utilization"]
                # Estimate time to 100%: if util% used in (300-remaining) minutes,
                # rate = util / elapsed, time_to_100 = (100-util) / rate
                elapsed_min = max(300 - remaining_min, 1)  # 5h = 300min
                rate = util / elapsed_min  # % per minute
                if rate > 0:
                    min_to_full = (100 - util) / rate
                    burn_key = f"burn_{reset_str[:16]}"
                    if min_to_full <= 30 and burn_key not in state:
                        _notify(
                            f"🔥 Session {util:.0f}%",
                            t("burn_rate").format(int(min_to_full))
                        )
                        state[burn_key] = datetime.now().isoformat()
                        changed = True
                    current_keys.add(burn_key)
        except Exception: pass

    # Cleanup: remove entries whose reset time has passed (not just missing from current check)
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
    # For non-burn keys: only remove if the reset time in the key is in the past
    for k in list(state.keys()):
        if k in current_keys: continue
        # Extract reset timestamp from key (last 16 chars after last _)
        parts = k.rsplit("_", 1)
        if len(parts) == 2 and len(parts[1]) >= 16:
            if parts[1] < now_str:
                del state[k]
                changed = True
        elif k.startswith("burn_") and k not in current_keys:
            # Burn key from past cycle
            burn_reset = k[5:]  # "burn_2026-04-11T06:00"
            if burn_reset < now_str:
                del state[k]
                changed = True

    if changed:
        try:
            NOTIFY_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            NOTIFY_STATE_FILE.write_text(json.dumps(state))
            NOTIFY_STATE_FILE.chmod(0o600)
        except Exception: pass

# ─── Auto-update (once per day, silent) ──────────────────────────

UPDATE_CHECK_FILE = Path.home() / ".config" / "cc-token-stats" / ".last_update_check"

def auto_update():
    """Check for updates once per day. Downloads new version silently."""
    if not CFG.get("auto_update", True):
        return
    try:
        # Check at most once per day
        if UPDATE_CHECK_FILE.is_file():
            last = float(UPDATE_CHECK_FILE.read_text().strip())
            if datetime.now().timestamp() - last < 86400:  # 24h
                return
    except Exception: pass

    try:
        import urllib.request, hashlib
        # Fetch remote version line
        req = urllib.request.Request(f"{REPO_URL}/cc-token-stats.5m.py",
                                     headers={"Range": "bytes=0-500"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            head = resp.read(500).decode("utf-8", errors="ignore")
        # Parse VERSION from remote
        for line in head.splitlines():
            if line.startswith("VERSION"):
                remote_ver = line.split('"')[1]
                if remote_ver != VERSION:
                    # Resolve plugin path
                    plugin_path = None
                    try:
                        plugin_dir = subprocess.run(
                            ["defaults", "read", "com.ameba.SwiftBar", "PluginDirectory"],
                            capture_output=True, text=True, timeout=3
                        ).stdout.strip()
                        if plugin_dir:
                            plugin_path = os.path.join(plugin_dir, "cc-token-stats.5m.py")
                    except Exception: pass
                    if not plugin_path:
                        plugin_path = os.path.join(
                            str(Path.home()), "Library", "Application Support",
                            "SwiftBar", "plugins", "cc-token-stats.5m.py")

                    # Download to temp file
                    tmp_path = plugin_path + ".tmp"
                    urllib.request.urlretrieve(f"{REPO_URL}/cc-token-stats.5m.py", tmp_path)

                    # Verify SHA256 checksum
                    with open(tmp_path, "rb") as f:
                        actual_hash = hashlib.sha256(f.read()).hexdigest()
                    with urllib.request.urlopen(f"{REPO_URL}/checksum.sha256", timeout=5) as resp:
                        expected_hash = resp.read().decode().strip().split()[0]
                    if actual_hash != expected_hash:
                        try: os.remove(tmp_path)
                        except Exception: pass
                        return  # checksum mismatch — don't record, retry next cycle

                    os.chmod(tmp_path, 0o755)
                    os.rename(tmp_path, plugin_path)  # atomic on same filesystem
                break

        # Record check time — only reached on success or same-version
        UPDATE_CHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
        UPDATE_CHECK_FILE.write_text(str(datetime.now().timestamp()))
        UPDATE_CHECK_FILE.chmod(0o600)
    except Exception: pass

# ─── Usage API (official rate limits) ────────────────────────────

def _detect_macos_proxy():
    """Read HTTPS proxy from macOS system settings via scutil.
    Returns 'http://host:port' or None."""
    try:
        out = subprocess.run(["scutil", "--proxy"], capture_output=True, text=True, timeout=3)
        d = {}
        for line in out.stdout.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                d[k.strip()] = v.strip()
        if d.get("HTTPSEnable") == "1" and d.get("HTTPSProxy") and d.get("HTTPSPort"):
            return f"http://{d['HTTPSProxy']}:{d['HTTPSPort']}"
        if d.get("HTTPEnable") == "1" and d.get("HTTPProxy") and d.get("HTTPPort"):
            return f"http://{d['HTTPProxy']}:{d['HTTPPort']}"
    except Exception:
        pass
    return None

def get_oauth_token():
    """Read Claude Code OAuth token from macOS Keychain."""
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", "Claude Code-credentials", "-g"],
            capture_output=True, text=True, timeout=5
        )
        # Extract password field from stderr (security outputs it there)
        for line in out.stderr.splitlines():
            if line.startswith("password: "):
                pw = line[len("password: "):]
                if pw.startswith('"') and pw.endswith('"'):
                    pw = pw[1:-1]
                creds = json.loads(pw)
                oauth = creds.get("claudeAiOauth", {})
                return oauth.get("accessToken"), oauth.get("subscriptionType"), oauth.get("rateLimitTier")
    except Exception:
        pass
    return None, None, None

def fetch_usage():
    """Fetch official plan usage from Anthropic API. Returns (data, error_hint).
    error_hint is None on success, or a short string describing the failure."""
    token, sub_type, tier = get_oauth_token()
    if not token:
        return None, "no_token"
    try:
        import urllib.request, urllib.error
        url = "https://api.anthropic.com/api/oauth/usage"
        headers = {
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
            "Content-Type": "application/json",
        }
        # Try 1: default behavior (auto-detects env vars + macOS system proxy)
        # Try 2: if that fails, read macOS system proxy via scutil (SwiftBar
        #         strips env vars and _scproxy may not work in its sandbox)
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, headers=headers)
                if attempt == 0:
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read())
                else:
                    proxy = _detect_macos_proxy()
                    if not proxy:
                        break  # no system proxy found, don't retry
                    handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
                    opener = urllib.request.build_opener(handler)
                    with opener.open(req, timeout=10) as resp:
                        data = json.loads(resp.read())
                data["_sub_type"] = sub_type
                data["_tier"] = tier
                return data, None
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    # Pass Retry-After hint if server provides one
                    retry_after = e.headers.get("Retry-After") if e.headers else None
                    return None, f"rate_limit:{retry_after}" if retry_after else "rate_limit"
                if attempt == 0:
                    continue
            except Exception:
                if attempt == 0:
                    continue
        return None, "api_error"
    except Exception:
        return None, "api_error"

USAGE_CACHE = Path.home() / ".config" / "cc-token-stats" / ".usage_cache.json"
BACKOFF_STATE_FILE = Path.home() / ".config" / "cc-token-stats" / ".backoff_state.json"

def _load_backoff():
    try:
        if BACKOFF_STATE_FILE.is_file():
            s = json.loads(BACKOFF_STATE_FILE.read_text())
            return s.get("until", 0), s.get("count", 0)
    except Exception: pass
    return 0, 0

def _save_backoff(until_ts, count):
    try:
        BACKOFF_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        BACKOFF_STATE_FILE.write_text(json.dumps({"until": until_ts, "count": count}))
    except Exception: pass

def _clear_backoff():
    try: BACKOFF_STATE_FILE.unlink(missing_ok=True)
    except Exception: pass

def _read_synced_usage():
    """Try to read fresh usage data from another machine via sync directory."""
    if not SYNC_DIR:
        return None
    try:
        shared = os.path.join(SYNC_DIR, "shared_usage.json")
        if not os.path.isfile(shared):
            return None
        data = json.loads(Path(shared).read_text())
        return data
    except Exception:
        return None

def _write_synced_usage(data):
    """Share fresh usage data for other machines via sync directory."""
    if not SYNC_DIR:
        return
    try:
        shared = os.path.join(SYNC_DIR, "shared_usage.json")
        os.makedirs(os.path.dirname(shared), exist_ok=True)
        Path(shared).write_text(json.dumps(data))
    except Exception:
        pass

def get_usage():
    """Get usage with multi-layer cache: local → synced → API (with backoff)."""
    now_ts = datetime.now().timestamp()

    # Layer 1: local cache (< 9 minutes)
    if USAGE_CACHE.is_file():
        try:
            cached = json.loads(USAGE_CACHE.read_text())
            age = now_ts - cached.get("_ts", 0)
            if age < 540:  # 9 minutes
                return cached, None
        except Exception: pass

    # Layer 2: synced usage from another machine (< 9 minutes)
    synced = _read_synced_usage()
    if synced:
        synced_age = now_ts - synced.get("_ts", 0)
        if synced_age < 540:
            # Save to local cache so we don't re-read sync dir every run
            try:
                USAGE_CACHE.parent.mkdir(parents=True, exist_ok=True)
                USAGE_CACHE.write_text(json.dumps(synced))
                USAGE_CACHE.chmod(0o600)
            except Exception: pass
            return synced, None

    # Layer 3: check backoff — if in cooldown, use whatever cache we have
    backoff_until, backoff_count = _load_backoff()
    if backoff_until > now_ts:
        return _best_cached(now_ts), None  # silent — data is just slightly stale

    # Layer 4: fetch from API
    data, err = fetch_usage()
    if data:
        data["_ts"] = now_ts
        try:
            USAGE_CACHE.parent.mkdir(parents=True, exist_ok=True)
            USAGE_CACHE.write_text(json.dumps(data))
            USAGE_CACHE.chmod(0o600)
        except Exception: pass
        _write_synced_usage(data)  # share with other machines
        _clear_backoff()
        return data, None

    # On 429: backoff (10m → 20m → 40m → 60m cap), respect Retry-After
    if err and err.startswith("rate_limit"):
        new_count = backoff_count + 1
        retry_after_secs = None
        if ":" in err:
            try: retry_after_secs = int(err.split(":")[1])
            except (ValueError, IndexError): pass
        delay = min(retry_after_secs, 3600) if retry_after_secs and retry_after_secs > 0 \
            else min(600 * (2 ** (new_count - 1)), 3600)
        _save_backoff(now_ts + delay, new_count)
        return _best_cached(now_ts), None  # silent fallback

    # Other errors (no_token, api_error): only show if no data at all
    cached = _best_cached(now_ts)
    if cached:
        return cached, None
    return None, err

def _best_cached(now_ts):
    """Return best available cached data (local or synced), up to 2h stale."""
    for source in [USAGE_CACHE]:
        try:
            if source.is_file():
                data = json.loads(source.read_text())
                if now_ts - data.get("_ts", 0) < 7200:
                    return data
        except Exception: pass
    synced = _read_synced_usage()
    if synced and now_ts - synced.get("_ts", 0) < 7200:
        return synced
    return None

# ─── Data ────────────────────────────────────────────────────────

def _file_fingerprints(base):
    """Collect {path: mtime} for all JSONL files under base."""
    fps = {}
    if not os.path.isdir(base):
        return fps
    for pd in glob.glob(os.path.join(base, "*")):
        if not os.path.isdir(pd): continue
        for jf in glob.glob(os.path.join(pd, "*.jsonl")):
            try: fps[jf] = os.path.getmtime(jf)
            except Exception: pass
    return fps

def _load_scan_cache(base, today_str):
    """Return cached scan result if all files unchanged and same day."""
    try:
        if not SCAN_CACHE_FILE.is_file():
            return None
        cache = json.loads(SCAN_CACHE_FILE.read_text())
        if cache.get("date") != today_str:
            return None  # day boundary crossed, need re-scan for today stats
        current_fps = _file_fingerprints(base)
        cached_fps = cache.get("file_mtimes", {})
        if current_fps == cached_fps:
            # Restore defaultdicts from cached plain dicts
            s = cache["result"]
            s["daily"] = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "msgs": 0, "sessions": 0}, s.get("daily", {}))
            s["hourly"] = defaultdict(int, {int(k): v for k, v in s.get("hourly", {}).items()})
            s["projects"] = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "msgs": 0}, s.get("projects", {}))
            s.setdefault("daily_models", {})
            s.setdefault("daily_hourly", {})
            s.setdefault("sessions_by_day", {})
            return s
    except Exception: pass
    return None

def _save_scan_cache(base, today_str, s):
    """Save scan result and file fingerprints to cache."""
    try:
        cache = {
            "date": today_str,
            "file_mtimes": _file_fingerprints(base),
            "result": {k: (dict(v) if isinstance(v, defaultdict) else v) for k, v in s.items()},
        }
        SCAN_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCAN_CACHE_FILE.write_text(json.dumps(cache))
    except Exception: pass

def scan():
    base = os.path.join(CLAUDE_DIR, "projects")
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Incremental: return cached result if no files changed
    cached = _load_scan_cache(base, today_str)
    if cached is not None:
        return cached

    now_dt = datetime.now()
    cutoff_5h = now_dt - timedelta(hours=5)
    cutoff_7d = now_dt - timedelta(days=7)

    s = {
        "machine": MACHINE, "sessions": 0,
        "inp": 0, "out": 0, "cw": 0, "cr": 0,
        "cost": 0.0, "d_min": None, "d_max": None,
        "models": {},
        # Today
        "today": {"tokens": 0, "cost": 0.0, "msgs": 0, "inp": 0, "out": 0, "cw": 0, "cr": 0, "models": {}},
        # Rolling windows
        "window_5h": {"tokens": 0, "cost": 0.0, "msgs": 0, "out": 0},
        "window_7d": {"tokens": 0, "cost": 0.0, "msgs": 0, "out": 0},
        # Daily (ALL dates, collected dynamically)
        "daily": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "msgs": 0, "sessions": 0}),
        # Hourly (24h)
        "hourly": defaultdict(int),
        # Per-project
        "projects": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "msgs": 0}),
        # v3: per-day per-model breakdown
        "daily_models": defaultdict(lambda: defaultdict(lambda: {"cost": 0.0, "msgs": 0})),
        # v3: per-day per-hour (for heatmap)
        "daily_hourly": defaultdict(lambda: defaultdict(int)),
        # v3: session-level detail per day
        "sessions_by_day": defaultdict(list),
    }

    if not os.path.isdir(base):
        return s

    for pd in glob.glob(os.path.join(base, "*")):
        if not os.path.isdir(pd): continue
        proj = os.path.basename(pd)
        # Extract readable project name
        parts = [p for p in proj.replace("-", "/").split("/") if p]
        proj_name = parts[-1] if parts else proj[:20]

        for jf in glob.glob(os.path.join(pd, "*.jsonl")):
            has = False
            sess_cost = 0.0; sess_msgs = 0; sess_first_date = None; sess_model_counts = {}
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            d = json.loads(line)
                            if d.get("type") != "assistant": continue
                            msg = d.get("message", {})
                            if not isinstance(msg, dict): continue
                            u = msg.get("usage")
                            if not u: continue
                            i, o, w, r = u.get("input_tokens", 0), u.get("output_tokens", 0), u.get("cache_creation_input_tokens", 0), u.get("cache_read_input_tokens", 0)
                            s["inp"] += i; s["out"] += o; s["cw"] += w; s["cr"] += r; has = True
                            total_t = i + o + w + r
                            m = msg.get("model", "")
                            p = PRICING.get(tier(m), PRICING["sonnet"])
                            mc = (i * p["input"] + o * p["output"] + w * p["cache_write"] + r * p["cache_read"]) / 1e6
                            s["cost"] += mc
                            # v3: session-level tracking
                            sess_cost += mc; sess_msgs += 1
                            if m and m != "<synthetic>":
                                sess_model_counts[m] = sess_model_counts.get(m, 0) + 1

                            # Model breakdown
                            if m and m != "<synthetic>":
                                if m not in s["models"]: s["models"][m] = {"msgs": 0, "tokens": 0, "cost": 0.0}
                                s["models"][m]["msgs"] += 1; s["models"][m]["tokens"] += total_t; s["models"][m]["cost"] += mc

                            # Per-message date
                            ts_str = d.get("timestamp", "")
                            msg_date = ts_str[:10] if ts_str and len(ts_str) >= 10 else None

                            # Today
                            if msg_date == today_str:
                                td = s["today"]
                                td["tokens"] += total_t; td["cost"] += mc; td["msgs"] += 1
                                td["inp"] += i; td["out"] += o; td["cw"] += w; td["cr"] += r
                                if m and m != "<synthetic>":
                                    if m not in td["models"]: td["models"][m] = {"msgs": 0, "cost": 0.0}
                                    td["models"][m]["msgs"] += 1; td["models"][m]["cost"] += mc

                            # v3: track first message date for session
                            if msg_date and not sess_first_date:
                                sess_first_date = msg_date

                            # Daily (all dates) + date range from message timestamps
                            if msg_date:
                                dd = s["daily"][msg_date]
                                dd["tokens"] += total_t; dd["cost"] += mc; dd["msgs"] += 1
                                if not s["d_min"] or msg_date < s["d_min"]: s["d_min"] = msg_date
                                if not s["d_max"] or msg_date > s["d_max"]: s["d_max"] = msg_date
                                # v3: per-day per-model
                                if m and m != "<synthetic>":
                                    short_m = MODEL_SHORT.get(m, m.split("-")[-1] if "-" in m else m[:15])
                                    dm = s["daily_models"][msg_date][short_m]
                                    dm["cost"] += mc; dm["msgs"] += 1

                            # Hourly (convert to local timezone)
                            if ts_str:
                                try:
                                    local_dt = datetime.fromisoformat(ts_str.replace("Z","+00:00")).astimezone()
                                    local_h = local_dt.hour
                                    s["hourly"][local_h] += 1
                                    # v3: per-day per-hour for heatmap
                                    if msg_date:
                                        local_weekday = local_dt.weekday()  # 0=Mon, 6=Sun
                                        s["daily_hourly"][local_weekday][local_h] += 1
                                except Exception: pass

                            # Rolling windows (5h / 7d)
                            if ts_str:
                                try:
                                    msg_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
                                    if msg_dt >= cutoff_5h:
                                        s["window_5h"]["tokens"] += total_t; s["window_5h"]["cost"] += mc
                                        s["window_5h"]["msgs"] += 1; s["window_5h"]["out"] += o
                                    if msg_dt >= cutoff_7d:
                                        s["window_7d"]["tokens"] += total_t; s["window_7d"]["cost"] += mc
                                        s["window_7d"]["msgs"] += 1; s["window_7d"]["out"] += o
                                except Exception: pass

                            # Project
                            s["projects"][proj_name]["tokens"] += total_t
                            s["projects"][proj_name]["cost"] += mc
                            s["projects"][proj_name]["msgs"] += 1

                        except Exception: pass
                if has:
                    s["sessions"] += 1
                    # v3: record session detail + count sessions per day
                    if sess_first_date:
                        s["daily"][sess_first_date]["sessions"] = s["daily"][sess_first_date].get("sessions", 0) + 1
                        sess_list = s["sessions_by_day"][sess_first_date]
                        if len(sess_list) < 30:  # cap per day
                            dom_model = max(sess_model_counts, key=sess_model_counts.get) if sess_model_counts else ""
                            short_dm = MODEL_SHORT.get(dom_model, dom_model.split("-")[-1] if "-" in dom_model else dom_model[:15])
                            sess_list.append({"project": proj_name, "cost": round(sess_cost, 2),
                                              "msgs": sess_msgs, "model": short_dm})
            except Exception: pass

    _save_scan_cache(base, today_str, s)
    return s

def save_sync(st):
    if not SYNC_DIR: return
    d = os.path.join(SYNC_DIR, "machines", MACHINE)
    try:
        os.makedirs(d, exist_ok=True)
        mb = {m: {**v, "cost": round(v["cost"], 2)} for m, v in st.get("models", {}).items()}
        # Daily: {date: {cost, msgs, tokens}}
        daily = {k: {"cost": round(v["cost"], 2), "msgs": v["msgs"], "tokens": v["tokens"]}
                 for k, v in st.get("daily", {}).items() if v.get("cost", 0) > 0 or v.get("msgs", 0) > 0}
        # Hourly: {hour: count}
        hourly = {str(k): v for k, v in st.get("hourly", {}).items() if v > 0}
        # Projects: {name: {cost, msgs, tokens}}
        projects = {k: {"cost": round(v["cost"], 2), "msgs": v["msgs"], "tokens": v["tokens"]}
                    for k, v in st.get("projects", {}).items() if v.get("cost", 0) > 0}
        # Today snapshot
        td = st.get("today", {})
        today = {"cost": round(td.get("cost", 0), 2), "msgs": td.get("msgs", 0),
                 "tokens": td.get("tokens", 0)}
        with open(os.path.join(d, "token-stats.json"), "w") as f:
            json.dump({"machine": MACHINE, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "session_count": st["sessions"], "input_tokens": st["inp"], "output_tokens": st["out"],
                "cache_write_tokens": st["cw"], "cache_read_tokens": st["cr"],
                "total_cost": round(st["cost"], 2), "date_range": {"min": st["d_min"], "max": st["d_max"]},
                "model_breakdown": mb, "daily": daily, "hourly": hourly,
                "projects": projects, "today": today}, f, indent=2)
    except Exception: pass

def recalc_remote_cost(data):
    """Recalculate remote machine cost using current pricing (not cached total_cost)."""
    total = 0.0
    mb = data.get("model_breakdown", {})
    if mb:
        # Has per-model breakdown — use token ratio (not msg ratio, since
        # Opus messages have far more tokens per msg than Haiku)
        inp = data.get("input_tokens", 0)
        out = data.get("output_tokens", 0)
        cw = data.get("cache_write_tokens", 0)
        cr = data.get("cache_read_tokens", 0)
        total_tokens = max(sum(v.get("tokens", 0) for v in mb.values()), 1)
        for model, mdata in mb.items():
            ratio = mdata.get("tokens", 0) / total_tokens
            p = PRICING.get(tier(model), PRICING["sonnet"])
            model_cost = (inp * ratio * p["input"] + out * ratio * p["output"] +
                          cw * ratio * p["cache_write"] + cr * ratio * p["cache_read"]) / 1e6
            total += model_cost
            mdata["cost"] = round(model_cost, 2)
    else:
        # Fallback: assume sonnet pricing
        inp = data.get("input_tokens", 0)
        out = data.get("output_tokens", 0)
        cw = data.get("cache_write_tokens", 0)
        cr = data.get("cache_read_tokens", 0)
        p = PRICING["sonnet"]
        total = (inp * p["input"] + out * p["output"] + cw * p["cache_write"] + cr * p["cache_read"]) / 1e6
    data["total_cost"] = round(total, 2)
    return data

def load_remotes():
    remotes = []
    if not SYNC_DIR: return remotes
    md = os.path.join(SYNC_DIR, "machines")
    if not os.path.isdir(md): return remotes
    for m in os.listdir(md):
        if m == MACHINE: continue
        sf = os.path.join(md, m, "token-stats.json")
        if os.path.isfile(sf):
            try:
                with open(sf) as f:
                    data = recalc_remote_cost(json.load(f))
                # Normalize field names to match local scan() output
                data["cost"] = data.get("total_cost", 0)
                data["sessions"] = data.get("session_count", 0)
                data["d_min"] = data.get("date_range", {}).get("min")
                data["d_max"] = data.get("date_range", {}).get("max")
                data.setdefault("models", data.get("model_breakdown", {}))
                data.setdefault("daily", {})
                data.setdefault("hourly", {})
                data.setdefault("projects", {})
                data.setdefault("today", {"cost": 0, "msgs": 0, "tokens": 0})
                data.setdefault("daily_models", {})
                data.setdefault("daily_hourly", {})
                data.setdefault("sessions_by_day", {})
                remotes.append(data)
            except Exception: pass
    return remotes

DASHBOARD_FILE = Path.home() / ".config" / "cc-token-stats" / "dashboard.html"

def generate_dashboard():
    """Generate a self-contained HTML dashboard and open in browser."""
    local = scan()
    usage, _ = get_usage()
    remotes = load_remotes()
    machines = [local] + [r for r in remotes]
    sub = CFG.get("subscription", 0)

    tc = sum(m.get("cost", 0) for m in machines)
    ts = sum(m.get("sessions", 0) for m in machines)

    # Merge today across all machines
    today = dict(local.get("today", {}))
    for r in remotes:
        rt = r.get("today", {})
        today["cost"] = today.get("cost", 0) + rt.get("cost", 0)
        today["msgs"] = today.get("msgs", 0) + rt.get("msgs", 0)

    # Merge daily across all machines
    daily = {}
    for m in machines:
        for date, v in m.get("daily", {}).items():
            if date not in daily:
                daily[date] = {"cost": 0.0, "msgs": 0, "tokens": 0}
            daily[date]["cost"] += v.get("cost", 0)
            daily[date]["msgs"] += v.get("msgs", 0)
            daily[date]["tokens"] += v.get("tokens", 0)

    # Merge hourly across all machines
    hourly = {}
    for m in machines:
        for h, cnt in m.get("hourly", {}).items():
            h_str = str(h)
            hourly[h_str] = hourly.get(h_str, 0) + cnt

    # Merge models across all machines
    models = {}
    for m in machines:
        for model, data in m.get("models", {}).items():
            if model not in models:
                models[model] = {"msgs": 0, "tokens": 0, "cost": 0.0}
            models[model]["msgs"] += data.get("msgs", 0)
            models[model]["tokens"] += data.get("tokens", 0)
            models[model]["cost"] += data.get("cost", 0)

    # Merge projects across all machines
    projects = {}
    for m in machines:
        for proj, v in m.get("projects", {}).items():
            if proj not in projects:
                projects[proj] = {"cost": 0.0, "msgs": 0, "tokens": 0}
            projects[proj]["cost"] += v.get("cost", 0)
            projects[proj]["msgs"] += v.get("msgs", 0)
            projects[proj]["tokens"] += v.get("tokens", 0)

    machine_data = [{"name": m.get("machine", "?"), "cost": round(m.get("cost", 0), 2),
                     "sessions": m.get("sessions", 0)} for m in machines]
    model_display = {}
    model_msgs = {}
    for k, v in models.items():
        short = MODEL_SHORT.get(k, k.split("-")[-1] if "-" in k else k[:15])
        model_display[short] = round(v["cost"], 2)
        model_msgs[short] = v["msgs"]

    # Token composition
    total_inp = sum(m.get("inp", 0) + m.get("input_tokens", 0) for m in machines)
    total_out = sum(m.get("out", 0) + m.get("output_tokens", 0) for m in machines)
    total_cw = sum(m.get("cw", 0) + m.get("cache_write_tokens", 0) for m in machines)
    total_cr = sum(m.get("cr", 0) + m.get("cache_read_tokens", 0) for m in machines)
    total_tokens = total_inp + total_out + total_cw + total_cr

    # Date range across all machines
    dmin_all = local.get("d_min")
    for r in remotes:
        rd = r.get("d_min") or r.get("date_range", {}).get("min")

    # Daily average based on calendar span
    active_days = len([v for v in daily.values() if v.get("cost", 0) > 0])
    if dmin_all:
        span_days = (datetime.now() - datetime.strptime(dmin_all, "%Y-%m-%d")).days + 1
    else:
        span_days = max(active_days, 1)
    daily_avg = round(tc / max(span_days, 1), 2)
    limits = {}
    if usage:
        for key in ["five_hour", "seven_day", "seven_day_sonnet", "seven_day_opus"]:
            obj = usage.get(key)
            if obj and obj.get("utilization") is not None:
                limits[key] = {"util": obj["utilization"], "resets_at": obj.get("resets_at", "")}
        if rd and (not dmin_all or rd < dmin_all): dmin_all = rd
    roi = {}
    if sub > 0 and dmin_all:
        first = datetime.strptime(dmin_all, "%Y-%m-%d")
        months = max((datetime.now() - first).days / 30.0, 1)
        paid = sub * months
        roi = {"sub": sub, "months": round(months, 1), "paid": round(paid, 0),
               "cost": round(tc, 2), "multiplier": round(tc / paid, 1)}

    # v3: Merge daily_models across machines
    daily_models = {}
    for m in machines:
        for date, models_d in m.get("daily_models", {}).items():
            if date not in daily_models:
                daily_models[date] = {}
            for model, v in models_d.items():
                if model not in daily_models[date]:
                    daily_models[date][model] = {"cost": 0.0, "msgs": 0}
                daily_models[date][model]["cost"] += v.get("cost", 0)
                daily_models[date][model]["msgs"] += v.get("msgs", 0)

    # v3: Merge daily_hourly (weekday × hour heatmap)
    heatmap = {}  # {weekday: {hour: count}}
    for m in machines:
        for wd, hours_d in m.get("daily_hourly", {}).items():
            wd_s = str(wd)
            if wd_s not in heatmap:
                heatmap[wd_s] = {}
            for h, cnt in hours_d.items():
                h_s = str(h)
                heatmap[wd_s][h_s] = heatmap[wd_s].get(h_s, 0) + cnt

    # v3: Merge sessions_by_day
    sessions_by_day = {}
    for m in machines:
        for date, sess_list in m.get("sessions_by_day", {}).items():
            if date not in sessions_by_day:
                sessions_by_day[date] = []
            sessions_by_day[date].extend(sess_list)
    # Cap and sort by cost desc
    for date in sessions_by_day:
        sessions_by_day[date] = sorted(sessions_by_day[date], key=lambda x: -x.get("cost", 0))[:30]

    # v3: Forecast — project current month total based on 7-day average
    forecast = {}
    sorted_dates = sorted(daily.keys())
    if len(sorted_dates) >= 3:
        recent_7 = [daily[d]["cost"] for d in sorted_dates[-7:]]
        avg_7d = sum(recent_7) / len(recent_7)
        today_dt = datetime.now()
        days_in_month = 30  # simplified
        try:
            import calendar
            days_in_month = calendar.monthrange(today_dt.year, today_dt.month)[1]
        except Exception: pass
        month_prefix = today_dt.strftime("%Y-%m")
        month_actual = sum(daily[d]["cost"] for d in daily if d[:7] == month_prefix)
        days_left = days_in_month - today_dt.day
        projected = month_actual + (avg_7d * max(days_left, 0))
        forecast = {"projected": round(projected, 0), "avg_7d": round(avg_7d, 2),
                    "days_left": days_left, "month_actual": round(month_actual, 2)}

    # v3: Anomaly detection — days where cost > 2x trailing 30-day average
    anomaly_dates = []
    for idx, date in enumerate(sorted_dates):
        window = [daily[d]["cost"] for d in sorted_dates[max(0, idx-30):idx]]
        if len(window) >= 3:
            avg = sum(window) / len(window)
            if avg > 0 and daily[date]["cost"] > avg * 2:
                anomaly_dates.append(date)

    # v3: daily_models for payload (round costs)
    dm_payload = {}
    for date, models_d in sorted(daily_models.items()):
        dm_payload[date] = {m: round(v["cost"], 2) for m, v in models_d.items()}

    payload = json.dumps({
        "daily": {k: {"cost": round(v["cost"], 2), "msgs": v["msgs"], "tokens": v["tokens"],
                       "sessions": v.get("sessions", 0)}
                  for k, v in sorted(daily.items()) if v.get("cost", 0) > 0 or v.get("msgs", 0) > 0},
        "hourly": {str(k): v for k, v in sorted(hourly.items())},
        "models": model_display, "model_msgs": model_msgs,
        "projects": {k: {"cost": round(v["cost"], 2), "msgs": v["msgs"]}
                     for k, v in sorted(projects.items(), key=lambda x: -x[1]["cost"])[:15]},
        "machines": machine_data, "limits": limits, "roi": roi,
        "today": {"cost": round(today.get("cost", 0), 2), "msgs": today.get("msgs", 0)},
        "total": {"cost": round(tc, 2), "sessions": ts, "tokens": total_tokens,
                  "inp": total_inp, "out": total_out, "cw": total_cw, "cr": total_cr},
        "daily_avg": daily_avg, "active_days": active_days, "span_days": span_days,
        "daily_models": dm_payload,
        "heatmap": heatmap,
        "sessions_by_day": sessions_by_day,
        "forecast": forecast,
        "anomaly_dates": anomaly_dates,
        "lang": LANG, "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False)

    html = _build_dashboard_html(payload)
    # Atomic file write: tmp + rename to avoid race condition
    DASHBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = DASHBOARD_FILE.with_suffix(".tmp")
    tmp_path.write_text(html)
    os.rename(str(tmp_path), str(DASHBOARD_FILE))
    return str(DASHBOARD_FILE)

def _build_dashboard_html(payload):
    """Build self-contained HTML string for dashboard v3. All data from trusted local caches."""
    template = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Claude Code Token Stats</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0d1117;--card:#161b22;--border:#30363d;--text:#c9d1d9;--dim:#8b949e;
  --teal:#58d4ab;--blue:#58a6ff;--gold:#d4a04a;--red:#f85149;--amber:#d29922;
  --purple:#a371f7;--muted:#484f58;
}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text",system-ui,sans-serif;padding:16px;line-height:1.5}
.grid{display:grid;gap:16px;grid-template-columns:repeat(12,1fr)}
.s2{grid-column:span 2}.s4{grid-column:span 4}.s6{grid-column:span 6}.s12{grid-column:span 12}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;position:relative;overflow:hidden}
.kpi{text-align:center}
.kpi .label{font-size:12px;color:var(--dim);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.kpi .value{font-size:28px;font-weight:700;font-family:"SF Mono",SFMono-Regular,Consolas,monospace}
.kpi .sub{font-size:12px;color:var(--dim);margin-top:4px}
.kpi .stripe{position:absolute;top:0;left:0;right:0;height:3px;border-radius:12px 12px 0 0}
.chart-box{min-height:320px}
.section-title{font-size:14px;font-weight:600;margin-bottom:12px;color:var(--text)}
/* Progress bars */
.pbar-wrap{margin-bottom:10px}
.pbar-label{display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px}
.pbar-label span:first-child{color:var(--text)}.pbar-label span:last-child{color:var(--dim);font-family:"SF Mono",monospace}
.pbar{height:8px;background:var(--muted);border-radius:4px;overflow:hidden}
.pbar-fill{height:100%;border-radius:4px;transition:width .3s}
/* Limit battery */
.limit-item{margin-bottom:14px}
.limit-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}
.limit-name{font-size:13px;color:var(--text)}.limit-pct{font-size:13px;font-family:"SF Mono",monospace;font-weight:600}
.limit-bar{height:20px;background:#21262d;border-radius:4px;position:relative;overflow:hidden;border:1px solid var(--border)}
.limit-fill{height:100%;border-radius:3px;transition:width .4s}
.limit-mark{position:absolute;top:0;bottom:0;width:1px;border-left:2px dashed rgba(255,255,255,.3)}
.limit-reset{font-size:11px;color:var(--dim);margin-top:2px}
/* Machine cards */
.machine-card{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:10px}
.machine-name{font-size:14px;font-weight:600;margin-bottom:8px}
.machine-stat{display:flex;justify-content:space-between;font-size:12px;color:var(--dim);margin-bottom:4px}
.machine-stat span:last-child{color:var(--text);font-family:"SF Mono",monospace}
/* Table */
.data-table{width:100%;border-collapse:collapse;font-size:13px}
.data-table th{text-align:left;padding:10px 12px;border-bottom:2px solid var(--border);color:var(--dim);font-weight:500;font-size:12px;text-transform:uppercase;letter-spacing:.5px}
.data-table td{padding:8px 12px;border-bottom:1px solid var(--border);font-family:"SF Mono",monospace}
.data-table tr.clickable{cursor:pointer}.data-table tr.clickable:hover{background:rgba(88,166,255,.06)}
.data-table tr.sub-row{background:rgba(22,27,34,.8)}
.data-table tr.sub-row td{padding:6px 12px 6px 32px;font-size:12px;color:var(--dim);border-bottom:1px solid rgba(48,54,61,.5)}
.data-table tr.sub-row td:first-child{color:var(--blue)}
.hidden{display:none}
/* Scrollable table wrapper */
.table-wrap{max-height:500px;overflow-y:auto}
.table-wrap::-webkit-scrollbar{width:6px}.table-wrap::-webkit-scrollbar-track{background:var(--bg)}.table-wrap::-webkit-scrollbar-thumb{background:var(--muted);border-radius:3px}
/* Footer */
.footer{text-align:center;padding:20px 0 8px;font-size:11px;color:var(--muted)}
/* Responsive */
@media(max-width:900px){
  .s2{grid-column:span 4}.s4{grid-column:span 6}.s6{grid-column:span 12}
}
@media(max-width:600px){
  .s2{grid-column:span 6}.s4{grid-column:span 12}.s6{grid-column:span 12}
  .kpi .value{font-size:22px}body{padding:8px}.grid{gap:10px}
}
</style>
</head>
<body>
<!-- Row 1: KPI Cards -->
<div class="grid" id="kpi-row">
  <div class="card kpi s2" id="kpi-today"><div class="stripe" style="background:var(--teal)"></div><div class="label" id="kl-today"></div><div class="value" id="kv-today" style="color:var(--teal)"></div><div class="sub" id="ks-today"></div></div>
  <div class="card kpi s2" id="kpi-total"><div class="stripe" style="background:var(--blue)"></div><div class="label" id="kl-total"></div><div class="value" id="kv-total" style="color:var(--blue)"></div><div class="sub" id="ks-total"></div></div>
  <div class="card kpi s2" id="kpi-forecast"><div class="stripe" style="background:var(--gold)"></div><div class="label" id="kl-forecast"></div><div class="value" id="kv-forecast" style="color:var(--gold)"></div><div class="sub" id="ks-forecast"></div></div>
  <div class="card kpi s2" id="kpi-roi"><div class="stripe" style="background:var(--amber)"></div><div class="label" id="kl-roi"></div><div class="value" id="kv-roi" style="color:var(--amber)"></div><div class="sub" id="ks-roi"></div></div>
  <div class="card kpi s2" id="kpi-sessions"><div class="stripe" style="background:var(--teal)"></div><div class="label" id="kl-sessions"></div><div class="value" id="kv-sessions" style="color:var(--teal)"></div><div class="sub" id="ks-sessions"></div></div>
  <div class="card kpi s2" id="kpi-avg"><div class="stripe" style="background:var(--purple)"></div><div class="label" id="kl-avg"></div><div class="value" id="kv-avg" style="color:var(--purple)"></div><div class="sub" id="ks-avg"></div></div>
</div>
<!-- Row 2: Daily Chart -->
<div class="grid" style="margin-top:16px">
  <div class="card s12 chart-box" style="min-height:400px"><div id="chart-daily" style="width:100%;height:380px"></div></div>
</div>
<!-- Row 3: Model + Token + Limits -->
<div class="grid" style="margin-top:16px">
  <div class="card s4"><div class="section-title" id="title-model"></div><div id="model-area" style="min-height:260px"></div></div>
  <div class="card s4"><div class="section-title" id="title-token"></div><div id="token-area"></div></div>
  <div class="card s4"><div class="section-title" id="title-limits"></div><div id="limits-area"></div></div>
</div>
<!-- Row 4: Model Trend + Heatmap -->
<div class="grid" style="margin-top:16px">
  <div class="card s6 chart-box"><div id="chart-model-trend" style="width:100%;height:300px"></div></div>
  <div class="card s6 chart-box"><div id="chart-heatmap" style="width:100%;height:300px"></div></div>
</div>
<!-- Row 5: Projects + Machines -->
<div class="grid" style="margin-top:16px">
  <div class="card s6 chart-box"><div id="chart-projects" style="width:100%;height:320px"></div></div>
  <div class="card s6"><div class="section-title" id="title-machines"></div><div id="machines-area"></div></div>
</div>
<!-- Row 6: Daily Detail Table -->
<div class="grid" style="margin-top:16px">
  <div class="card s12">
    <div class="section-title" id="title-table"></div>
    <div class="table-wrap"><table class="data-table" id="detail-table"><thead id="table-head"></thead><tbody id="table-body"></tbody></table></div>
  </div>
</div>
<div class="footer" id="footer-text"></div>

<script>
const D = __DATA__;
const zh = D.lang === 'zh';
const $ = id => document.getElementById(id);

// ── Helpers ──
function fc(n) {
  if (n == null) return '—';
  return '$' + n.toFixed(2);
}
function fk(n) {
  if (n == null) return '—';
  if (zh) {
    if (n >= 1e8) return (n / 1e8).toFixed(2) + ' \u4ebf';
    if (n >= 1e4) return (n / 1e4).toFixed(1) + ' \u4e07';
    return n.toLocaleString();
  }
  if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return n.toLocaleString();
}
function pct(a, b) { return b ? (a / b * 100).toFixed(1) : '0.0'; }
function escHtml(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

// ── Row 1: KPI Cards ──
$('kl-today').textContent = zh ? '\u4eca\u65e5\u82b1\u8d39' : 'Today Cost';
$('kv-today').textContent = fc(D.today.cost);
$('ks-today').textContent = D.today.msgs + (zh ? ' \u6761\u6d88\u606f' : ' messages');

$('kl-total').textContent = zh ? '\u603b\u82b1\u8d39' : 'Total Cost';
$('kv-total').textContent = fc(D.total.cost);
$('ks-total').textContent = D.span_days + (zh ? ' \u5929' : ' days');

$('kl-forecast').textContent = zh ? '\u672c\u6708\u9884\u6d4b' : 'Month Forecast';
if (D.forecast && D.forecast.projected) {
  $('kv-forecast').textContent = fc(D.forecast.projected);
  $('ks-forecast').textContent = zh ? '\u57fa\u4e8e 7 \u5929\u5747\u503c' : 'based on 7d avg';
} else {
  $('kv-forecast').textContent = '\u2014';
  $('ks-forecast').textContent = '';
}

$('kl-roi').textContent = 'ROI';
if (D.roi && D.roi.multiplier) {
  $('kv-roi').textContent = D.roi.multiplier.toFixed(1) + 'x';
  $('ks-roi').textContent = fc(D.roi.paid) + (zh ? ' \u5df2\u4ed8' : ' paid');
} else {
  $('kv-roi').textContent = '\u2014';
  $('ks-roi').textContent = '';
}

$('kl-sessions').textContent = zh ? '\u4f1a\u8bdd' : 'Sessions';
$('kv-sessions').textContent = D.total.sessions.toLocaleString();
$('ks-sessions').textContent = (D.machines ? D.machines.length : 0) + (zh ? ' \u53f0\u673a\u5668' : ' machines');

$('kl-avg').textContent = zh ? '\u65e5\u5747\u82b1\u8d39' : 'Daily Avg';
$('kv-avg').textContent = fc(D.daily_avg);
$('ks-avg').textContent = '/' + (zh ? '\u5929' : 'day');

// ── Row 2: Daily Cost+Messages Chart ──
(function() {
  var dates = Object.keys(D.daily).sort();
  var costs = dates.map(function(d) { return D.daily[d].cost || 0; });
  var msgs = dates.map(function(d) { return D.daily[d].msgs || 0; });
  var anomalySet = {};
  (D.anomaly_dates || []).forEach(function(d) { anomalySet[d] = true; });
  var anomalyPoints = [];
  dates.forEach(function(d, i) {
    if (anomalySet[d]) anomalyPoints.push({coord: [i, costs[i]], value: costs[i]});
  });

  // Forecast line data
  var forecastData = [];
  if (D.forecast && D.forecast.avg_7d && dates.length > 0) {
    var lastDate = new Date(dates[dates.length - 1]);
    var lastMonth = lastDate.getMonth();
    var lastYear = lastDate.getFullYear();
    var daysInMonth = new Date(lastYear, lastMonth + 1, 0).getDate();
    // Add from last real date to end of month
    for (var fd = lastDate.getDate(); fd <= daysInMonth; fd++) {
      var ds = lastYear + '-' + String(lastMonth + 1).padStart(2, '0') + '-' + String(fd).padStart(2, '0');
      forecastData.push([ds, D.forecast.avg_7d]);
    }
  }

  // Enhanced tooltip with model breakdown
  var dailyModels = D.daily_models || {};

  var chart = echarts.init($('chart-daily'), null, {renderer: 'canvas'});
  var allDates = dates.slice();
  forecastData.forEach(function(f) { if (allDates.indexOf(f[0]) === -1) allDates.push(f[0]); });
  allDates.sort();

  // Re-map costs/msgs to full date range
  var fullCosts = allDates.map(function(d) { return D.daily[d] ? D.daily[d].cost || 0 : null; });
  var fullMsgs = allDates.map(function(d) { return D.daily[d] ? D.daily[d].msgs || 0 : null; });

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#161b22',
      borderColor: '#30363d',
      textStyle: {color: '#c9d1d9', fontSize: 12},
      formatter: function(params) {
        var date = params[0].axisValue;
        var lines = ['<b>' + date + '</b>'];
        params.forEach(function(p) {
          if (p.seriesName === (zh ? '\u82b1\u8d39' : 'Cost') && p.value != null) {
            lines.push(p.marker + ' ' + p.seriesName + ': ' + fc(p.value));
          }
          if (p.seriesName === (zh ? '\u6d88\u606f' : 'Messages') && p.value != null) {
            lines.push(p.marker + ' ' + p.seriesName + ': ' + p.value);
          }
        });
        // Model breakdown
        var dm = dailyModels[date];
        if (dm) {
          lines.push('<br/><span style="color:#8b949e">' + (zh ? '\u6a21\u578b\u660e\u7ec6' : 'Models') + ':</span>');
          Object.keys(dm).sort(function(a, b) { return dm[b] - dm[a]; }).forEach(function(m) {
            lines.push('&nbsp;&nbsp;' + escHtml(m) + ': ' + fc(dm[m]));
          });
        }
        return lines.join('<br/>');
      }
    },
    legend: {data: [zh ? '\u82b1\u8d39' : 'Cost', zh ? '\u6d88\u606f' : 'Messages'], textStyle: {color: '#8b949e'}, top: 8},
    grid: {left: 60, right: 60, top: 50, bottom: 70},
    xAxis: {type: 'category', data: allDates, axisLabel: {color: '#8b949e', fontSize: 11, rotate: dates.length > 30 ? 45 : 0}, axisLine: {lineStyle: {color: '#30363d'}}},
    yAxis: [
      {type: 'value', name: zh ? '\u82b1\u8d39 ($)' : 'Cost ($)', nameTextStyle: {color: '#8b949e'}, axisLabel: {color: '#8b949e', formatter: function(v) { return '$' + v.toFixed(0); }}, splitLine: {lineStyle: {color: '#21262d'}}},
      {type: 'value', name: zh ? '\u6d88\u606f' : 'Msgs', nameTextStyle: {color: '#8b949e'}, axisLabel: {color: '#8b949e'}, splitLine: {show: false}}
    ],
    dataZoom: [{type: 'slider', start: dates.length > 60 ? 50 : 0, end: 100, height: 24, bottom: 10, borderColor: '#30363d', fillerColor: 'rgba(88,212,171,.15)', handleStyle: {color: '#58d4ab'}, textStyle: {color: '#8b949e'}}],
    series: [
      {
        name: zh ? '\u82b1\u8d39' : 'Cost', type: 'bar', data: fullCosts, yAxisIndex: 0,
        itemStyle: {color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{offset: 0, color: '#58d4ab'}, {offset: 1, color: '#2ea77a'}]), borderRadius: [3, 3, 0, 0]},
        markPoint: {
          symbol: 'circle', symbolSize: 14,
          itemStyle: {color: 'rgba(248,81,73,.8)', borderColor: '#f85149', borderWidth: 2},
          label: {show: false},
          data: anomalyPoints
        }
      },
      {
        name: zh ? '\u6d88\u606f' : 'Messages', type: 'line', data: fullMsgs, yAxisIndex: 1,
        smooth: true, symbol: 'none', lineStyle: {color: '#58a6ff', width: 2},
        areaStyle: {color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{offset: 0, color: 'rgba(88,166,255,.2)'}, {offset: 1, color: 'rgba(88,166,255,.02)'}])}
      },
      {
        name: zh ? '\u9884\u6d4b' : 'Forecast', type: 'line', data: (function() {
          return allDates.map(function(d) {
            var match = forecastData.find(function(f) { return f[0] === d; });
            return match ? match[1] : null;
          });
        })(),
        yAxisIndex: 0, smooth: false, symbol: 'none',
        lineStyle: {color: '#d4a04a', width: 2, type: 'dashed'},
        connectNulls: false
      }
    ]
  });
  window.addEventListener('resize', function() { chart.resize(); });
})();

// ── Row 3a: Model Distribution ──
(function() {
  $('title-model').textContent = zh ? '\u6a21\u578b\u5206\u5e03' : 'Model Distribution';
  var models = D.models || {};
  var names = Object.keys(models).sort(function(a, b) { return models[b] - models[a]; });
  var total = names.reduce(function(s, n) { return s + models[n]; }, 0);
  if (names.length === 0) { $('model-area').textContent = zh ? '\u65e0\u6570\u636e' : 'No data'; return; }

  var maxPct = total > 0 ? (models[names[0]] / total * 100) : 0;
  if (maxPct > 90) {
    // Progress bars mode
    var html = '';
    names.forEach(function(n) {
      var p = total > 0 ? (models[n] / total * 100) : 0;
      html += '<div class="pbar-wrap"><div class="pbar-label"><span>' + escHtml(n) + '</span><span>' + fc(models[n]) + ' (' + p.toFixed(1) + '%)</span></div><div class="pbar"><div class="pbar-fill" style="width:' + p.toFixed(1) + '%;background:var(--teal)"></div></div></div>';
    });
    $('model-area').insertAdjacentHTML('beforeend', html);
  } else {
    // Donut chart
    var el = document.createElement('div');
    el.style.width = '100%'; el.style.height = '260px';
    $('model-area').appendChild(el);
    var colors = ['#58d4ab', '#58a6ff', '#d4a04a', '#a371f7', '#f85149', '#d29922', '#484f58'];
    var chart = echarts.init(el);
    chart.setOption({
      tooltip: {trigger: 'item', backgroundColor: '#161b22', borderColor: '#30363d', textStyle: {color: '#c9d1d9'}, formatter: function(p) { return escHtml(p.name) + '<br/>' + fc(p.value) + ' (' + p.percent + '%)'; }},
      series: [{
        type: 'pie', radius: ['45%', '72%'], center: ['50%', '50%'],
        label: {color: '#c9d1d9', fontSize: 11, formatter: function(p) { return p.name.length > 15 ? p.name.substring(0, 12) + '...' : p.name; }},
        data: names.map(function(n, i) { return {name: n, value: +models[n].toFixed(4), itemStyle: {color: colors[i % colors.length]}}; })
      }]
    });
    window.addEventListener('resize', function() { chart.resize(); });
  }
})();

// ── Row 3b: Token Composition ──
(function() {
  $('title-token').textContent = zh ? 'Token \u7ec4\u6210' : 'Token Composition';
  var t = D.total;
  var parts = [
    {label: zh ? '\u8f93\u5165' : 'Input', value: t.inp || 0, color: 'var(--blue)'},
    {label: zh ? '\u8f93\u51fa' : 'Output', value: t.out || 0, color: 'var(--teal)'},
    {label: zh ? '\u7f13\u5b58\u5199\u5165' : 'Cache Write', value: t.cw || 0, color: 'var(--gold)'},
    {label: zh ? '\u7f13\u5b58\u8bfb\u53d6' : 'Cache Read', value: t.cr || 0, color: 'var(--purple)'}
  ];
  var max = Math.max.apply(null, parts.map(function(p) { return p.value; }));
  if (max === 0) max = 1;
  var html = '';
  parts.forEach(function(p) {
    var w = (p.value / max * 100).toFixed(1);
    html += '<div class="pbar-wrap"><div class="pbar-label"><span>' + p.label + '</span><span>' + fk(p.value) + '</span></div><div class="pbar"><div class="pbar-fill" style="width:' + w + '%;background:' + p.color + '"></div></div></div>';
  });
  html += '<div style="margin-top:12px;font-size:12px;color:var(--dim)">' + (zh ? '\u603b\u8ba1' : 'Total') + ': ' + fk(t.tokens || 0) + ' tokens</div>';
  $('token-area').insertAdjacentHTML('beforeend', html);
})();

// ── Row 3c: Rate Limits ──
(function() {
  $('title-limits').textContent = zh ? '\u901f\u7387\u9650\u5236' : 'Rate Limits';
  var limits = D.limits || {};
  var keys = Object.keys(limits);
  if (keys.length === 0) {
    $('limits-area').textContent = zh ? '\u65e0\u9650\u5236\u6570\u636e' : 'No limit data';
    return;
  }
  var html = '';
  keys.forEach(function(k) {
    var lim = limits[k];
    var util = (lim.util || 0) * 100;
    var color = util < 50 ? 'var(--teal)' : util < 80 ? 'var(--gold)' : 'var(--red)';
    var resetText = '';
    if (lim.resets_at) {
      var now = new Date();
      var reset = new Date(lim.resets_at);
      var diffMin = Math.max(0, Math.round((reset - now) / 60000));
      if (diffMin >= 60) {
        resetText = (zh ? '\u91cd\u7f6e: ' : 'Resets: ') + Math.floor(diffMin / 60) + 'h ' + (diffMin % 60) + 'm';
      } else {
        resetText = (zh ? '\u91cd\u7f6e: ' : 'Resets: ') + diffMin + (zh ? ' \u5206\u949f' : ' min');
      }
    }
    html += '<div class="limit-item"><div class="limit-header"><span class="limit-name">' + escHtml(k) + '</span><span class="limit-pct" style="color:' + color + '">' + util.toFixed(1) + '%</span></div>';
    html += '<div class="limit-bar"><div class="limit-fill" style="width:' + Math.min(util, 100).toFixed(1) + '%;background:' + color + '"></div><div class="limit-mark" style="left:80%"></div></div>';
    if (resetText) html += '<div class="limit-reset">' + escHtml(resetText) + '</div>';
    html += '</div>';
  });
  $('limits-area').insertAdjacentHTML('beforeend', html);
})();

// ── Row 4a: Model Trend Stacked Area ──
(function() {
  var dm = D.daily_models || {};
  var dates = Object.keys(dm).sort();
  if (dates.length === 0) return;
  var modelSet = {};
  dates.forEach(function(d) { Object.keys(dm[d]).forEach(function(m) { modelSet[m] = true; }); });
  var modelNames = Object.keys(modelSet);
  var colors = ['#58d4ab', '#58a6ff', '#d4a04a', '#a371f7', '#f85149', '#d29922', '#484f58', '#79c0ff', '#7ee787'];

  var chart = echarts.init($('chart-model-trend'));
  chart.setOption({
    title: {text: zh ? '\u6a21\u578b\u8d8b\u52bf' : 'Model Trend', textStyle: {color: '#c9d1d9', fontSize: 14, fontWeight: 600}, top: 4, left: 4},
    tooltip: {trigger: 'axis', backgroundColor: '#161b22', borderColor: '#30363d', textStyle: {color: '#c9d1d9', fontSize: 12}},
    legend: {data: modelNames, textStyle: {color: '#8b949e', fontSize: 11}, top: 28, type: 'scroll'},
    grid: {left: 50, right: 20, top: 60, bottom: 30},
    xAxis: {type: 'category', data: dates, axisLabel: {color: '#8b949e', fontSize: 10, rotate: dates.length > 20 ? 45 : 0}, axisLine: {lineStyle: {color: '#30363d'}}},
    yAxis: {type: 'value', axisLabel: {color: '#8b949e', formatter: function(v) { return '$' + v.toFixed(0); }}, splitLine: {lineStyle: {color: '#21262d'}}},
    series: modelNames.map(function(m, i) {
      return {
        name: m, type: 'line', stack: 'total', areaStyle: {opacity: 0.6},
        emphasis: {focus: 'series'},
        lineStyle: {width: 1, color: colors[i % colors.length]},
        itemStyle: {color: colors[i % colors.length]},
        symbol: 'none',
        data: dates.map(function(d) { return dm[d][m] || 0; })
      };
    })
  });
  window.addEventListener('resize', function() { chart.resize(); });
})();

// ── Row 4b: 7x24 Heatmap ──
(function() {
  var hm = D.heatmap || {};
  var weekdays = zh ? ['\u5468\u4e00', '\u5468\u4e8c', '\u5468\u4e09', '\u5468\u56db', '\u5468\u4e94', '\u5468\u516d', '\u5468\u65e5'] : ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  var hours = [];
  for (var h = 0; h < 24; h++) hours.push(String(h).padStart(2, '0'));

  var data = [];
  var maxVal = 0;
  for (var wd = 0; wd < 7; wd++) {
    var wdData = hm[String(wd)] || {};
    for (var hr = 0; hr < 24; hr++) {
      var hrKey = String(hr).padStart(2, '0');
      var val = wdData[hrKey] || 0;
      data.push([hr, wd, val]);
      if (val > maxVal) maxVal = val;
    }
  }

  var chart = echarts.init($('chart-heatmap'));
  chart.setOption({
    title: {text: zh ? '\u6d3b\u52a8\u70ed\u529b\u56fe' : 'Activity Heatmap', textStyle: {color: '#c9d1d9', fontSize: 14, fontWeight: 600}, top: 4, left: 4},
    tooltip: {backgroundColor: '#161b22', borderColor: '#30363d', textStyle: {color: '#c9d1d9'}, formatter: function(p) { return weekdays[p.value[1]] + ' ' + hours[p.value[0]] + ':00<br/>' + p.value[2] + (zh ? ' \u6761\u6d88\u606f' : ' msgs'); }},
    grid: {left: 60, right: 40, top: 40, bottom: 30},
    xAxis: {type: 'category', data: hours, axisLabel: {color: '#8b949e', fontSize: 10}, axisLine: {lineStyle: {color: '#30363d'}}, splitArea: {show: true, areaStyle: {color: ['rgba(0,0,0,0)', 'rgba(0,0,0,0)']}}},
    yAxis: {type: 'category', data: weekdays, axisLabel: {color: '#8b949e', fontSize: 11}, axisLine: {lineStyle: {color: '#30363d'}}},
    visualMap: {min: 0, max: maxVal || 1, calculable: false, orient: 'horizontal', left: 'center', bottom: 2, itemWidth: 12, itemHeight: 80, textStyle: {color: '#8b949e', fontSize: 10}, inRange: {color: ['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353']}},
    series: [{
      type: 'heatmap', data: data,
      label: {show: false},
      itemStyle: {borderColor: '#0d1117', borderWidth: 2, borderRadius: 3},
      emphasis: {itemStyle: {borderColor: '#58a6ff', borderWidth: 2}}
    }]
  });
  window.addEventListener('resize', function() { chart.resize(); });
})();

// ── Row 5a: Project Ranking ──
(function() {
  var projects = D.projects || {};
  var names = Object.keys(projects).sort(function(a, b) { return projects[b].cost - projects[a].cost; });
  if (names.length === 0) return;

  var chart = echarts.init($('chart-projects'));
  var reversed = names.slice().reverse();
  chart.setOption({
    title: {text: zh ? '\u9879\u76ee\u6392\u540d' : 'Project Ranking', textStyle: {color: '#c9d1d9', fontSize: 14, fontWeight: 600}, top: 4, left: 4},
    tooltip: {backgroundColor: '#161b22', borderColor: '#30363d', textStyle: {color: '#c9d1d9'}, formatter: function(p) { return escHtml(p.name) + '<br/>' + fc(p.value) + ' | ' + (projects[p.name] ? projects[p.name].msgs : 0) + (zh ? ' \u6761\u6d88\u606f' : ' msgs'); }},
    grid: {left: 140, right: 60, top: 40, bottom: 20},
    xAxis: {type: 'value', axisLabel: {color: '#8b949e', formatter: function(v) { return '$' + v.toFixed(0); }}, splitLine: {lineStyle: {color: '#21262d'}}},
    yAxis: {type: 'category', data: reversed.map(function(n) { return n.length > 18 ? n.substring(0, 15) + '...' : n; }), axisLabel: {color: '#c9d1d9', fontSize: 11}},
    series: [{
      type: 'bar',
      data: reversed.map(function(n) { return {name: n, value: +projects[n].cost.toFixed(4)}; }),
      itemStyle: {color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{offset: 0, color: '#2ea77a'}, {offset: 1, color: '#58d4ab'}]), borderRadius: [0, 4, 4, 0]},
      barMaxWidth: 20,
      label: {show: true, position: 'right', color: '#8b949e', fontSize: 11, formatter: function(p) { return fc(p.value); }}
    }]
  });
  window.addEventListener('resize', function() { chart.resize(); });
})();

// ── Row 5b: Machine Cards ──
(function() {
  $('title-machines').textContent = zh ? '\u673a\u5668\u5bf9\u6bd4' : 'Machine Comparison';
  var machines = D.machines || [];
  if (machines.length === 0) { $('machines-area').textContent = zh ? '\u65e0\u6570\u636e' : 'No data'; return; }
  var maxCost = Math.max.apply(null, machines.map(function(m) { return m.cost; }));
  if (maxCost === 0) maxCost = 1;
  var html = '';
  machines.forEach(function(m) {
    var w = (m.cost / maxCost * 100).toFixed(1);
    html += '<div class="machine-card">';
    html += '<div class="machine-name">' + escHtml(m.name) + '</div>';
    html += '<div class="machine-stat"><span>' + (zh ? '\u82b1\u8d39' : 'Cost') + '</span><span>' + fc(m.cost) + '</span></div>';
    html += '<div class="machine-stat"><span>' + (zh ? '\u4f1a\u8bdd' : 'Sessions') + '</span><span>' + (m.sessions || 0) + '</span></div>';
    html += '<div class="pbar" style="margin-top:6px"><div class="pbar-fill" style="width:' + w + '%;background:var(--blue)"></div></div>';
    html += '</div>';
  });
  $('machines-area').insertAdjacentHTML('beforeend', html);
})();

// ── Row 6: Daily Detail Table ──
(function() {
  $('title-table').textContent = zh ? '\u6bcf\u65e5\u660e\u7ec6' : 'Daily Details';
  var daily = D.daily || {};
  var sessions = D.sessions_by_day || {};
  var dates = Object.keys(daily).sort().reverse();

  // Table header
  var thHtml = '<tr><th>' + (zh ? '\u65e5\u671f' : 'Date') + '</th><th>' + (zh ? '\u82b1\u8d39' : 'Cost') + '</th><th>' + (zh ? '\u6d88\u606f' : 'Msgs') + '</th><th>Tokens</th><th>' + (zh ? '\u4f1a\u8bdd' : 'Sessions') + '</th></tr>';
  $('table-head').insertAdjacentHTML('beforeend', thHtml);

  var html = '';
  dates.forEach(function(d) {
    var row = daily[d];
    var hasSessions = sessions[d] && sessions[d].length > 0;
    var rowId = 'dr-' + d.replace(/-/g, '');
    html += '<tr class="' + (hasSessions ? 'clickable' : '') + '" ' + (hasSessions ? 'data-date="' + d + '"' : '') + '>';
    html += '<td>' + (hasSessions ? '\u25b6 ' : '') + d + '</td>';
    html += '<td>' + fc(row.cost || 0) + '</td>';
    html += '<td>' + (row.msgs || 0) + '</td>';
    html += '<td>' + fk(row.tokens || 0) + '</td>';
    html += '<td>' + (row.sessions || 0) + '</td>';
    html += '</tr>';
    // Sub-rows (hidden by default)
    if (hasSessions) {
      sessions[d].forEach(function(s, i) {
        html += '<tr class="sub-row hidden" data-parent="' + d + '">';
        html += '<td>' + escHtml(s.project || '\u2014') + '</td>';
        html += '<td>' + fc(s.cost || 0) + '</td>';
        html += '<td>' + (s.msgs || 0) + '</td>';
        html += '<td colspan="2">' + escHtml(s.model || '\u2014') + '</td>';
        html += '</tr>';
      });
    }
  });
  $('table-body').insertAdjacentHTML('beforeend', html);

  // Click to expand/collapse
  $('table-body').addEventListener('click', function(e) {
    var tr = e.target.closest('tr.clickable');
    if (!tr) return;
    var date = tr.getAttribute('data-date');
    if (!date) return;
    var subs = document.querySelectorAll('tr.sub-row[data-parent="' + date + '"]');
    var isHidden = subs.length > 0 && subs[0].classList.contains('hidden');
    var arrow = isHidden ? '\u25bc ' : '\u25b6 ';
    tr.querySelector('td').textContent = arrow + date;
    subs.forEach(function(s) { s.classList.toggle('hidden'); });
  });
})();

// ── Footer ──
$('footer-text').textContent = (zh ? '\u751f\u6210\u4e8e ' : 'Generated at ') + (D.generated || '') + ' | Claude Code Token Stats Dashboard';
</script>
</body>
</html>
"""
    return template.replace("__DATA__", payload)

# ─── Render ──────────────────────────────────────────────────────

# Styles — auto-detect dark/light mode
def _is_dark():
    try:
        r = subprocess.run(["defaults","read","-g","AppleInterfaceStyle"],
                           capture_output=True, text=True, timeout=3)
        return "dark" in r.stdout.lower()
    except Exception: return True  # default to dark

DARK = _is_dark()

# ── Color System ──
# Brand: teal green · Info: blue · Warn: amber · Danger: red
# Light mode: all colors must have hue saturation (pure gray/black renders transparent on frosted glass)

if DARK:
    # ── Dark mode: soft, warm tones on dark background ──
    H1   = "color=#5CC6A7 size=14"                # teal — title/section headers
    H2   = "color=#5CC6A7 size=13"
    ROW  = "color=#D4CDC0 size=13 font=Menlo"     # warm white — primary data
    ROW2 = "color=#D4CDC0 size=12 font=Menlo"
    DIM  = "color=#9E9589 size=11 font=Menlo"     # warm gray — secondary info
    DIM2 = "color=#9E9589 size=10 font=Menlo"
    META = "color=#6B6560 size=10"                 # muted — footer/timestamps
    SEC  = "color=#6BA4C9 size=13"                 # soft blue — interactive items
    SEC2 = "color=#6BA4C9 size=12"
    MODL = "color=#9E9589 size=12 font=Menlo"     # warm gray — model details
    BAR  = "color=#5CC6A7 size=11 font=Menlo"     # teal — bar charts
    WARN = "color=#E8A838 size=12"                 # amber — warnings
else:
    # ── Light mode: dark saturated tones (avoid pure gray → SwiftBar makes it transparent) ──
    H1   = "color=#0E1018 size=14"                # near-black with subtle blue tint — title
    H2   = "color=#0E1018 size=13"
    ROW  = "color=#1C2030 size=13 font=Menlo"     # dark navy — primary data (reads as near-black)
    ROW2 = "color=#1C2030 size=12 font=Menlo"
    DIM  = "color=#2C3040 size=12 font=Menlo"     # navy — secondary info
    DIM2 = "color=#2C3040 size=11 font=Menlo"
    META = "color=#3C4050 size=11"                 # slate — footer
    SEC  = "color=#1B5A85 size=13"                 # deep blue — interactive items
    SEC2 = "color=#1B5A85 size=12"
    MODL = "color=#2C3040 size=12 font=Menlo"     # navy — model details
    BAR  = "color=#1A5C4C size=12 font=Menlo"     # rich dark teal — bar charts
    WARN = "color=#B86E1A size=12"                 # dark amber — warnings

def main():
    auto_update()
    local = scan()
    save_sync(local)
    remotes = load_remotes()

    # Build machine list
    machines = [{
        "label": mlabel(MACHINE), "name": MACHINE, "sessions": local["sessions"],
        "inp": local["inp"], "out": local["out"], "cw": local["cw"], "cr": local["cr"],
        "cost": local["cost"], "d_min": local["d_min"], "d_max": local["d_max"],
        "local": True, "at": None, "models": local.get("models", {}),
    }]
    for r in remotes:
        dr = r.get("date_range", {})
        machines.append({
            "label": mlabel(r.get("machine", "?")), "name": r.get("machine", "?"),
            "sessions": r.get("session_count", 0),
            "inp": r.get("input_tokens", 0), "out": r.get("output_tokens", 0),
            "cw": r.get("cache_write_tokens", 0), "cr": r.get("cache_read_tokens", 0),
            "cost": r.get("total_cost", 0), "d_min": dr.get("min"), "d_max": dr.get("max"),
            "local": False, "at": r.get("generated_at"), "models": r.get("model_breakdown", {}),
        })

    ti = sum(m["inp"] for m in machines); to = sum(m["out"] for m in machines)
    tw = sum(m["cw"] for m in machines); tr = sum(m["cr"] for m in machines)
    tc = sum(m["cost"] for m in machines); ts = sum(m["sessions"] for m in machines)
    ta = ti + to + tw + tr
    today = local["today"]
    machine_count = len(machines)

    daily = dict(local["daily"])  # convert from defaultdict
    # Sort by date
    daily_sorted = sorted(daily.items(), key=lambda x: x[0])
    # Last 7 days for quick stats (today + 6 preceding days)
    last_7d = [(d, v) for d, v in daily_sorted if d >= (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")]

    # Aggregate models across all machines
    all_models = {}
    for m in machines:
        for model, data in m.get("models", {}).items():
            if model not in all_models:
                all_models[model] = {"msgs": 0, "tokens": 0, "cost": 0.0}
            all_models[model]["msgs"] += data["msgs"]
            all_models[model]["tokens"] += data["tokens"]
            all_models[model]["cost"] += data["cost"]
    total_model_msgs = max(sum(v["msgs"] for v in all_models.values()), 1)

    # ─── Menu bar line ───
    usage, usage_err = get_usage()

    # Get limits for panel display
    _5h_util = 0; _7d_util = 0
    if usage:
        _fh = usage.get("five_hour")
        if _fh and _fh.get("utilization") is not None: _5h_util = _fh["utilization"]
        _sd = usage.get("seven_day")
        if _sd and _sd.get("utilization") is not None: _7d_util = _sd["utilization"]

    _max_util = max(_5h_util, _7d_util)
    if _max_util >= 100:
        print(f"CC 100%")
    elif _5h_util > 0:
        print(f"CC {_5h_util:.0f}%")
    else:
        print("CC")
    print("---")

    # ═══════════════════════════════════════════════════════════════
    # LAYOUT: Limits → Today → Overview → ROI → Details → Machines
    # ═══════════════════════════════════════════════════════════════
    title = t("title")
    print(f"{title} | {H1}")

    W = 30  # total line display width for aligned rows
    def rj(label, val):
        pad = W - len(label) - dw(val)
        return f"{label}{' ' * max(pad, 1)}{val}"

    # ═══ 1. LIMITS (most urgent) ═══
    # usage already fetched above for menu bar line
    check_and_notify(usage)
    if usage:
        def _reset_time_local(reset_str):
            try:
                rt = datetime.fromisoformat(reset_str.replace("Z", "+00:00"))
                return rt.astimezone().strftime("%m-%d %H:%M")
            except Exception: return ""

        def _gauge(pct):
            p = min(max(pct, 0), 100)
            filled = round(p / 100 * 10)
            return "▰" * filled + "▱" * (10 - filled)

        # Each gauge gets a distinct base color; danger overrides at 60%/80%
        if DARK:
            LINE_COLORS = ["#5CC6A7", "#C9B87A", "#6BA4C9", "#D4CDC0"]   # teal, gold, blue, warm white
        else:
            LINE_COLORS = ["#1A5C4C", "#6B5C28", "#1B5A85", "#2C3040"]   # rich teal, bronze, deep blue, navy
        _color_idx = [0]

        def _gauge_color(pct):
            """Base color by position, overridden by danger at high utilization."""
            idx = _color_idx[0]
            _color_idx[0] += 1
            if pct >= 80: return "#E85838" if DARK else "#C03020"   # red
            if pct >= 60: return "#E8A838" if DARK else "#B86E1A"   # amber
            return LINE_COLORS[idx % len(LINE_COLORS)]

        LW = 8

        def _reset_short(reset_str):
            """Short reset label — ASCII only for uniform monospace width."""
            if not reset_str: return ""
            try:
                rt = datetime.fromisoformat(reset_str.replace("Z", "+00:00"))
                now_aware = datetime.now().astimezone()
                secs = (rt - now_aware).total_seconds()
                if secs <= 0: return "now"
                hrs = int(secs // 3600); mins = int((secs % 3600) // 60)
                if hrs >= 48: return f"{hrs // 24}d"
                if hrs >= 24: return f"1d{hrs-24}h"
                # Use fixed-length format: "Xh" or "XhYm" or "Xm"
                if hrs > 0 and mins > 0: return f"{hrs}h{mins}m"
                if hrs > 0: return f"{hrs}h"
                return f"{mins}m"
            except Exception: return ""

        gauge_items = [
            ("Session", usage.get("five_hour")),
            ("Weekly ", usage.get("seven_day")),
        ]
        ss = usage.get("seven_day_sonnet")
        if ss and ss.get("utilization") is not None:
            gauge_items.append(("Sonnet ", ss))
        so = usage.get("seven_day_opus")
        if so and so.get("utilization") is not None:
            gauge_items.append(("Opus   ", so))
        eu = usage.get("extra_usage")
        if eu and (eu.get("is_enabled") or (eu.get("used_credits") or 0) > 0):
            # API returns utilization as percentage (0.56 = 0.56%)
            eu_util = eu.get("utilization") or 0
            eu_obj = {"utilization": eu_util, "resets_at": eu.get("resets_at", "")}
            gauge_items.append(("Extra  ", eu_obj))

        # Build lines with uniform ASCII formatting
        gauge_lines = []
        for label, obj in gauge_items:
            if not obj or obj.get("utilization") is None: continue
            p = obj["utilization"]
            rst = _reset_short(obj.get("resets_at"))
            col = _gauge_color(p)
            rt_local = _reset_time_local(obj.get("resets_at", ""))
            # All ASCII: label(8) + gauge(10) + pct(5) + optional reset
            reset_part = f"  ↻{rst}" if rst else ""
            line = f"{label:<{LW}}{_gauge(p)} {p:>3.0f}%{reset_part}"
            is_extra = label.strip() == "Extra"
            gauge_lines.append((line, col, rt_local, is_extra))

        if gauge_lines:
            # Pad only to longest gauge line (NOT to W — that adds too much trailing space)
            max_len = max(len(text) for text, _, _, _ in gauge_lines)
            print("---")
            for text, col, rt_local, is_extra in gauge_lines:
                padded = text.ljust(max_len)
                col_attr = f"color={col} " if col else ""
                print(f"{padded} | {col_attr}size=13 font=Menlo")
                if is_extra and eu:
                    spent = eu.get("used_credits")
                    limit = eu.get("monthly_limit")
                    enabled = eu.get("is_enabled", False)
                    status = "ON" if enabled else "OFF"
                    if spent is not None:
                        print(f"--Spent: ${spent / 100:.2f} | {ROW2}")
                    if limit is not None:
                        print(f"--Limit: ${limit / 100:.0f}/mo | {DIM}")
                    print(f"--Status: {status} | {DIM}")
                elif rt_local:
                    print(f"--{t('reset')}: {rt_local} | {DIM}")

    # ═══ 1b. USAGE STATUS HINTS (only when NO data at all) ═══
    HINT = "color=#888888 size=11"
    if not usage and usage_err:
        hint = t("no_token") if usage_err == "no_token" else t("api_error")
        print(f"{hint} | {HINT}")

    # ═══ 1c. FIRST-USE GUIDE ═══
    if ts == 0:
        print(f"{t('first_use')} | {HINT}")

    # Section title style
    ST = "color=#6B6560 size=11" if DARK else "color=#3C4050 size=11"

    # ═══ 2. TODAY ═══
    if today["msgs"] > 0:
        print("---")
        today_label = t("today")
        # Trend vs recent average (active days in last 30d, excluding today)
        today_str_local = datetime.now().strftime("%Y-%m-%d")
        recent_days = [(d, v) for d, v in daily_sorted
                       if d != today_str_local
                       and d >= (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                       and v["cost"] > 0]
        trend = ""
        trend_avg = 0
        if recent_days:
            avg_cost = sum(v["cost"] for _, v in recent_days) / len(recent_days)
            avg_msgs = sum(v["msgs"] for _, v in recent_days) / len(recent_days)
            # Suppress trend when today's activity < 30% of daily average
            if avg_cost > 0 and (avg_msgs <= 0 or today["msgs"] / avg_msgs >= 0.3):
                pct_change = (today["cost"] - avg_cost) / avg_cost * 100
                if pct_change >= 1:
                    trend = f" ↑{pct_change:.0f}%"
                    trend_avg = avg_cost
        print(f"── {today_label} ── | {ST}")
        print(f"⚡ {fc(today['cost'])} · {today['msgs']} {t('msgs')}{trend} | {SEC}")
        if trend and trend_avg > 0:
            print(f"--{t('trend_vs')} {fc(trend_avg)} | {DIM}")
        # Token details in submenu
        print(f"--{t('input')}: {tk(today['inp'])}   {t('output')}: {tk(today['out'])} | {DIM}")
        print(f"--{t('cache_w')}: {tk(today['cw'])}   {t('cache_r')}: {tk(today['cr'])} | {DIM}")
        if today["models"]:
            print("-----")
            tm_total = max(sum(v["msgs"] for v in today["models"].values()), 1)
            for model, data in sorted(today["models"].items(), key=lambda x: -x[1]["cost"]):
                short = MODEL_SHORT.get(model, model)
                pct = data["msgs"] / tm_total * 100
                print(f"--{short}: {data['msgs']:,} ({pct:.0f}%) {fc(data['cost'])} | {MODL}")

    # ═══ 3. OVERVIEW ═══
    print("---")
    dmin_all = min((m["d_min"] for m in machines if m["d_min"]), default=None)
    dmax_all = max((m["d_max"] for m in machines if m["d_max"]), default=None)
    rng_label = f"{dmin_all[5:]}~{dmax_all[5:]}" if dmin_all and dmax_all else ""
    overview_title = t("overview")
    if rng_label:
        print(f"── {overview_title} ({rng_label}) ── | {ST}")
    else:
        print(f"── {overview_title} ── | {ST}")
    print(f"{rj('Cost:', fc(tc))} | {ROW}")
    print(f"{rj('Sessions:', f'{ts:,}')} | {ROW}")
    print(f"{rj('Tokens:', tk(ta))} | {ROW}")
    print(f"--{t('input')}: {tk(ti):>10}   {t('output')}: {tk(to):>10} | {DIM}")
    print(f"--{t('cache_w')}: {tk(tw):>8}   {t('cache_r')}: {tk(tr):>8} | {DIM}")

    # ═══ 4. SUBSCRIPTION ROI (stays as one line) ═══
    sub = CFG.get("subscription", 0)
    if sub > 0:
        lbl = CFG.get("subscription_label", "")
        prefix = f"{lbl} " if lbl else ""
        if dmin_all:
            first = datetime.strptime(dmin_all, "%Y-%m-%d")
            months_active = max((datetime.now() - first).days / 30.0, 1)
        else:
            months_active = 1
        total_paid = sub * months_active
        savings = tc - total_paid
        multiplier = tc / total_paid
        GOLD = "color=#D4A04A size=13" if DARK else "color=#8B6914 size=13"
        print(f"💰 {prefix}${sub:.0f}/mo · {t('saved')} {fc(savings)} ({multiplier:.0f}x) | {GOLD}")
        print(f"--{t('api_equiv')}: {fc(tc)} | {ROW2}")
        if dmin_all:
            total_days = max((datetime.now() - datetime.strptime(dmin_all, "%Y-%m-%d")).days + 1, 1)
            daily_avg = tc / total_days
            monthly_proj = daily_avg * 30
            print(f"--Daily: {fc(daily_avg)} · Monthly: {fc(monthly_proj)} | {DIM}")
        roi_note = t("roi_note").format(m=months_active, s=sub, p=total_paid, tc=fc(tc), x=multiplier)
        print(f"--{roi_note} | {DIM}")

    # ═══ 5. MACHINES ═══
    print("---")
    devices_label = t("devices")
    if machine_count > 1:
        sync_str = {"icloud": "iCloud", "custom": "Custom"}.get(SYNC_TYPE, "")
        suffix = f" ({machine_count} mac · {sync_str})" if sync_str else f" ({machine_count} mac)"
        print(f"── {devices_label}{suffix} ── | {ST}")

    for m in machines:
        ma = m["inp"] + m["out"] + m["cw"] + m["cr"]
        if machine_count == 1:
            icon_m = "💻"
        else:
            icon_m = "●" if m["local"] else "○"
        print(f"{icon_m} {m['label']}  {fc(m['cost'])} | {SEC}")

        # Submenu: machine details + stale detection
        if m["local"]:
            print(f"--{t('live')} | {DIM}")
        elif m.get("at"):
            stale_tag = ""
            try:
                _sync_dt = datetime.strptime(m["at"], "%Y-%m-%d %H:%M:%S")
                _sync_age = (datetime.now() - _sync_dt).days
                if _sync_age >= 7:
                    stale_tag = f" ({_sync_age}d)"
            except Exception: pass
            print(f"--{t('synced')} {m['at']}{stale_tag} | {DIM}")
        print(f"--Token: {tk(ma)} · Sessions: {m['sessions']} | {ROW2}")
        print(f"--{t('input')}: {tk(m['inp'])}   {t('output')}: {tk(m['out'])} | {DIM}")
        print(f"--{t('cache_w')}: {tk(m['cw'])}   {t('cache_r')}: {tk(m['cr'])} | {DIM}")
        mb = m.get("models", {})
        if mb:
            print("-----")
            mtotal = max(sum(v["msgs"] for v in mb.values()), 1)
            for model, data in sorted(mb.items(), key=lambda x: -x[1]["cost"]):
                short = MODEL_SHORT.get(model, model)
                pct = data["msgs"] / mtotal * 100
                print(f"--{short}: {pct:.0f}% · {fc(data['cost'])} | {MODL}")
        dr = f"{m['d_min'][5:]} ~ {m['d_max'][5:]}" if m["d_min"] and m["d_max"] else "N/A"
        print(f"--{dr} | {META}")

    print("---")

    # ═══════════════════════════════════════════════════════════════
    # DRILL-DOWN — clean, minimal, data-focused
    # ═══════════════════════════════════════════════════════════════

    # Helper script path (defined early — used by Details and Settings)
    helper = str(Path.home() / ".config" / "cc-token-stats" / ".toggle.sh")

    # ── Details ──
    SH = "color=#5CC6A7 size=12" if DARK else "color=#1A5C4C size=12"
    details_label = t("details")
    print(f"── {details_label} ── | {ST}")

    # Daily Details (newest first, max 15 visible, older folded)
    all_total_cost = sum(v["cost"] for v in daily.values())
    all_total_msgs = sum(v["msgs"] for v in daily.values())
    active_days = [(d, v) for d, v in reversed(daily_sorted) if v["msgs"] > 0]
    print(f"{t('daily')} | {SH}")
    all_total_tokens = sum(v["tokens"] for v in daily.values())
    for date, data in active_days[:15]:
        dd = date[5:]
        print(f"--{dd}   {fc(data['cost']):>8}   {tk(data['tokens']):>8}   {data['msgs']:>5} msgs | {ROW2}")
    if len(active_days) > 15:
        older = active_days[15:]
        older_cost = sum(v["cost"] for _, v in older)
        older_tokens = sum(v["tokens"] for _, v in older)
        older_msgs = sum(v["msgs"] for _, v in older)
        print(f"--{t('older')} ({len(older)}d) {fc(older_cost)} · {tk(older_tokens)} · {older_msgs} msgs | {DIM}")
        for date, data in older:
            dd = date[5:]
            print(f"----{dd}   {fc(data['cost']):>8}   {tk(data['tokens']):>8}   {data['msgs']:>5} msgs | {ROW2}")
    print("-----")
    total_label = t("total")
    print(f"--{total_label}   {fc(all_total_cost):>8}   {tk(all_total_tokens):>8}   {all_total_msgs:>5} msgs | {DIM}")

    # Models
    print(f"{t('models')} | {SH}")
    for model, data in sorted(all_models.items(), key=lambda x: -x[1]["cost"]):
        short = MODEL_SHORT.get(model, model)
        pct = data["msgs"] / total_model_msgs * 100
        print(f"--{short:<12} {pct:>3.0f}%   {fc(data['cost']):>8}   {data['msgs']:>6,} msgs | {ROW2}")

    # Hourly Activity
    hourly_local = local["hourly"]
    if hourly_local:
        print(f"{t('hours')} | {SH}")
        total_hourly = max(sum(hourly_local.values()), 1)
        max_h = max(hourly_local.values()) if hourly_local else 1
        sparks = " ▁▂▃▄▅▆▇█"
        def spark(h):
            v = hourly_local.get(h, 0)
            if v == 0: return "▁"
            level = min(int(v / max_h * 8) + 1, 8)
            return sparks[level]
        block_defs = [
            (t("am"),   "06–12", range(6, 12)),
            (t("pm"),   "12–18", range(12, 18)),
            (t("eve"),  "18–24", range(18, 24)),
            (t("late"), "00–06", range(0, 6)),
        ]
        for label, time_str, hours_range in block_defs:
            count = sum(hourly_local.get(h, 0) for h in hours_range)
            if count == 0: continue
            pct = count / total_hourly * 100
            sparkline = "".join(spark(h) for h in hours_range)
            msgs_u = t("msgs")
            print(f"--{label} {time_str}  {sparkline}  {count:>5,} {msgs_u} {pct:>2.0f}% | {ROW2}")

    # Top Projects
    projects_local = dict(local["projects"])
    if projects_local:
        print(f"{t('projects')} | {SH}")
        top = sorted(projects_local.items(), key=lambda x: -x[1]["cost"])[:8]
        for name, data in top:
            short_name = f"{name[:14]:<14}" if len(name) <= 14 else f"{name[:13]}…"
            print(f"--{short_name}  {fc(data['cost']):>8}   {tk(data['tokens']):>8}   {data['msgs']:>5} msgs | {ROW2}")

    # Dashboard link
    print(f"{t('report')} | bash={helper} param1=dashboard terminal=false {SH}")

    # ═══ USER LEVEL ═══
    print("---")
    level_title = t("level")
    print(f"── {level_title} ── | {ST}")
    try:
        _score, _lvl, _det = calc_user_level()
        _icon = LEVELS[_lvl][1]
        _en_name = LEVELS[_lvl][2]
        _zh_name = LEVELS[_lvl][3]
        _name = _zh_name if LANG == "zh" else _en_name
        _next_threshold = LEVELS[_lvl + 1][0] if _lvl < len(LEVELS) - 1 else None

        # Experience bar within current level
        _cur_threshold = LEVELS[_lvl][0]
        _next_t = LEVELS[_lvl + 1][0] if _lvl < len(LEVELS) - 1 else 100
        _progress = (_score - _cur_threshold) / max(_next_t - _cur_threshold, 1)
        _exp_bar = bar(_progress * 10, 10, 8)
        print(f"{_icon} Lv.{_lvl+1} {_name} {_exp_bar} | {SEC}")

        # Submenu: dimension breakdown
        dim_names = {"usage": t("dim_usage"), "context": t("dim_context"),
                     "tools": t("dim_tools"), "automation": t("dim_auto"),
                     "scale": t("dim_scale")}
        for k, label in dim_names.items():
            v = _det.get(k, 0)
            b = bar(v, 20, 5)
            print(f"--{label:<10} {b} {v:>2}/20 | {ROW2}")

        if _next_threshold:
            _gap = _next_threshold - _score
            _next_icon = LEVELS[_lvl + 1][1]
            _next_name = LEVELS[_lvl + 1][3] if LANG == "zh" else LEVELS[_lvl + 1][2]
            next_label = t("next_level")
            print(f"--{next_label}: {_next_icon} Lv.{_lvl+2} {_next_name} (+{_gap}) | {DIM}")
    except Exception: pass

    # ═══════════════════════════════════════════════════════════════
    # OPERATIONS (separated from data by ---)
    # ═══════════════════════════════════════════════════════════════
    print("---")

    # Notification toggle
    notify_on = CFG.get("notifications", True)
    notify_icon = "✓ " if notify_on else "  "
    notify_label = f"{notify_icon} {t('notify')}"
    toggle_val = "False" if notify_on else "True"  # Python bool, not JSON
    # Write a tiny helper script for SwiftBar to execute
    # Find plugin path for touch-refresh
    _plugin_path = ""
    try:
        _pd = subprocess.run(["defaults","read","com.ameba.SwiftBar","PluginDirectory"],
                             capture_output=True, text=True, timeout=3).stdout.strip()
        if _pd: _plugin_path = os.path.join(_pd, "cc-token-stats.5m.py")
    except Exception: pass
    if not _plugin_path:
        _plugin_path = os.path.join(str(Path.home()), "Library", "Application Support",
                                    "SwiftBar", "plugins", "cc-token-stats.5m.py")

    try:
        Path(helper).parent.mkdir(parents=True, exist_ok=True)
        _escaped_plugin = shlex.quote(_plugin_path)
        _escaped_config = str(CONFIG_FILE).replace("'", "'\\''")
        Path(helper).write_text(f"""#!/bin/bash
PLUGIN={_escaped_plugin}

case "$1" in
  notify)
    python3 - <<'PYEOF'
import json, pathlib
p = pathlib.Path('{_escaped_config}')
c = json.loads(p.read_text())
c["notifications"] = {toggle_val}
p.write_text(json.dumps(c, indent=2))
PYEOF
    ;;
  login-add)
    osascript -e 'tell application "System Events" to make login item at end with properties {{path:"/Applications/SwiftBar.app", hidden:false}}'
    sleep 1
    ;;
  login-remove)
    osascript -e 'tell application "System Events" to delete login item "SwiftBar"'
    sleep 1
    ;;
  autoupdate)
    python3 - <<'PYEOF'
import json, pathlib
p = pathlib.Path('{_escaped_config}')
c = json.loads(p.read_text())
c["auto_update"] = not c.get("auto_update", True)
p.write_text(json.dumps(c, indent=2))
PYEOF
    ;;
  sub)
    python3 - "$2" "$3" <<'PYEOF'
import json, pathlib, sys
p = pathlib.Path('{_escaped_config}')
c = json.loads(p.read_text())
c["subscription"] = int(sys.argv[1])
c["subscription_label"] = sys.argv[2]
p.write_text(json.dumps(c, indent=2))
PYEOF
    ;;
  dashboard)
    python3 {_escaped_plugin} --dashboard
    ;;
esac
""")
        os.chmod(helper, 0o755)
    except Exception: pass

    # ⚙️ Settings — all toggles collapsed into one submenu
    settings_label = t("settings")
    print(f"{settings_label} | size=13")

    # Notification toggle
    print(f"--{notify_label} | bash={helper} param1=notify terminal=false refresh=true")

    # Launch at login toggle
    try:
        login_items = subprocess.run(["osascript", "-e", 'tell application "System Events" to get the name of every login item'], capture_output=True, text=True, timeout=5).stdout
        login_on = "SwiftBar" in login_items
    except Exception: login_on = False
    login_icon = "✓ " if login_on else "  "
    login_label = f"{login_icon} {t('login')}"
    login_action = "login-remove" if login_on else "login-add"
    print(f"--{login_label} | bash={helper} param1={login_action} terminal=false refresh=true")

    # Auto-update toggle
    update_on = CFG.get("auto_update", True)
    update_icon = "✓ " if update_on else "  "
    update_label = f"{update_icon} {t('auto_upd')}"
    print(f"--{update_label} | bash={helper} param1=autoupdate terminal=false refresh=true")

    # Subscription plan selector
    cur_sub = CFG.get("subscription", 0)
    plans = [("Pro", 20), ("Max 5x", 100), ("Max 20x", 200), ("Team", 30), ("API / None", 0)]
    plan_title = t("subscription")
    cur_name = next((name for name, price in plans if price == cur_sub), f"${cur_sub}")
    print(f"--{plan_title}: {cur_name} | size=13")
    for name, price in plans:
        check = "✓ " if price == cur_sub else "  "
        label_short = name.split(" ")[0] if " " in name else name
        print(f"----{check}{name} (${price}/mo) | bash={helper} param1=sub param2={price} param3={label_short} terminal=false refresh=true")

    # Refresh and Quit — same level as settings, below separator
    print("---")
    print(f"{t('refresh')} | refresh=true")
    quit_label = t("quit")
    print(f"{quit_label} | bash='osascript' param1='-e' param2='quit app \"SwiftBar\"' terminal=false")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--dashboard":
        try:
            path = generate_dashboard()
            subprocess.run(["open", path])
        except Exception as e:
            print(f"Dashboard error: {e}", file=sys.stderr)
        sys.exit(0)
    try:
        main()
    except Exception:
        # Never crash — show basic menu bar item on any error
        print("CC")
        print("---")
        print("Error occurred | color=red")
        print("Click Refresh to retry | refresh=true")
