import numpy as np
import json
import re
import random
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------- Paths ----------------
ROOT = Path(__file__).resolve().parents[1]   # ecom-aigc/
OUT = ROOT / "data_processed"
DOC = ROOT / "docs"
SAMPLE = ROOT / "data_sample"

# ---------------- Load data (cached) ----------------
@st.cache_data
def load_data():
    # prefer sample data on cloud
    pf_path = SAMPLE / "product_facts_sample.csv"
    rv_path = SAMPLE / "reviews_sample.csv"
    lex_path = SAMPLE / "keyword_lexicon_sample.csv"

    if pf_path.exists() and rv_path.exists() and lex_path.exists():
        products = pd.read_csv(pf_path)
        reviews = pd.read_csv(rv_path)
        lex = pd.read_csv(lex_path)
    else:
        products = pd.read_csv(OUT / "product_facts.csv")
        reviews = pd.read_csv(OUT / "reviews.csv")
        lex = pd.read_csv(OUT / "keyword_lexicon.csv")

    lex_pos = lex[lex["polarity"] != "-"].copy()
    lex_neg = lex[lex["polarity"] == "-"].copy()
    policy = json.loads((DOC / "policy_rules.json").read_text(encoding="utf-8"))
    return products, reviews, lex_pos, lex_neg, policy
def safe(v):
    if pd.isna(v):
        return "未明确说明"
    return str(v)

def build_fact_sheet(row):
    lines = [
        f"product_id: {safe(row.get('product_id'))}",
        f"brand_name: {safe(row.get('brand_name'))}",
        f"product_name: {safe(row.get('product_name'))}",
        f"category: {safe(row.get('primary_category'))} / {safe(row.get('secondary_category'))} / {safe(row.get('tertiary_category'))}",
        f"price_usd: {safe(row.get('price_usd'))}",
        f"sale_price_usd: {safe(row.get('sale_price_usd'))}",
        f"rating_avg: {safe(row.get('rating_avg'))}",
        f"review_cnt: {safe(row.get('review_cnt'))}",
        f"ingredients: {safe(row.get('ingredients'))}",
        f"highlights: {safe(row.get('highlights'))}",
    ]
    return "\n".join(lines)

def sample_review_evidence(reviews_df, pid, n=8):
    sub = reviews_df.loc[reviews_df["product_id"] == pid, "review_text"].dropna()
    if len(sub) == 0:
        return []
    return random.sample(list(sub), min(n, len(sub)))

def make_keyword_maps(lex_pos, lex_neg, top_k=30):
    pos_map = (lex_pos.sort_values(["category","freq"], ascending=[True, False])
               .groupby("category")["keyword"].apply(lambda x: list(x.head(top_k))).to_dict())
    neg_map = (lex_neg.sort_values(["category","freq"], ascending=[True, False])
               .groupby("category")["keyword"].apply(lambda x: list(x.head(top_k))).to_dict())
    return pos_map, neg_map

def compliance_check(policy, text: str):
    t_low = text.lower()
    violations = []
    for rule in policy["rules"]:
        terms = rule.get("terms_zh", []) + rule.get("terms_en", [])
        hits = [term for term in terms if term.lower() in t_low]
        if hits:
            violations.append({
                "rule_id": rule["id"],
                "severity": rule["severity"],
                "matched_terms": hits[:20],
                "suggestion_zh": rule.get("suggestion_zh", "")
            })
    return violations

def keyword_hits(text: str, keywords):
    t = str(text).lower()
    hits = []
    for k in keywords:
        if str(k).lower() in t:
            hits.append(k)
    return sorted(set(hits))

def readability_score(text: str):
    t = str(text).strip()
    score = 100
    if len(t) < 60:
        score -= 10
    if len(t) > 1200:
        score -= 10
    words = re.findall(r"[a-zA-Z']+", t.lower())
    if len(words) >= 30:
        rep_ratio = 1 - (len(set(words)) / len(words))
        if rep_ratio > 0.4:
            score -= 15
    return max(0, score)

