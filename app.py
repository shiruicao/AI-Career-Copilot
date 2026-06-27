import streamlit as st
import json
import plotly.graph_objects as go
from api import call_job_copilot_api

# ==========================================
# 1. 页面基本配置与样式固化
# ==========================================
st.set_page_config(
    page_title="AI Job Copilot — 智能求职决策看板",
    page_icon="💼",
    layout="wide"  
)

st.markdown("""
    <style>
    .block-container {padding-top: 1.5rem; padding-bottom: 1.5rem;}
    .stCheckbox {margin-bottom: 0.5rem;}
    </style>
    """, unsafe_allow_html=True)

st.title("💼 AI Job Copilot")
st.caption("多维技能动态对齐 · 隐性风险探测 · 结构化求职行动指南")

# ==========================================
# 2. 布局设计：左侧通用画像输入控制栏 (Sidebar)
# ==========================================
with st.sidebar:
    st.header("📋 用户画像配置")
    
    # 🚨 核心改动：彻底废除文件上传，改为最稳健、无编码冲突的大文本框复制粘贴形式
    resume_text = st.text_area(
        "请在此粘贴个人简历文本内容:",
        height=300,
        placeholder="在此粘贴个人的完整简历文本（包含专业技能、实习经历、项目背景等）..."
    ).strip()
    
    if resume_text:
        st.success("🟢 个人简历画像已成功对齐")
    else:
        st.info("💡 评估前请先在左侧粘贴个人简历文本。")

    st.divider()
    st.header("🛑 个人红线预设")
    deal_breakers = st.multiselect(
        "触发时需进行风险提示的强要求:",
        ["单休", "大小周", "纯销售性质", "频繁出差", "严重加班"],
        default=["单休"]
    )

# ==========================================
# 3. 布局设计：右侧主工作区 (Main Panel)
# ==========================================
st.header("🔍 全新岗位动态评估")
jd_input = st.text_area(
    "请在此粘贴待投递岗位的招聘文本 (JD):", 
    height=180, 
    placeholder="在此粘贴全新岗位的招聘要求文本，图表与报告将根据双端数据实时刷新..."
)

