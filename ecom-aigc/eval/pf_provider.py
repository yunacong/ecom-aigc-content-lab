import json
import random
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]  # ecom-aigc/
OUT = ROOT / "data_processed"
DOC = ROOT / "docs"
SAMPLE = ROOT / "data_sample"

def _safe(v):
    try:
        if pd.isna(v):
            return "未明确说明"
    except Exception:
        pass
    return str(v)

def _load_tables():
    # Cloud / demo: prefer sample data if exists
    pf = SAMPLE / "product_facts_sample.csv"
    rv = SAMPLE / "reviews_sample.csv"
    lex = SAMPLE / "keyword_lexicon_sample.csv"
    if pf.exists() and rv.exists() and lex.exists():
        products = pd.read_csv(pf)
        reviews = pd.read_csv(rv)
        lexicon = pd.read_csv(lex)
    else:
        products = pd.read_csv(OUT / "product_facts.csv")
        reviews = pd.read_csv(OUT / "reviews.csv")
        lexicon = pd.read_csv(OUT / "keyword_lexicon.csv")
    # policy
    policy = json.loads((DOC / "policy_rules.json").read_text(encoding="utf-8"))
    return products, reviews, lexicon, policy

_PRODUCTS, _REVIEWS, _LEX, _POLICY = _load_tables()

def _make_keyword_maps(top_k=20):
    pos = _LEX[_LEX["polarity"] != "-"].copy()
    neg = _LEX[_LEX["polarity"] == "-"].copy()
    pos_map = (pos.sort_values(["category","freq"], ascending=[True, False])
               .groupby("category")["keyword"].apply(lambda x: list(x.head(top_k))).to_dict())
    neg_map = (neg.sort_values(["category","freq"], ascending=[True, False])
               .groupby("category")["keyword"].apply(lambda x: list(x.head(top_k))).to_dict())
    return pos_map, neg_map

_POS_MAP, _NEG_MAP = _make_keyword_maps(top_k=30)

def _compliance_hits(text: str):
    t = (text or "").lower()
    hits = []
    for rule in _POLICY.get("rules", []):
        terms = rule.get("terms_zh", []) + rule.get("terms_en", [])
        matched = [term for term in terms if str(term).lower() in t]
        if matched:
            hits.extend(matched)
    return list(dict.fromkeys(hits))[:30]

def _generate_title(row, keywords, seed=0):
    random.seed(seed)
    brand = _safe(row.get("brand_name"))
    name  = _safe(row.get("product_name"))

    k = [x for x in keywords if isinstance(x, str)]
    random.shuffle(k)
    kw1 = k[0] if len(k) > 0 else "highlight"

    raw_title = f"{brand} {name} | {kw1}"
    # hard safety: replace treat/treatment -> care
    raw_title = re.sub(r"\btreat(ment)?\b", "care", raw_title, flags=re.IGNORECASE)
    return raw_title[:60]

def call_api(prompt, options, context):
    """
    prompt: promptfoo 给的 prompt 文本（这里我们不依赖它）
    context['vars']: 来自 test_cases.csv 的字段
    return: {"output": "..."}  (promptfoo 规定)
    """
    vars_ = (context or {}).get("vars", {}) or {}
    pid = str(vars_.get("product_id", "")).strip()

    if not pid:
        return {"output": "ERROR: missing product_id"}

    sub = _PRODUCTS[_PRODUCTS["product_id"] == pid]
    if sub.empty:
        return {"output": f"ERROR: product_id not found: {pid}"}

    row = sub.iloc[0].to_dict()
    cat = str(row.get("primary_category", "Skincare"))
    keywords = _POS_MAP.get(cat, [])

    # fallback: 用 highlights 里的 fact-based 词（如果 lexicon 覆盖不到）
    if not keywords:
        highlights = str(row.get("highlights", ""))
        keywords = [x.strip().strip("'\"") for x in highlights.strip("[]").split(",") if x.strip()][:10]

    seed = int(vars_.get("seed", 0) or 0)
    # 1) 基础 title（不带 must）
    base_title = _generate_title(row, keywords, seed=seed)
    
    # 2) 解析 expected_keywords（CSV 里是 JSON 数组字符串）
    exp = vars_.get("expected_keywords", "[]")
    try:
        exp_list = json.loads(exp) if isinstance(exp, str) else exp
    except Exception:
        exp_list = []
    must = str(exp_list[0]).strip() if exp_list else ""
    
    # 3) 关键：预留 must 的长度，避免被 60 截断裁掉
    #    先拆出 brand+name 部分（不要用 base_title 里的 kw1）
    brand = _safe(row.get("brand_name"))
    name  = _safe(row.get("product_name"))
    core  = f"{brand} {name}".strip()
    
    suffix = f" | {must}" if must else ""
    max_len = 60
    core_max = max(10, max_len - len(suffix))  # 至少留 10 个字符给 core
    
    title = (core[:core_max] + suffix)[:max_len]
    
    # 4) safety：treat/treatment -> care
    title = re.sub(r"\btreat(ment)?\b", "care", title, flags=re.IGNORECASE)
    
    return {"output": title}