def score_bundle(policy, keywords, bundle):
    all_text = " ".join([
        bundle["title"],
        " ".join(bundle["bullets"]),
        bundle["detail"],
        bundle["video"],
    ])
    violations = compliance_check(policy, all_text)
    compliance_score = max(0, 100 - 15 * len(violations))

    hits = keyword_hits(all_text, keywords)
    coverage_score = min(100, len(hits) * 15)

    read_score = readability_score(all_text)
    total = round(0.4*compliance_score + 0.35*coverage_score + 0.25*read_score, 2)

    return {
        "total": total,
        "compliance_score": compliance_score,
        "coverage_score": coverage_score,
        "readability_score": read_score,
        "violations": violations,
        "keyword_hits": hits[:20],
    }

# ---------------- Generation (rule-based demo) ----------------
def generate_variant(row, keywords, risk_terms, seed=0):
    random.seed(seed)
    brand = safe(row.get("brand_name"))
    name  = safe(row.get("product_name"))
    cat   = safe(row.get("primary_category"))

    k = [x for x in keywords if isinstance(x, str)]
    random.shuffle(k)
    kw1 = k[0] if len(k) > 0 else "highlight"
    kw2 = k[1] if len(k) > 1 else "daily"

    raw_title = f"{brand} {name} | {kw1}"
    # avoid medical-like "treat" (replace before slicing)
    raw_title = re.sub(r"treat(ment)?", "care", raw_title, flags=re.IGNORECASE)
    title = raw_title[:60]

    bullets = [
        kw1[:40],
        kw2[:40],
        "absorbs quickly",
        "great for daily routine",
        "patch test if sensitive" if len(risk_terms) > 0 else "easy to use",
    ]
    detail = (
        f"**痛点**：想要更适合{cat}的日常体验？\n"
        f"**解决**：围绕 {kw1} / {kw2} 的使用感描述。\n"
        f"**证据**：关键词参考：{kw1}, {kw2}；评分 {safe(row.get('rating_avg'))}；评论数 {safe(row.get('review_cnt'))}。\n"
        f"**适用**：更适合日常通勤与基础护理。\n"
        f"**注意**：{'敏感肌先局部测试，不适即停用' if len(risk_terms)>0 else '如有不适请停止使用'}"
    )
    video = (
        f"Shot1\nVisual: problem scene\nVoiceover: Need an easier routine?\nOn-screen text: daily\n\n"
        f"Shot2\nVisual: texture + application\nVoiceover: {kw1}, {kw2}, absorbs quickly.\nOn-screen text: {kw1[:20]}\n\n"
        f"Shot3\nVisual: reviews + product\nVoiceover: Many users mention it. {'Patch test if sensitive.' if len(risk_terms)>0 else ''}\nOn-screen text: try"
    )
    return {"title": title, "bullets": bullets, "detail": detail, "video": video}

# ---------------- UI ----------------
st.set_page_config(page_title="Ecom AIGC Content Lab", layout="wide")

