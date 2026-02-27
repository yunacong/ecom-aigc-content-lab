# ecom-aigc/app/pages/compare.py
import pandas as pd
import streamlit as st
import altair as alt

# ---------------- Page config MUST be first Streamlit call ----------------
st.set_page_config(page_title="Compare & Select", layout="wide")


# ---------------- Altair theme ----------------
def apply_altair_theme():
    alt.themes.register(
        "dash",
        lambda: {
            "config": {
                "background": "transparent",
                "view": {"stroke": "transparent"},
                "axis": {
                    "labelColor": "rgba(15,23,42,.62)",
                    "titleColor": "rgba(15,23,42,.70)",
                    "gridColor": "rgba(15,23,42,.08)",
                    "tickColor": "rgba(15,23,42,.08)",
                },
                "legend": {
                    "labelColor": "rgba(15,23,42,.62)",
                    "titleColor": "rgba(15,23,42,.70)",
                },
            }
        },
    )
    alt.themes.enable("dash")


apply_altair_theme()

# ---------------- UI style ----------------
st.markdown(
    """
<style>
:root{
  --bg:#f7f8fc; --card:#fff; --text:#0f172a;
  --muted:rgba(15,23,42,.62); --border:rgba(15,23,42,.10);
  --shadow:0 12px 30px rgba(15,23,42,.10);
}
html, body {background: var(--bg) !important;}
.block-container{max-width:1200px; padding-top:1.2rem; padding-bottom:2.2rem;}

.card{background:var(--card); border:1px solid var(--border); border-radius:16px; padding:14px; box-shadow:var(--shadow);}
.card-title{font-weight:900; font-size:16px; color:rgba(15,23,42,.78); margin-bottom:10px; padding-bottom:8px; border-bottom:1px solid rgba(15,23,42,.08);}
.muted{color:var(--muted); font-size:12px;}

.hero{border-radius:20px; padding:16px; border:1px solid rgba(99,102,241,.18);
background: radial-gradient(1000px 240px at 0% 0%, rgba(99,102,241,.22), transparent 55%),
            radial-gradient(900px 220px at 100% 0%, rgba(236,72,153,.18), transparent 55%),
            linear-gradient(180deg, rgba(255,255,255,.95), rgba(255,255,255,.88));
box-shadow: 0 14px 40px rgba(15,23,42,.10);}

.tag{display:inline-block; padding:6px 10px; border-radius:999px; font-size:12px; margin:6px 8px 0 0; border:1px solid;}
.tag-ok{background:rgba(16,185,129,.10); color:#065f46; border-color:rgba(16,185,129,.25);}
.tag-warn{background:rgba(249,115,22,.10); color:#9a3412; border-color:rgba(249,115,22,.25);}
.tag-bad{background:rgba(239,68,68,.10); color:#991b1b; border-color:rgba(239,68,68,.25);}

.small-kpi{display:flex; gap:10px; margin-top:10px;}
.kpi{flex:1; border-radius:14px; border:1px solid rgba(15,23,42,.10); background:rgba(255,255,255,.9); padding:12px;}
.kpi .k{font-size:12px; color:rgba(15,23,42,.62);}
.kpi .v{font-size:24px; font-weight:900; margin-top:2px;}

.kpi-hero{
  border-radius:20px;
  padding:16px;
  border:1px solid rgba(99,102,241,.18);
  background: radial-gradient(900px 220px at 0% 0%, rgba(99,102,241,.24), transparent 55%),
              radial-gradient(900px 220px at 100% 0%, rgba(236,72,153,.20), transparent 55%),
              linear-gradient(180deg, rgba(255,255,255,.96), rgba(255,255,255,.88));
  box-shadow: 0 14px 40px rgba(15,23,42,.10);
  height: 190px;
  display:flex;
  flex-direction:column;
  justify-content:space-between;
}
.kpi-hero .t{font-size:13px; color:rgba(15,23,42,.65); font-weight:800;}
.kpi-hero .big{font-size:34px; font-weight:950; margin-top:6px;}
.kpi-hero .sub{font-size:12px; color:rgba(15,23,42,.55); margin-top:6px;}
.kpi-hero .badge{display:inline-block; padding:6px 10px; border-radius:999px; font-size:12px; border:1px solid rgba(15,23,42,.10); background:rgba(255,255,255,.8);}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------- Guard ----------------
st.title("版本对比与选优看板")
st.caption("对同一商品的多个生成版本进行指标对比、失败原因统计，并一键推荐最优版本。")

if "variants" not in st.session_state or "scores" not in st.session_state:
    st.warning("还没有生成内容。请先回到 app 首页点击「生成」，再来这里查看对比。")
    st.stop()

variants = st.session_state["variants"]
scores = st.session_state["scores"]
pid = st.session_state.get("pid", "demo")

# ---------------- Build comparison table ----------------
rows = []
for i, (v, s) in enumerate(zip(variants, scores), start=1):
    publishable = (len(s.get("violations", [])) == 0 and s.get("total", 0) >= 70)
    rows.append(
        {
            "variant_id": f"v{i}",
            "total": float(s.get("total", 0)),
            "compliance": float(s.get("compliance_score", 0)),
            "coverage": float(s.get("coverage_score", 0)),
            "readability": float(s.get("readability_score", 0)),
            "violations_cnt": len(s.get("violations", [])),
            "keyword_hits_cnt": len(s.get("keyword_hits", [])),
            "title_len": len(str(v.get("title", ""))),
            "detail_len": len(str(v.get("detail", ""))),
            "publishable": "✅" if publishable else "❌",
        }
    )

cmp = pd.DataFrame(rows).sort_values("total", ascending=False).reset_index(drop=True)

st.caption("上线门槛：无违规（violations_cnt=0）且 total ≥ 70；否则需要按规则改写/补词后再上线。")


def _status_row(r):
    if r["violations_cnt"] > 0:
        return "需改写（违规）"
    if r["coverage"] == 0:
        return "需补词（coverage=0）"
    if r["total"] < 70:
        return "需增强（total<70）"
    return "可上线"


cmp["status"] = cmp.apply(_status_row, axis=1)
cmp["publishable"] = cmp["status"].apply(lambda x: "✅" if x == "可上线" else "❌")

best_vid = str(cmp.iloc[0]["variant_id"])  # for highlight

# ---------------- Demo jitter (charts only) ----------------
DEMO_JITTER = True  # 只影响图表展示，不影响表格/推荐逻辑

if DEMO_JITTER:
    def _seed(vid: str) -> int:
        try:
            return int(str(vid).replace("v", ""))
        except Exception:
            return 0

    demo_total, demo_comp, demo_cov, demo_read = [], [], [], []
    for vid, t, c, cov, r in zip(cmp["variant_id"], cmp["total"], cmp["compliance"], cmp["coverage"], cmp["readability"]):
        s = _seed(vid)
        j1 = ((s * 37) % 17 - 8) / 10.0     # [-0.8, +0.8]
        j2 = ((s * 29) % 9 - 4) * 0.5       # [-2, +2]
        j3 = ((s * 41) % 9 - 4) * 0.5
        j4 = ((s * 53) % 9 - 4) * 0.5

        demo_total.append(round(float(t) + j1, 2))
        demo_comp.append(int(max(0, min(100, float(c) + j2))))
        demo_cov.append(int(max(0, min(100, float(cov) + j3))))
        demo_read.append(int(max(0, min(100, float(r) + j4))))

    cmp["demo_total"] = demo_total
    cmp["demo_compliance"] = demo_comp
    cmp["demo_coverage"] = demo_cov
    cmp["demo_readability"] = demo_read

# ---------------- Failure reasons ----------------
def fail_reasons(v, s):
    reasons = []
    if len(s.get("violations", [])) > 0:
        reasons.append("违规（policy）")
    if s.get("coverage_score", 0) == 0:
        reasons.append("关键词缺失（coverage=0）")

    all_text = " ".join(
        [
            str(v.get("title", "")),
            " ".join([str(x) for x in v.get("bullets", [])]),
            str(v.get("detail", "")),
            str(v.get("video", "")),
        ]
    )
    if len(all_text) < 200:
        reasons.append("内容太短")
    if len(all_text) > 1800:
        reasons.append("内容太长")

    return reasons or ["无明显失败原因"]


reason_rows = []
for i, (v, s) in enumerate(zip(variants, scores), start=1):
    for r in fail_reasons(v, s):
        reason_rows.append({"variant_id": f"v{i}", "reason": r})
reason_df = pd.DataFrame(reason_rows)

reason_stat = reason_df["reason"].value_counts().reset_index()
reason_stat.columns = ["reason", "count"]
reason_stat["percent"] = (reason_stat["count"] / reason_stat["count"].sum()).round(3)
reason_stat["percent"] = (reason_stat["percent"] * 100).round(1).astype(str) + "%"

# ---------------- Section 1: Comparison ----------------
publishable_cnt = int((cmp["publishable"] == "✅").sum())
vio_cnt = int((cmp["violations_cnt"] > 0).sum())

k1, k2, k3 = st.columns(3, gap="large")
with k1:
    st.markdown(
        f"""
    <div class="kpi-hero">
      <div>
        <div class="t">Best Variant</div>
        <div class="big">{best_vid.upper()}</div>
        <div class="sub">Top by total score</div>
      </div>
      <div class="badge">Rank #1</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        f"""
    <div class="kpi-hero">
      <div>
        <div class="t">Publishable</div>
        <div class="big">{publishable_cnt}</div>
        <div class="sub">无违规 & total≥70</div>
      </div>
      <div class="badge">Ready to publish</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        f"""
    <div class="kpi-hero">
      <div>
        <div class="t">With Violations</div>
        <div class="big">{vio_cnt}</div>
        <div class="sub">需改写后再上线</div>
      </div>
      <div class="badge">Need rewrite</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="card"><div class="card-title">1) 版本对比表</div>', unsafe_allow_html=True)
cols_show = [
    "variant_id",
    "status",
    "publishable",
    "total",
    "compliance",
    "coverage",
    "readability",
    "violations_cnt",
    "keyword_hits_cnt",
    "title_len",
    "detail_len",
]
st.dataframe(cmp[cols_show], use_container_width=True, hide_index=True)
st.markdown("</div>", unsafe_allow_html=True)  # ✅ close card

# ---------------- Charts panel ----------------
st.markdown('<div class="card"><div class="card-title">图表看板</div>', unsafe_allow_html=True)
if DEMO_JITTER:
    st.caption("⚠️ Demo view：图表为展示效果加入小幅波动（不影响表格/推荐/真实评分逻辑）")

# --- 1) Total score bar (use demo if enabled) ---
st.markdown('<div class="muted" style="margin-top:6px;">各版本总分（Table）</div>', unsafe_allow_html=True)

# 取 demo 分数（你现在开了 DEMO_JITTER），如果你关掉 DEMO_JITTER 就会自动用真实分数
if DEMO_JITTER and all(c in cmp.columns for c in ["demo_total","demo_compliance","demo_coverage","demo_readability"]):
    score_table = cmp[["variant_id","demo_total","demo_compliance","demo_coverage","demo_readability"]].rename(columns={
        "demo_total": "total",
        "demo_compliance": "compliance",
        "demo_coverage": "coverage",
        "demo_readability": "readability",
    }).copy()
else:
    score_table = cmp[["variant_id","total","compliance","coverage","readability"]].copy()

# 排序：按总分从高到低
score_table = score_table.sort_values("total", ascending=False).reset_index(drop=True)

# 展示成表格
st.dataframe(score_table, use_container_width=True, hide_index=True)

# --- 2) Delta dot plot (vs best) ---
st.markdown('<div class="muted" style="margin-top:14px;">指标差值对比（相对最佳版本 Δ）</div>', unsafe_allow_html=True)

if DEMO_JITTER:
    delta_src = cmp[["variant_id", "demo_total", "demo_compliance", "demo_coverage", "demo_readability"]].rename(
        columns={
            "demo_total": "total",
            "demo_compliance": "compliance",
            "demo_coverage": "coverage",
            "demo_readability": "readability",
        }
    ).copy()
else:
    delta_src = cmp[["variant_id", "total", "compliance", "coverage", "readability"]].copy()

best_row = delta_src.loc[delta_src["variant_id"] == best_vid].iloc[0]

delta = delta_src.copy()
delta["Total Δ"] = delta["total"] - float(best_row["total"])
delta["Compliance Δ"] = delta["compliance"] - float(best_row["compliance"])
delta["Coverage Δ"] = delta["coverage"] - float(best_row["coverage"])
delta["Readability Δ"] = delta["readability"] - float(best_row["readability"])

delta_long = delta.melt(
    id_vars=["variant_id"],
    value_vars=["Total Δ", "Compliance Δ", "Coverage Δ", "Readability Δ"],
    var_name="metric",
    value_name="delta",
)

color_scale = alt.Scale(
    domain=sorted(delta_long["variant_id"].unique().tolist()),
    range=["#2563EB", "#60A5FA", "#F97316", "#FB7185", "#10B981"],
)

dxmin = float(delta_long["delta"].min())
dxmax = float(delta_long["delta"].max())
dpad = max(0.5, (dxmax - dxmin) * 0.2)
d_domain = [dxmin - dpad, dxmax + dpad]

zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="rgba(15,23,42,.22)").encode(x="x:Q")

dots = alt.Chart(delta_long).mark_point(filled=True, size=120).encode(
    y=alt.Y(
        "metric:N",
        sort=["Total Δ", "Compliance Δ", "Coverage Δ", "Readability Δ"],
        title="",
    ),
    x=alt.X("delta:Q", title="Δ vs Best", scale=alt.Scale(domain=d_domain), axis=alt.Axis(format=".2f")),
    color=alt.Color("variant_id:N", scale=color_scale, legend=alt.Legend(title="Variant")),
    tooltip=["variant_id", "metric", alt.Tooltip("delta:Q", format=".2f")],
)

labels = alt.Chart(delta_long).mark_text(align="left", dx=8, fontSize=11, color="rgba(15,23,42,.65)").encode(
    y=alt.Y("metric:N", sort=["Total Δ", "Compliance Δ", "Coverage Δ", "Readability Δ"]),
    x="delta:Q",
    text=alt.Text("delta:Q", format=".2f"),
)

st.altair_chart((zero + dots + labels).properties(height=180), use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)  # close charts card

# ---------------- Section 2: Failure stats + viewer ----------------
st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
st.markdown('<div class="card"><div class="card-title">2) Top 失败原因统计</div>', unsafe_allow_html=True)

c1, c2 = st.columns([1.1, 1.9], gap="large")
with c1:
    st.write("原因统计：")
    st.dataframe(reason_stat, use_container_width=True, hide_index=True)
    st.markdown('<div class="muted" style="margin-top:10px;">失败原因分布</div>', unsafe_allow_html=True)

    if reason_stat.shape[0] <= 1:
        st.info(
            "当前样本失败原因较单一（几乎都集中在同一类原因），建议：①生成更多版本（n=5~8）②扩大样本商品 ③放宽/细化规则后再观察分布差异。"
        )
    else:
        reason_plot = reason_stat.copy()
        bar = alt.Chart(reason_plot).mark_bar(cornerRadiusEnd=6).encode(
            y=alt.Y("reason:N", sort="-x", title=""),
            x=alt.X("count:Q", title="Count"),
            tooltip=["reason", "count", "percent"],
        )
        txt = alt.Chart(reason_plot).mark_text(align="left", dx=6, fontSize=12).encode(
            y=alt.Y("reason:N", sort="-x"),
            x="count:Q",
            text="percent:N",
        )
        st.altair_chart((bar + txt).properties(height=120), use_container_width=True)

with c2:
    st.write("按版本查看原因：")
    vids = sorted(reason_df["variant_id"].unique().tolist())
    pick = st.selectbox("选择版本", vids, index=0)

    picked = reason_df[reason_df["variant_id"] == pick]["reason"].tolist()
    st.markdown('<div class="muted">原因标签</div>', unsafe_allow_html=True)
    for r in picked:
        cls = "tag-bad" if "违规" in r else ("tag-warn" if ("缺失" in r or "太短" in r or "太长" in r) else "tag-ok")
        st.markdown(f'<span class="tag {cls}">{r}</span>', unsafe_allow_html=True)

    st.markdown('<div class="muted" style="margin-top:14px;">原因明细（表）</div>', unsafe_allow_html=True)
    st.dataframe(reason_df[reason_df["variant_id"] == pick], use_container_width=True, hide_index=True)

st.markdown("</div>", unsafe_allow_html=True)  # close section2 card

# ---------------- Section 3: Recommend best ----------------
st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
st.markdown('<div class="card"><div class="card-title">3) 一键推荐最优版本</div>', unsafe_allow_html=True)

best_idx = int(best_vid.replace("v", "")) - 1
best_v = variants[best_idx]
best_s = scores[best_idx]

st.markdown(
    f"""
<div class="hero">
  <div class="muted">推荐版本</div>
  <div style="font-size:34px; font-weight:900; margin:6px 0 2px;">{best_vid.upper()}</div>
  <div class="muted">product_id = {pid}</div>
  <div class="small-kpi">
    <div class="kpi"><div class="k">Total</div><div class="v">{best_s.get("total",0)}</div></div>
    <div class="kpi"><div class="k">Compliance</div><div class="v">{best_s.get("compliance_score",0)}</div></div>
    <div class="kpi"><div class="k">Coverage</div><div class="v">{best_s.get("coverage_score",0)}</div></div>
    <div class="kpi"><div class="k">Readability</div><div class="v">{best_s.get("readability_score",0)}</div></div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

why = []
if len(best_s.get("violations", [])) == 0:
    why.append("合规通过（无违规）")
else:
    why.append(f"存在 {len(best_s.get('violations', []))} 条违规（建议按规则改写后上线）")
if best_s.get("coverage_score", 0) > 0:
    why.append(f"关键词覆盖较好（命中 {len(best_s.get('keyword_hits', []))} 个）")
else:
    why.append("关键词覆盖为 0（建议补充类目高频词/高亮词）")
why.append(f"可读性得分 {best_s.get('readability_score', 0)}")

st.markdown('<div class="muted" style="margin-top:12px;">推荐理由</div>', unsafe_allow_html=True)
for w in why:
    st.write(f"- {w}")

tabs = st.tabs(["标题", "卖点", "详情", "短视频脚本", "违规详情"])
with tabs[0]:
    st.write(best_v.get("title", ""))
with tabs[1]:
    st.write("\n".join([f"- {x}" for x in best_v.get("bullets", [])]))
with tabs[2]:
    st.markdown(best_v.get("detail", ""))
with tabs[3]:
    st.code(best_v.get("video", ""))
with tabs[4]:
    vio = best_s.get("violations", [])
    if not vio:
        st.success("无违规")
    else:
        for item in vio:
            sev = item.get("severity", "medium")
            cls = "tag-bad" if sev == "high" else "tag-warn"
            st.markdown(f'<span class="tag {cls}">{item["rule_id"]} ({sev})</span>', unsafe_allow_html=True)
            st.write(f"命中：{item.get('matched_terms', [])}")
            st.write(f"建议：{item.get('suggestion_zh', '')}")

st.markdown("</div>", unsafe_allow_html=True)  # close section3 card