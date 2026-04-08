#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>
# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>

"""
cc-token-stats — Peek at your Claude Code token usage from the menu bar.
https://github.com/echowonderfulworld/cc-token-stats
"""

import json, os, glob, socket, subprocess
from datetime import datetime
from pathlib import Path

# ─── Config ──────────────────────────────────────────────────────

CONFIG_FILE = Path.home() / ".config" / "cc-token-stats" / "config.json"
ICLOUD_SYNC_DIR = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "cc-token-stats"

DEFAULTS = {
    "claude_dir": str(Path.home() / ".claude"),
    "sync_repo": "", "sync_mode": "auto",
    "subscription": 0, "subscription_label": "",
    "language": "auto", "machine_labels": {},
    "menu_bar_icon": "sfSymbol=sparkles.rectangle.stack",
}

def load_config():
    cfg = dict(DEFAULTS)
    if CONFIG_FILE.is_file():
        try:
            with open(CONFIG_FILE) as f: cfg.update(json.load(f))
        except: pass
    for ek, ck in [("CC_STATS_CLAUDE_DIR","claude_dir"),("CC_STATS_SYNC_REPO","sync_repo"),("CC_STATS_LANG","language")]:
        if os.environ.get(ek): cfg[ck] = os.environ[ek]
    if os.environ.get("CC_STATS_SUBSCRIPTION"):
        try: cfg["subscription"] = float(os.environ["CC_STATS_SUBSCRIPTION"])
        except: pass
    if cfg["language"] == "auto":
        try:
            out = subprocess.check_output(["defaults","read",".GlobalPreferences","AppleLanguages"], stderr=subprocess.DEVNULL, text=True)
            cfg["language"] = "zh" if "zh" in out.lower() else "en"
        except: cfg["language"] = "en"
    return cfg

CFG = load_config()
ZH = CFG["language"] == "zh"
MACHINE = socket.gethostname().split(".")[0]
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

PRICING = {
    "opus":{"input":15,"output":75,"cache_write":18.75,"cache_read":1.50},
    "sonnet":{"input":3,"output":15,"cache_write":3.75,"cache_read":0.30},
    "haiku":{"input":0.80,"output":4,"cache_write":1.00,"cache_read":0.08},
}
MODEL_SHORT = {
    "claude-opus-4-6":"Opus 4.6","claude-opus-4-5-20250918":"Opus 4.5",
    "claude-sonnet-4-6":"Sonnet 4.6","claude-sonnet-4-5-20250929":"Sonnet 4.5",
    "claude-haiku-4-5-20251001":"Haiku 4.5",
}

def dw(s):
    return sum(2 if ord(c)>0x2E7F else 1 for c in s)

def tk(n):
    if ZH:
        if n>=1e8: return f"{n/1e8:.2f} 亿"
        if n>=1e4: return f"{n/1e4:.1f} 万"
    else:
        if n>=1e9: return f"{n/1e9:.2f}B"
        if n>=1e6: return f"{n/1e6:.1f}M"
        if n>=1e3: return f"{n/1e3:.1f}K"
    return f"{n:,}"

def fc(n):
    return f"${n:,.0f}" if n>=10000 else f"${n:,.2f}"

def tier(m):
    m=m.lower()
    if "opus" in m: return "opus"
    if "haiku" in m: return "haiku"
    return "sonnet"

def mlabel(h):
    labels = CFG.get("machine_labels",{})
    if h in labels: return labels[h]
    hl = h.lower()
    if "mac" in hl and ("mini" in hl or "home" in hl): return "🏠 Home" if not ZH else "🏠 家里"
    if any(x in hl for x in ["office","work","corp"]): return "🏢 Office" if not ZH else "🏢 办公室"
    return f"💻 {h}"

# ─── Data ────────────────────────────────────────────────────────