# Theme CSS (internet style + gradient hero)
st.markdown("""
<style>
:root{
  --bg:#f7f8fc;
  --card:#ffffff;
  --text:#0f172a;
  --muted:rgba(15,23,42,.62);
  --border:rgba(15,23,42,.10);
  --shadow:0 12px 30px rgba(15,23,42,.10);
  --r:18px;
}
html, body {background: var(--bg) !important;}
.block-container{max-width:1200px; padding-top:1.2rem; padding-bottom:2.2rem;}
h1,h2,h3{letter-spacing:-0.02em; color:var(--text);}

.card{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:16px;
  padding:14px 14px;      /* 18 -> 14 */
  box-shadow: var(--shadow);
}
.card-title{
  font-weight:900;
  font-size:16px;         /* 14 -> 16 */
  color:rgba(15,23,42,.78);
  margin-bottom:10px;     /* 12 -> 10 */
}
.muted{color:var(--muted); font-size:12px;}

.hero{
  border-radius:22px;
  padding:18px;
  border:1px solid rgba(99,102,241,.18);
  background: radial-gradient(1200px 260px at 0% 0%, rgba(99,102,241,.28), transparent 55%),
              radial-gradient(900px 220px at 100% 0%, rgba(236,72,153,.22), transparent 55%),
              linear-gradient(180deg, rgba(255,255,255,.95), rgba(255,255,255,.85));
  box-shadow: 0 14px 40px rgba(15,23,42,.12);
}
.hero .label{font-size:12px; color:rgba(15,23,42,.62);}
.hero .big{font-size:28px;}    /* 34 -> 28 */
.hero .score{font-size:36px;}  /* 42 -> 36 */

.kpi-row{display:flex; gap:10px; margin-top:10px;}
.kpi{
  flex:1;
  border-radius:16px;
  border:1px solid rgba(15,23,42,.10);
  background: rgba(255,255,255,.9);
  padding:12px 12px;
}
.kpi .k{font-size:12px; color:rgba(15,23,42,.62);}
.kpi .v{font-size:24px; font-weight:900; margin-top:2px;}

.tag{display:inline-block; padding:6px 10px; border-radius:999px; font-size:12px; margin:6px 8px 0 0; border:1px solid;}
.tag-ok{background:rgba(16,185,129,.10); color:#065f46; border-color:rgba(16,185,129,.25);}
.tag-warn{background:rgba(249,115,22,.10); color:#9a3412; border-color:rgba(249,115,22,.25);}
.tag-bad{background:rgba(239,68,68,.10); color:#991b1b; border-color:rgba(239,68,68,.25);}

.stButton button, .stDownloadButton button{
  border-radius:14px !important;
  padding:10px 14px !important;
  border:1px solid rgba(15,23,42,.14) !important;
  background: white !important;
}
.stDownloadButton button:hover, .stButton button:hover{
  border-color: rgba(99,102,241,.35) !important;
  box-shadow: 0 10px 18px rgba(99,102,241,.12) !important;
}
.stTabs [data-baseweb="tab-list"] button {font-weight:700;}
/* 输入区 hero 卡（和右侧 hero 同一风格） */
.input-hero{
  border-radius:18px;
  padding:12px 14px;           /* 18 -> 14 */
  border:1px solid rgba(99,102,241,.14);
  background: radial-gradient(1000px 240px at 0% 0%, rgba(99,102,241,.18), transparent 55%),
              radial-gradient(900px 220px at 100% 0%, rgba(34,211,238,.14), transparent 55%),
              linear-gradient(180deg, rgba(255,255,255,.95), rgba(255,255,255,.88));
  box-shadow: 0 14px 40px rgba(15,23,42,.10);
}

/* 分隔带：输入→输出的视觉过渡 */
.divider-wrap{
  margin: 14px 0 18px 0;
}
.divider-line{
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(90deg,
      rgba(99,102,241,.0),
      rgba(99,102,241,.35),
      rgba(236,72,153,.28),
      rgba(34,211,238,.22),
      rgba(99,102,241,.0)
  );
  filter: blur(0.2px);
}
.divider-text{
  margin-top: 8px;
  font-size: 12px;
  color: rgba(15,23,42,.62);
  display:flex;
  align-items:center;
  gap:8px;
}
.divider-pill{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(15,23,42,.10);
  background: rgba(255,255,255,.85);
}
.cta .stButton button{
  background: linear-gradient(90deg, rgba(99,102,241,.95), rgba(236,72,153,.90)) !important;
  color: white !important;
  border: none !important;
}
.cta .stButton button:hover{
  filter: brightness(1.03);
}
/* 压缩控件间距，让输入区更紧凑 */
div[data-testid="stVerticalBlock"] > div { margin-bottom: 0.4rem; }
div[data-testid="stForm"] { margin-top: 0.2rem; }
label { font-size: 12px !important; color: rgba(15,23,42,.70) !important; }
</style>
""", unsafe_allow_html=True)

# Load data
products, reviews, lex_pos, lex_neg, policy = load_data()
pos_map, neg_map = make_keyword_maps(lex_pos, lex_neg, top_k=30)