if st.button("🚀 开始智能探测与决策分析", type="primary"):
    # 强约束控制流校验
    if not resume_text:
        st.error("🛑 分析终止：未在左侧检测到有效简历画像，请先粘贴个人简历文本。")
    elif not jd_input:
        st.warning("⚠️ 请先粘贴待评估岗位的 JD 文本内容。")
    else:
        with st.spinner("数据通道维持畅通，大模型深度比对与长报告正在连环生成，请保持耐心等待全程跑完..."):
            
            # 发起流式长连接请求
            api_response = call_job_copilot_api(resume_text, jd_input)
            
            if api_response is None:
                st.error("❌ 接口通信故障：未能在预定时间内收到工作流的任何响应。")
            elif "error_details" in api_response:
                st.error(f"🛑 物理层连接中断故障：")
                st.code(api_response["error_details"], language="text")
            else:
                data_layer = api_response.get("data", {})
                status = data_layer.get("status")
                
                if status == "failed":
                    error_msg = data_layer.get("error", "未获取到具体的错误日志")
                    st.error(f"❌ Dify 后端工作流执行失败！具体的引擎中断原因: {error_msg}")
                else:
                    outputs_data = data_layer.get("outputs", {})
                    
                    # 1. 动态提取长报告
                    report_markdown = outputs_data.get("final_text") or outputs_data.get("text")
                    
                    # 2. 动态提取打分 JSON
                    match_engine_data = outputs_data.get("match_json")
                    if match_engine_data and isinstance(match_engine_data, str):
                        try:
                            match_engine_data = json.loads(match_engine_data)
                        except json.JSONDecodeError:
                            match_engine_data = None

                    # 3. 正常渲染看板
                    if match_engine_data and report_markdown:
                        st.success("✨ 全新岗位决策数据与报告同步动态生成完毕！")
                        st.divider()
                        
                        # 看板第 1 层：KPI 状态组件
                        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
                        with kpi_col1:
                            st.metric(label="🏆 综合推荐指数", value=f"{match_engine_data.get('match_score', 0)} / 100")
                        
                        with kpi_col2:
                            level_upper = str(match_engine_data.get('match_level', 'UNKNOWN')).upper()
                            st.markdown(f"**📊 匹配等级 (Match Level)**")
                            if "EXCELLENT" in level_upper or "HIGH" in level_upper:
                                st.success(f"🟢 {level_upper}")
                            else:
                                st.warning(f"🟡 {level_upper}")
                                
                        with kpi_col3:
                            rec_map = {"strong_recommend": "强烈推荐申请 ⭐", "recommend": "建议投递", "neutral": "谨慎观望"}
                            st.markdown(f"**🧭 投递决策建议 (Decision)**")
                            st.info(rec_map.get(match_engine_data.get('recommendation', ''), "正常评估"))
                        
                        st.progress(int(match_engine_data.get('match_score', 0)) / 100)
                        st.divider()
                        
                        # 看板第 2 层：四维评分卡片与雷达图
                        st.subheader("📊 多维加权对齐分析")
                        dims = match_engine_data.get('dimension_scores', {"skills_match": 0, "project_match": 0, "domain_match": 0, "bonus_match": 0})
                        
                        chart_col, card_col = st.columns([3, 2])
                        with chart_col:
                            categories = ['硬技能匹配 (40%)', '项目经验 (30%)', '行业经验 (20%)', '加分项 (10%)']
                            scores = [dims.get('skills_match', 0), dims.get('project_match', 0), dims.get('domain_match', 0), dims.get('bonus_match', 0)]
                            categories.append(categories[0])
                            scores.append(scores[0])
                            
                            fig = go.Figure()
                            fig.add_trace(go.Scatterpolar(
                                r=scores, theta=categories, fill='toself', 
                                fillcolor='rgba(26, 115, 232, 0.15)', line=dict(color='#1A73E8', width=2)
                            ))
                            fig.update_layout(
                                polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False,
                                margin=dict(l=50, r=50, t=20, b=20), height=300
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            
                        with card_col:
                            st.metric("🔧 硬技能匹配", f"{dims.get('skills_match', 0)} / 100")
                            st.metric("📂 项目经验匹配", f"{dims.get('project_match', 0)} / 100")
                            st.metric("🏢 行业背景经验", f"{dims.get('domain_match', 0)} / 100")
                            st.metric("🎁 岗位加分项", f"{dims.get('bonus_match', 0)} / 100")
                            
                        st.divider()
                        
                        # 看板第 3 层：核心优势与主要差距动态对比
                        layout_col1, layout_col2 = st.columns(2)
                        with layout_col1:
                            st.markdown("### 🟢 核心优势 (Strengths)")
                            for strength in match_engine_data.get('strengths', []):
                                st.markdown(f"`{strength}`")
                        with layout_col2:
                            st.markdown("### 🔴 主要差距 (Gaps)")
                            for gap in match_engine_data.get('gaps', []):
                                st.markdown(f"❌ <span style='color:#d93025;'>{gap}</span>", unsafe_allow_html=True)
                        
                        if match_engine_data.get('risk_flags', []):
                            st.markdown("#### 🚨 隐性风险提示 (Risk Flags)")
                            for risk in match_engine_data.get('risk_flags', []):
                                st.error(f"风险因子: {risk}")
                                
                        st.divider()
                        
                        # 看板第 4 层：智能改进指南
                        st.subheader("🛠 Prescriptive Action Plan — 行动改进指南")
                        tab1, tab2 = st.tabs(["📝 简历针对性优化 (Resume)", "📅 建议投递跟进建议 (Action Plan)"])
                        with tab1:
                            current_gaps = match_engine_data.get('gaps', [])
                            if current_gaps:
                                for idx, gap in enumerate(current_gaps):
                                    st.checkbox(f"针对主要差距【{gap}】，在个人简历中微调强化或补充相关的实战话术描述", key=f"fin_sug_{idx}")
                            else:
                                st.info("当前用户简历匹配度良好，无强烈硬技能差距。")
                        with tab2:
                            st.markdown(f"**⏱️ Step 1** ：参考上游匹配引擎动态指出的 `主要差距(Gaps)` 补齐面试技术话术。")
                            st.markdown(f"**⏱️ Step 2** ：完成简历微调 Checklist 检查后导出更新文件。")
                            st.markdown(f"**⏱️ Step 3** ：一键发起投递，该岗位最终获得的推荐评级为 `{level_upper}`。")
                    else:
                        st.error("❌ 数据渲染终止：未能从 Dify 最终输出中结构化解析出打分字典变量 `match_json` 或长报告变量。")

                # 看板第 5 层：最终版 Markdown 长报告展示与一键下载
                # ==========================================
                if 'report_markdown' in locals() and report_markdown:
                    st.divider()
                    with st.expander("📖 查看 AI 深度决策分析长报告", expanded=True):
                        
                        # 🚨 核心新增：加入一键下载纯净报告的功能
                        st.download_button(
                            label="📥 一键下载纯净版决策报告 (.md)",
                            data=report_markdown,
                            file_name="AI_Job_Copilot_Decision_Report.md",
                            mime="text/markdown",
                            type="secondary"
                        )
                        
                        st.markdown(report_markdown)