def scan():
    base = os.path.join(CLAUDE_DIR,"projects")
    s = {"machine":MACHINE,"sessions":0,"inp":0,"out":0,"cw":0,"cr":0,
         "cost":0.0,"d_min":None,"d_max":None,"models":{}}
    if not os.path.isdir(base): return s
    for pd in glob.glob(os.path.join(base,"*")):
        if not os.path.isdir(pd): continue
        for jf in glob.glob(os.path.join(pd,"*.jsonl")):
            has=False
            try: fd=datetime.fromtimestamp(os.path.getmtime(jf)).strftime("%Y-%m-%d")
            except: fd=None
            try:
                with open(jf,"r",encoding="utf-8") as f:
                    for line in f:
                        try:
                            d=json.loads(line)
                            if d.get("type")!="assistant": continue
                            msg=d.get("message",{})
                            if not isinstance(msg,dict): continue
                            u=msg.get("usage")
                            if not u: continue
                            i,o,w,r=u.get("input_tokens",0),u.get("output_tokens",0),u.get("cache_creation_input_tokens",0),u.get("cache_read_input_tokens",0)
                            s["inp"]+=i;s["out"]+=o;s["cw"]+=w;s["cr"]+=r;has=True
                            m=msg.get("model","")
                            p=PRICING.get(tier(m),PRICING["sonnet"])
                            mc=(i*p["input"]+o*p["output"]+w*p["cache_write"]+r*p["cache_read"])/1e6
                            s["cost"]+=mc
                            if m and m!="<synthetic>":
                                if m not in s["models"]: s["models"][m]={"msgs":0,"tokens":0,"cost":0.0}
                                s["models"][m]["msgs"]+=1;s["models"][m]["tokens"]+=i+o+w+r;s["models"][m]["cost"]+=mc
                        except: pass
                if has:
                    s["sessions"]+=1
                    if fd:
                        if not s["d_min"] or fd<s["d_min"]: s["d_min"]=fd
                        if not s["d_max"] or fd>s["d_max"]: s["d_max"]=fd
            except: pass
    return s

def save_sync(st):
    if not SYNC_DIR: return
    d=os.path.join(SYNC_DIR,"machines",MACHINE)
    try:
        os.makedirs(d,exist_ok=True)
        mb={m:{**v,"cost":round(v["cost"],2)} for m,v in st.get("models",{}).items()}
        json.dump({"machine":MACHINE,"generated_at":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "session_count":st["sessions"],"input_tokens":st["inp"],"output_tokens":st["out"],
            "cache_write_tokens":st["cw"],"cache_read_tokens":st["cr"],
            "total_cost":round(st["cost"],2),"date_range":{"min":st["d_min"],"max":st["d_max"]},
            "model_breakdown":mb},open(os.path.join(d,"token-stats.json"),"w"),indent=2)
    except: pass

def load_remotes():
    remotes=[]
    if not SYNC_DIR: return remotes
    md=os.path.join(SYNC_DIR,"machines")
    if not os.path.isdir(md): return remotes
    for m in os.listdir(md):
        if m==MACHINE: continue
        sf=os.path.join(md,m,"token-stats.json")
        if os.path.isfile(sf):
            try: remotes.append(json.load(open(sf)))
            except: pass
    return remotes

# ─── Render ──────────────────────────────────────────────────────

# Styles
H1  = "color=#4EC9B0 size=14"
ROW = "color=#E0D8C8 size=13 font=Menlo"
DIM = "color=#9B9080 size=11 font=Menlo"
META= "color=#6B6560 size=10"
SEC = "color=#7AAFCF size=13"
MODL= "color=#8B8578 size=11 font=Menlo"

