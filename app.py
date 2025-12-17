import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 设置页面配置
st.set_page_config(
    page_title="高考数据分析看板",
    page_icon="📊",
    layout="wide"
)

# 标题
st.title("📊 高考模拟数据与志愿填报分析系统")
st.markdown("---")

# 数据加载函数 (使用缓存提高性能)
@st.cache_data
def load_data():
    base_path = "data"
    
    # 1. 加载成绩数据
    score_file = os.path.join(base_path, "赋分后的高考模拟数据.csv")
    if os.path.exists(score_file):
        df_score = pd.read_csv(score_file)
        # 计算总成绩: 语数英 + 赋分科目
        # 识别赋分列 (假设列名包含'赋分') 和 主科
        fufen_cols = [c for c in df_score.columns if '赋分' in c]
        main_cols = ['语文', '数学', '英语']
        calc_cols = [c for c in main_cols + fufen_cols if c in df_score.columns]
        
        if calc_cols:
            df_score['总成绩'] = df_score[calc_cols].sum(axis=1)
        else:
            st.error("未找到成绩列，无法计算总分")
    else:
        st.error(f"文件未找到: {score_file}")
        return None, None, None

    # 2. 加载位次数据
    rank_file = os.path.join(base_path, "高考考生位次.csv")
    if os.path.exists(rank_file):
        df_rank = pd.read_csv(rank_file)
    else:
        df_rank = None

    # 3. 加载招生计划
    plan_file = os.path.join(base_path, "招生计划.csv")
    if os.path.exists(plan_file):
        df_plan = pd.read_csv(plan_file)
    else:
        df_plan = None
        
    return df_score, df_rank, df_plan

# 加载数据
df_score, df_rank, df_plan = load_data()

