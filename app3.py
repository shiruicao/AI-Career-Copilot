import streamlit as st
import json
import plotly.graph_objects as go
from api import call_job_copilot_api

st.set_page_config(layout="wide", page_title="AI Job Copilot · AI求职助手")

# ========== CSS ==========
try:
    with open("style.css", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# ========== HERO ==========
st.markdown("""
<div class="hero">
    <h1><span class="hero-symbol">✦</span> AI Job Copilot · 您的AI求职助手</h1>
    <p>Intelligent Job Matching & Personalized Career Support</p>
</div>
""", unsafe_allow_html=True)

# ========== 翻译函数 ==========
def translate_level(level: str) -> str:
    mapping = {"low": "低", "medium": "中", "high": "高", "excellent": "优秀"}
    return mapping.get(str(level).lower(), level)

def translate_recommendation(rec: str) -> str:
    mapping = {
        "strong_recommend": "非常推荐",
        "recommend": "比较推荐",
        "neutral": "中等",
        "not_recommend": "不推荐"
    }
    return mapping.get(str(rec).lower(), rec)

def translate_decision(dec: str) -> str:
    mapping = {
        "apply_now": "立即投递",
        "apply_with_improvement": "完善后投递",
        "low_priority": "低优先级",
        "not_recommended": "不推荐投递"
    }
    return mapping.get(str(dec).lower(), dec)

# ========== SIDEBAR ==========
with st.sidebar:
    resume = st.text_area("简历", height=250)
    st.markdown("<hr style='margin: 24px 0 16px 0; border-top: 1px solid rgba(0,0,0,0.08);'>", unsafe_allow_html=True)
    st.markdown("<div class='redline-label'>求职雷区</div>", unsafe_allow_html=True)

    all_options = ["单休", "大小周", "销售性质", "频繁出差", "严重加班"]
    if "red_lines" not in st.session_state:
        st.session_state.red_lines = []

    # 已选框：仅展示文字标签（不可点击），取消通过下方选项块完成
    selected = st.session_state.red_lines
    if selected:
        chips_html = "".join(
            f'<span class="selected-chip">{opt}</span>' for opt in selected
        )
        st.markdown(f'<div class="selected-box-wrapper">{chips_html}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="selected-box-wrapper"><span class="empty-hint-box">暂未选择</span></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # 2-2-1 点击选项块：已选项加 ✓ 前缀标记 + 低透明度，点击可取消
    rows = [all_options[0:2], all_options[2:4], all_options[4:5]]
    for row in rows:
        cols = st.columns(len(row))
        for col, opt in zip(cols, row):
            with col:
                is_selected = opt in st.session_state.red_lines
                label = f"✓ {opt}" if is_selected else opt
                btn_type = "secondary" if is_selected else "primary"
                if st.button(label, key=f"rl_{opt}", use_container_width=True, type=btn_type):
                    if is_selected:
                        st.session_state.red_lines.remove(opt)
                    else:
                        st.session_state.red_lines.append(opt)
                    st.rerun()

    red_lines = st.session_state.red_lines

jd = st.text_area("岗位 JD", height=200)
analyze = st.button("开始分析", type="primary")

# ========== session_state 保存分析结果，防止下载触发重置 ==========
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# ========== DASHBOARD ==========
if analyze:
    if not resume.strip() or not jd.strip():
        st.warning("请填写完整信息")
        st.stop()

    with st.spinner("AI 分析中，请稍候..."):
        try:
            result = call_job_copilot_api(resume, jd, red_lines=red_lines)

            raw = result.get("data", {})
            output = raw.get("outputs", {})

            match_json = output.get("match_json", {})
            if isinstance(match_json, str):
                match_json = json.loads(match_json)

            red_line_hits = output.get("red_line_hits", [])
            if isinstance(red_line_hits, str):
                try:
                    red_line_hits = json.loads(red_line_hits)
                except Exception:
                    red_line_hits = []

            advisor_json = output.get("advisor_json", {})
            if isinstance(advisor_json, str):
                try:
                    advisor_json = json.loads(advisor_json)
                except Exception:
                    advisor_json = {}

            final_text = output.get("final_text", "")

            if not match_json:
                st.error("API 返回数据为空，请检查服务状态。")
                st.stop()

            # 保存到 session_state
            st.session_state.analysis_result = {
                "match_json": match_json,
                "red_line_hits": red_line_hits,
                "advisor_json": advisor_json,
                "final_text": final_text,
                "red_lines_used": list(red_lines),
            }

        except json.JSONDecodeError:
            st.error("解析 AI 返回结果失败，数据格式异常。")
            st.stop()
        except Exception as e:
            st.error(f"分析失败：{e}")
            st.stop()

# 有分析结果就渲染（无论是刚分析还是下载触发的重渲染）
if st.session_state.analysis_result:
    res         = st.session_state.analysis_result
    match_json  = res["match_json"]
    red_line_hits = res["red_line_hits"]
    advisor_json = res["advisor_json"]
    final_text  = res["final_text"]
    red_lines_used = res["red_lines_used"]

    # ===== KPI =====
    c1, c2, c3 = st.columns(3)
    c1.metric("综合推荐指数", match_json.get("match_score", "N/A"))
    c2.metric("匹配程度", translate_level(match_json.get("match_level", "N/A")))
    c3.metric("投递建议", translate_recommendation(match_json.get("recommendation", "N/A")))

    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

    # ===== 雷达图 + 分数列表 =====
    dims = match_json.get("dimension_scores", {})
    skills_v  = dims.get("skills_match", 0)
    project_v = dims.get("project_match", 0)
    domain_v  = dims.get("domain_match", 0)
    bonus_v   = dims.get("bonus_match", 0)
    values = [skills_v, project_v, domain_v, bonus_v]
    labels = ["硬技能匹配", "项目经验匹配", "行业背景经验", "岗位加分项"]

    col_radar, col_scores = st.columns([6, 3])

    with col_radar:
        if any(v > 0 for v in values):
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=values + [values[0]],
                theta=labels + [labels[0]],
                fill="toself",
                fillcolor="rgba(111,139,255,0.15)",
                line=dict(color="#7C3AED", width=2.5),
                hovertemplate="%{theta}: %{r}<extra></extra>",
                name=""
            ))
            fig.update_layout(
                polar=dict(
                    bgcolor="rgba(0,0,0,0)",
                    radialaxis=dict(visible=False, range=[0, 100]),
                    angularaxis=dict(
                        tickfont=dict(size=14, color="#3b4d7a", family="PingFang SC, Microsoft YaHei"),
                        linecolor="rgba(0,0,0,0.06)",
                        rotation=90,
                        direction="clockwise"
                    ),
                    gridshape="circular",
                    domain=dict(x=[0.05, 0.95], y=[0.05, 0.95])
                ),
                showlegend=False,
                margin=dict(l=90, r=90, t=80, b=80),
                height=420,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("维度评分数据暂无，无法渲染雷达图。")

    with col_scores:
        st.markdown("<div style='height:48px'></div>", unsafe_allow_html=True)
        for label, val in zip(labels, values):
            st.markdown(f"""
<div class="score-item">
    <div class="score-label">✦ {label}</div>
    <div class="score-value">{val} <span class="score-denom">/ 100</span></div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ===== 核心优势 + 主要差距 =====
    strengths = match_json.get("strengths", [])
    gaps      = match_json.get("gaps", [])

    col_str, col_gap = st.columns(2)

    with col_str:
        items_html = "".join(
            f'<div class="sg-item"><span class="sg-num">{i+1}</span>{item}</div>'
            for i, item in enumerate(strengths)
        ) if strengths else '<div class="sg-empty">暂无数据</div>'
        st.markdown(f"""
<div class="sg-box-h">
    <div class="sg-title">核心优势</div>
    {items_html}
</div>""", unsafe_allow_html=True)

    with col_gap:
        items_html = "".join(
            f'<div class="sg-item"><span class="sg-num">{i+1}</span>{item}</div>'
            for i, item in enumerate(gaps)
        ) if gaps else '<div class="sg-empty">暂无数据</div>'
        st.markdown(f"""
<div class="sg-box-h">
    <div class="sg-title">主要差距</div>
    {items_html}
</div>""", unsafe_allow_html=True)

    st.divider()

    # ===== 行动改进指南 =====
    st.markdown("### 行动改进指南")
    tab1, tab2, tab3 = st.tabs(["简历优化建议", "下一步行动建议", "面试准备建议"])

    resume_optimization = advisor_json.get("resume_optimization", [])
    improvement_actions = advisor_json.get("improvement_actions", [])
    interview_focus = advisor_json.get("interview_focus", [])

    with tab1:
        if resume_optimization:
            for item in resume_optimization:
                st.markdown(f"· {item}")
        else:
            st.caption("暂无简历优化建议")

    with tab2:
        if improvement_actions:
            for item in improvement_actions:
                st.markdown(f"· {item}")
        else:
            st.caption("暂无下一步行动建议")

    with tab3:
        if interview_focus:
            for item in interview_focus:
                st.markdown(f"· {item}")
        else:
            st.caption("暂无面试准备建议")

    st.divider()

    # ===== 红线检测 + 风险提示 =====
    col_risk1, col_risk2 = st.columns(2)

    with col_risk1:
        st.markdown("### 红线检测")
        if not red_lines_used:
            st.caption("未设置求职雷区条件")
        elif red_line_hits:
            for hit in red_line_hits:
                st.error(f"· 命中：{hit}")
        else:
            st.success("· 未命中任何求职雷区")

    with col_risk2:
        st.markdown("### 风险提示")
        risk_flags = match_json.get("risk_flags", [])
        if risk_flags:
            for flag in risk_flags:
                st.warning(f"· {flag}")
        else:
            st.caption("暂无风险提示")

    st.divider()

    # ===== 完整报告 + 下载按钮 =====
    col_report_title, col_download = st.columns([8, 2])
    with col_report_title:
        st.markdown("### 岗位匹配分析报告")
    with col_download:
        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
        if final_text:
            st.download_button(
                label="⬇",
                data=final_text.encode("utf-8"),
                file_name="岗位匹配分析报告.md",
                mime="text/markdown",
                use_container_width=True,
                key="download_report"
            )

    with st.expander("展开查看完整报告", expanded=False):
        if final_text:
            st.markdown(final_text)
        else:
            st.caption("报告内容暂未返回")