def main():
    local = scan()
    save_sync(local)
    remotes = load_remotes()

    # Build machine list
    machines = [{
        "label":mlabel(MACHINE),"sessions":local["sessions"],
        "inp":local["inp"],"out":local["out"],"cw":local["cw"],"cr":local["cr"],
        "cost":local["cost"],"d_min":local["d_min"],"d_max":local["d_max"],
        "local":True,"at":None,"models":local.get("models",{}),
    }]
    for r in remotes:
        dr=r.get("date_range",{})
        machines.append({
            "label":mlabel(r.get("machine","?")),"sessions":r.get("session_count",0),
            "inp":r.get("input_tokens",0),"out":r.get("output_tokens",0),
            "cw":r.get("cache_write_tokens",0),"cr":r.get("cache_read_tokens",0),
            "cost":r.get("total_cost",0),"d_min":dr.get("min"),"d_max":dr.get("max"),
            "local":False,"at":r.get("generated_at"),"models":r.get("model_breakdown",{}),
        })

    ti=sum(m["inp"] for m in machines); to=sum(m["out"] for m in machines)
    tw=sum(m["cw"] for m in machines);  tr=sum(m["cr"] for m in machines)
    tc=sum(m["cost"] for m in machines); ts=sum(m["sessions"] for m in machines)
    ta=ti+to+tw+tr
    dmin=min((m["d_min"] for m in machines if m["d_min"]),default="N/A")
    dmax=max((m["d_max"] for m in machines if m["d_max"]),default="N/A")
    now=datetime.now().strftime("%H:%M:%S")
    icon=CFG.get("menu_bar_icon","sfSymbol=sparkles.rectangle.stack")

    # ─── Menu bar ───
    print(f"CC: {tk(ta)} | {icon}")
    print("---")

    # ─── Title ───
    title = "Claude Code Token 统计 (合计)" if ZH else "Claude Code Token Stats (Total)"
    print(f"{title} | {H1}")
    print("---")

    # ─── Summary: aligned rows ───
    if ZH:
        rows = [
            ("总等价费用：", fc(tc)), ("总 Session：", f"{ts:,}"), ("总 Token：", tk(ta)),
            None,
            ("输入：", tk(ti)), ("输出：", tk(to)), ("缓存写入：", tk(tw)), ("缓存读取：", tk(tr)),
        ]
    else:
        rows = [
            ("API Equiv. Cost:", fc(tc)), ("Sessions:", f"{ts:,}"), ("Total Tokens:", tk(ta)),
            None,
            ("Input:", tk(ti)), ("Output:", tk(to)), ("Cache Write:", tk(tw)), ("Cache Read:", tk(tr)),
        ]
    # Global right-alignment: all values end at same column
    max_w = 0
    for r in rows:
        if r is None: continue
        max_w = max(max_w, dw(r[0]) + 1 + dw(r[1]))
    # Ensure wider than title/machine labels
    max_w = max(max_w, dw(title), *(dw(m["label"])+20 for m in machines))
    for r in rows:
        if r is None:
            print("---")
            continue
        l, v = r
        gap = max_w - dw(l) - dw(v)
        print(f"{l}{' '*gap}{v} | {ROW}")
    print("---")

    # ─── Per-machine submenus ───
    for m in machines:
        ma = m["inp"]+m["out"]+m["cw"]+m["cr"]
        if m["local"]:
            suf = " (实时)" if ZH else " (live)"
        elif m.get("at"):
            suf = f" (synced {m['at'][5:16]})" if not ZH else f" (同步于 {m['at']})"
        else:
            suf = ""
        print(f"{m['label']}{suf} | {SEC}")

        # Submenu
        if ZH:
            print(f"--等价费用: {fc(m['cost'])} | {ROW}")
            print(f"--Token: {tk(ma)} | {ROW}")
            print(f"--Sessions: {m['sessions']} | {ROW}")
            print("-----")
            print(f"--输入: {tk(m['inp'])}   输出: {tk(m['out'])} | {DIM}")
            print(f"--缓存写: {tk(m['cw'])}   缓存读: {tk(m['cr'])} | {DIM}")
        else:
            print(f"--Cost: {fc(m['cost'])} | {ROW}")
            print(f"--Tokens: {tk(ma)} | {ROW}")
            print(f"--Sessions: {m['sessions']} | {ROW}")
            print("-----")
            print(f"--Input: {tk(m['inp'])}   Output: {tk(m['out'])} | {DIM}")
            print(f"--Cache W: {tk(m['cw'])}   Cache R: {tk(m['cr'])} | {DIM}")

        mb = m.get("models",{})
        if mb:
            print("-----")
            total_msgs = max(sum(v["msgs"] for v in mb.values()),1)
            for model,data in sorted(mb.items(), key=lambda x:-x[1]["cost"]):
                short = MODEL_SHORT.get(model, model)
                pct = data["msgs"]/total_msgs*100
                print(f"--{short}: {data['msgs']:,} ({pct:.0f}%) {fc(data['cost'])} | {MODL}")

        dr = f"{m['d_min']} ~ {m['d_max']}" if m["d_min"] and m["d_max"] else "N/A"
        print("-----")
        if ZH:
            print(f"--范围: {dr} | {META}")
        else:
            print(f"--Range: {dr} | {META}")

    # ─── Footer ───
    print("---")
    rng = f"{dmin[5:]} ~ {dmax[5:]}" if dmin!="N/A" else "N/A"
    sync_str = {"icloud":"iCloud","custom":"Custom"}.get(SYNC_TYPE,"")
    parts = [rng, f"{len(machines)}{'台' if ZH else ' machines'}", now]
    if sync_str: parts.insert(2, sync_str)
    print(f"{' · '.join(parts)} | {META}")

    sub = CFG.get("subscription",0)
    if sub > 0:
        lbl = CFG.get("subscription_label","")
        pf = f"{lbl} " if lbl else ""
        sv = tc - sub
        if ZH:
            print(f"{pf}${sub:.0f}/月 → 已节省 {fc(sv)} | {META}")
        else:
            print(f"{pf}${sub:.0f}/mo → saved {fc(sv)} | {META}")

    print("---")
    print("Refresh | refresh=true")
    quit_label = "退出 SwiftBar" if ZH else "Quit SwiftBar"
    print(f"{quit_label} | bash='osascript' param1='-e' param2='quit app \"SwiftBar\"' terminal=false")

if __name__ == "__main__":
    main()