if df_score is not None:
    # 侧边栏 - 全局筛选
    st.sidebar.header("🔍 筛选条件")
    
    # 假设数据中有班级字段，如果没有则跳过
    if '班级' in df_score.columns:
        selected_class = st.sidebar.multiselect(
            "选择班级",
            options=df_score['班级'].unique(),
            default=df_score['班级'].unique()
        )
        # 过滤数据
        df_filtered = df_score[df_score['班级'].isin(selected_class)]
    else:
        df_filtered = df_score

    # 创建标签页
    tab1, tab2, tab3 = st.tabs(["📈 成绩整体分析", "🔍 个人成绩查询", "🏫 志愿填报参考"])

    # --- Tab 1: 成绩整体分析 ---
    with tab1:
        st.header("模拟高考成绩概览")
        
        # 关键指标 (KPI)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("参考人数", f"{len(df_filtered)} 人")
        with col2:
            st.metric("平均总分", f"{df_filtered['总成绩'].mean():.1f} 分")
        with col3:
            st.metric("最高分", f"{df_filtered['总成绩'].max()} 分")
        with col4:
            st.metric("最低分", f"{df_filtered['总成绩'].min()} 分")

        st.markdown("### 📊 成绩分布可视化")
        
        c1, c2 = st.columns(2)
        
        with c1:
            # 直方图：总成绩分布
            fig_hist = px.histogram(
                df_filtered, 
                x="总成绩", 
                nbins=20, 
                title="总成绩分布直方图",
                color_discrete_sequence=['#636EFA']
            )
            fig_hist.update_layout(bargap=0.1)
            st.plotly_chart(fig_hist, use_container_width=True)
            
        with c2:
            # 箱线图：各科成绩分布 (需要数据转换)
            # 动态获取科目：语数英 + 赋分科目
            subjects = [col for col in df_filtered.columns if col in ['语文', '数学', '英语'] or '赋分' in col]
            
            # 简单的melt操作用于绘图
            if subjects:
                df_melted = df_filtered.melt(value_vars=subjects, var_name="科目", value_name="分数")
                fig_box = px.box(
                    df_melted, 
                    x="科目", 
                    y="分数", 
                    color="科目", 
                    title="各学科成绩箱线图"
                )
                st.plotly_chart(fig_box, use_container_width=True)
            else:
                st.info("未检测到分科成绩列，无法展示箱线图。")

    # --- Tab 2: 个人成绩查询 ---
    with tab2:
        st.header("个人成绩单查询")
        
        search_input = st.text_input("请输入姓名或准考证号进行查询:")
        
        if search_input:
            # 模糊匹配
            mask = (df_score['姓名'].astype(str).str.contains(search_input)) | \
                   (df_score['准考证号'].astype(str).str.contains(search_input))
            student_result = df_score[mask]
            
            if not student_result.empty:
                st.success(f"查询到 {len(student_result)} 条记录")
                for index, row in student_result.iterrows():
                    with st.expander(f"📄 {row['姓名']} (准考证号: {row['准考证号']})", expanded=True):
                        # 展示个人详细分数
                        sc1, sc2 = st.columns([1, 2])
                        with sc1:
                            st.markdown(f"### 总分: **{row['总成绩']}**")
                            # 如果有位次数据，尝试查找
                            if df_rank is not None:
                                # 假设位次表里也有总成绩和位次对应，或者直接在成绩表里就有位次
                                # 这里简单演示，如果成绩表里有'位次'列
                                if '位次' in row:
                                    st.markdown(f"### 位次: **{row['位次']}**")
                                else:
                                    # 尝试从位次表查找 (假设位次表是 分数-位次 对应表)
                                    # 这里简化处理，仅展示已有信息
                                    pass
                        
                        with sc2:
                            # 雷达图展示各科能力
                            if subjects:
                                scores = [row[s] for s in subjects]
                                df_radar = pd.DataFrame(dict(
                                    r=scores,
                                    theta=subjects
                                ))
                                fig_radar = px.line_polar(df_radar, r='r', theta='theta', line_close=True, title="学科能力雷达图")
                                fig_radar.update_traces(fill='toself')
                                st.plotly_chart(fig_radar, use_container_width=True)
            else:
                st.warning("未找到匹配的学生信息。")

    # --- Tab 3: 志愿填报参考 ---
    with tab3:
        st.header("智能志愿推荐参考")
        
        if df_plan is not None:
            st.info("基于您的总成绩和位次，筛选历年录取情况（模拟数据）。")
            
            my_score = st.number_input("输入你的预估总分", min_value=0, max_value=750, value=int(df_filtered['总成绩'].mean()))
            
            # 简单的推荐逻辑：推荐 录取分 <= 我的分数 的学校，且分差在一定范围内
            # 假设招生计划表有 '最低投档分' 或类似字段
            # 先检查列名
            # st.write(df_plan.columns) # 调试用
            
            # 尝试寻找分数线列
            score_col = None
            for col in df_plan.columns:
                if '分' in col:
                    score_col = col
                    break
            
            if score_col:
                # 筛选逻辑： 录取分 <= 我的分数 且 录取分 > 我的分数 - 30 (冲稳保的简单模拟)
                # 注意：实际数据中可能是字符串或含有非数字，需要处理
                try:
                    # 清洗数据，确保是数字
                    df_plan_clean = df_plan.copy()
                    df_plan_clean[score_col] = pd.to_numeric(df_plan_clean[score_col], errors='coerce')
                    df_plan_clean = df_plan_clean.dropna(subset=[score_col])
                    
                    # 推荐区间：[我的分数-40, 我的分数+10] (可以冲一点，也可以保底)
                    recommendations = df_plan_clean[
                        (df_plan_clean[score_col] <= my_score + 10) & 
                        (df_plan_clean[score_col] >= my_score - 40)
                    ].sort_values(by=score_col, ascending=False)
                    
                    st.write(f"为您推荐 {len(recommendations)} 个可能的志愿方向 (分数范围: {my_score-40} - {my_score+10}):")
                    st.dataframe(recommendations, use_container_width=True)
                    
                    if not recommendations.empty:
                        # 简单的统计图
                        if '院校名称' in recommendations.columns:
                            top_schools = recommendations['院校名称'].value_counts().head(10)
                            fig_schools = px.bar(x=top_schools.index, y=top_schools.values, title="推荐院校频次 (Top 10)")
                            st.plotly_chart(fig_schools)
                            
                except Exception as e:
                    st.error(f"数据处理出错: {e}")
            else:
                st.warning("在招生计划表中未找到分数线相关列，无法自动推荐。请检查数据源。")
                st.dataframe(df_plan.head())
        else:
            st.warning("缺少招生计划数据文件 (招生计划.csv)，无法进行志愿推荐。")

else:
    st.warning("请确保 data 目录下存在数据文件。")