# ===== Header =====
st.title("Ecom AIGC Content Lab — Demo")
st.caption("选择商品 → 多版本生成 → 自动评分/合规 → 导出投放素材包")
tab1, tab2 = st.tabs(["🏠 生成首页", "📊 对比看板"])
with tab2:
    st.markdown('<div class="card"><div class="card-title">对比看板</div>', unsafe_allow_html=True)
    st.write("生成完成后可在对比看板里查看版本对比、失败原因与推荐。")
    if st.button("打开版本对比与选优看板", use_container_width=True):
        st.switch_page("pages/compare.py")
    st.markdown('</div>', unsafe_allow_html=True)

# ===== Input panel under title (NO sidebar) =====

st.markdown('<div class="input-hero"><div class="card-title" style="margin-bottom:4px;">选择输入</div>', unsafe_allow_html=True)
st.markdown('<div class="muted" style="margin-bottom:8px;">选择类目/商品并生成多版本内容</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns([1.2, 2.2, 1.2, 1.0], gap="large")
with c1:
    cats = sorted(products["primary_category"].dropna().unique().tolist())
    cat = st.selectbox("Category", cats, index=0)

sub_products = products[products["primary_category"] == cat].copy().sort_values("review_cnt", ascending=False).head(200)

def label_row(r):
    return f'{r["brand_name"]} | {r["product_name"]} ({r["product_id"]})'

labels = sub_products.apply(label_row, axis=1).tolist()
with c2:
    choice = st.selectbox("Product", labels)

pid = choice.split("(")[-1].replace(")", "").strip()

with c3:
    n = st.slider("生成版本数", min_value=3, max_value=5, value=3)

with c4:
    st.markdown('<div class="cta">', unsafe_allow_html=True)
    run_btn = st.button("生成", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
st.markdown("""
<div class="divider-wrap">
  <div class="divider-line"></div>
  <div class="divider-text">
    <span class="divider-pill">🧩 输入</span>
    <span>→</span>
    <span class="divider-pill">✨ 多版本生成</span>
    <span>→</span>
    <span class="divider-pill">✅ 评分/合规</span>
    <span>→</span>
    <span class="divider-pill">📦 导出</span>
  </div>
</div>
""", unsafe_allow_html=True)
# ===== Run generation =====
if run_btn:
    row = products[products["product_id"] == pid].iloc[0]
    fact_sheet = build_fact_sheet(row)

    keywords = pos_map.get(cat, [])
    risk_terms = neg_map.get(cat, [])

    # fallback: use highlights (fact-based)
    if not keywords:
        highlights = str(row.get("highlights", ""))
        keywords = [x.strip().strip("'") for x in highlights.strip("[]").split(",") if x.strip()][:10]

    evidence = sample_review_evidence(reviews, pid, n=8)

    variants = [generate_variant(row, keywords, risk_terms, seed=i) for i in range(n)]
    scored = [score_bundle(policy, keywords, v) for v in variants]

    st.session_state["pid"] = pid
    st.session_state["row"] = row.to_dict()
    st.session_state["fact_sheet"] = fact_sheet
    st.session_state["keywords"] = keywords[:20]
    st.session_state["risk_terms"] = risk_terms[:20]
    st.session_state["evidence"] = evidence
    st.session_state["variants"] = variants
    st.session_state["scores"] = scored

st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
st.markdown('<div class="muted">输出区（基于事实生成与评测）</div>', unsafe_allow_html=True)
# ===== Row 1: Fact sheet + Generated content =====
col_fs, col_gen = st.columns([1.1, 2.4], gap="large")

with col_fs:
    st.markdown('<div class="card"><div class="card-title">FACT_SHEET</div>', unsafe_allow_html=True)
    if "fact_sheet" in st.session_state:
        st.code(st.session_state["fact_sheet"])
        st.markdown('<div class="muted">仅允许引用 FACT_SHEET 信息（防幻觉约束）</div>', unsafe_allow_html=True)
    else:
        st.info("请先在上方点击「生成」")
    st.markdown('</div>', unsafe_allow_html=True)

with col_gen:
    st.markdown('<div class="card"><div class="card-title">生成内容（多版本）</div>', unsafe_allow_html=True)

    if "variants" not in st.session_state:
        st.info("请先在上方点击「生成」")
    else:
        variants = st.session_state["variants"]
        scores = st.session_state["scores"]
        tabs = st.tabs([f"Variant {i+1} (Score {scores[i]['total']})" for i in range(len(variants))])

        for i, tab in enumerate(tabs):
            with tab:
                v = variants[i]
                t1, t2, t3, t4 = st.tabs(["标题", "卖点", "详情", "短视频脚本"])
                with t1:
                    st.write(v["title"])
                with t2:
                    st.write("\n".join([f"- {b}" for b in v["bullets"]]))
                with t3:
                    st.markdown(v["detail"])
                with t4:
                    st.code(v["video"])

        st.markdown('<div class="muted" style="margin-top:10px;">Export</div>', unsafe_allow_html=True)

        export = {
            "product_id": st.session_state.get("pid"),
            "product": st.session_state.get("row"),
            "keywords": st.session_state.get("keywords"),
            "risk_terms": st.session_state.get("risk_terms"),
            "variants": [
                {"variant_id": f"v{i+1}", "output": variants[i], "score": scores[i]}
                for i in range(len(variants))
            ]
        }
        export_json = json.dumps(export, ensure_ascii=False, indent=2)

        txt_lines = []
        for i, v in enumerate(variants):
            txt_lines.append(f"=== Variant {i+1} ===")
            txt_lines.append(f"Title: {v['title']}")
            txt_lines.append("Bullets:")
            txt_lines.extend([f"- {b}" for b in v["bullets"]])
            txt_lines.append("Detail:")
            txt_lines.append(v["detail"])
            txt_lines.append("Video:")
            txt_lines.append(v["video"])
            txt_lines.append("")
        export_txt = "\n".join(txt_lines)

        b1, b2 = st.columns(2)
        with b1:
            st.download_button("导出投放素材包（JSON）", data=export_json, file_name="ad_pack.json", mime="application/json")
        with b2:
            st.download_button("导出投放素材包（TXT）", data=export_txt, file_name="ad_pack.txt", mime="text/plain")

    st.markdown('</div>', unsafe_allow_html=True)

# ===== Row 2: Scoring & policy (full width) =====
st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
st.markdown('<div class="card"><div class="card-title">评分分解 & 合规</div>', unsafe_allow_html=True)

if "scores" not in st.session_state:
    st.info("生成后显示评分")
else:
    scores = st.session_state["scores"]
    best_i = max(range(len(scores)), key=lambda i: scores[i]["total"])
    s = scores[best_i]

    st.markdown(f'''
    <div class="hero">
      <div class="label">推荐版本</div>
      <div class="big">Variant {best_i+1}</div>
      <div class="label">Total Score</div>
      <div class="score">{s["total"]}</div>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown(f'''
    <div class="kpi-row">
      <div class="kpi"><div class="k">Compliance</div><div class="v">{s["compliance_score"]}</div></div>
      <div class="kpi"><div class="k">Coverage</div><div class="v">{s["coverage_score"]}</div></div>
      <div class="kpi"><div class="k">Readability</div><div class="v">{s["readability_score"]}</div></div>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown('<div class="card-title" style="margin-top:14px;">命中关键词</div>', unsafe_allow_html=True)
    if s["keyword_hits"]:
        for k in s["keyword_hits"]:
            st.markdown(f'<span class="tag tag-ok">{k}</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="tag tag-warn">No hits</span>', unsafe_allow_html=True)

    st.markdown('<div class="card-title" style="margin-top:14px;">合规提示</div>', unsafe_allow_html=True)
    if s["violations"]:
        for v in s["violations"]:
            sev = v["severity"]
            cls = "tag-bad" if sev == "high" else "tag-warn"
            st.markdown(f'<span class="tag {cls}">{v["rule_id"]} ({sev})</span>', unsafe_allow_html=True)
            st.write(f"命中：{v['matched_terms']}")
            st.write(f"建议：{v['suggestion_zh']}")
    else:
        st.markdown('<span class="tag tag-ok">未检测到违规</span>', unsafe_allow_html=True)

    with st.expander("查看抽样评论证据（可选）"):
        for i, e in enumerate(st.session_state.get("evidence", [])[:8]):
            st.write(f"{i+1}. {e}")

st.markdown('</div>', unsafe_allow_html=True)
