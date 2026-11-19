from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

COLORS = {"이마트": "#FFB81C", "하이마트": "#E60012"}
st.set_page_config(page_title="이마트 vs 하이마트 평균 실적 비교", layout="wide")
st.title("이마트와 하이마트의 평균 실적 비교")
st.caption("출처: 금융감독원 전자공시시스템(DART) 분기보고서 요약 데이터(sales.csv) · 2025-1Q ~ 2026-3Q · 금액 단위: 억원")

# 1-3 데이터 경로
HERE = Path(__file__).parent
DATA_PATH = HERE / "sales.csv"


@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


if not DATA_PATH.exists():
    st.error("sales.csv 파일을 찾을 수 없습니다. app.py와 같은 폴더에 sales.csv가 있는지 확인해 주세요.")
    st.stop()

data = load_data(DATA_PATH)

# 2-2 위젯 세 개: 사이드바에 기업 선택, 분기 범위, 표시 지표
st.sidebar.header("조회 조건 설정")

companies = sorted(data["company"].unique().tolist())
selected_companies = st.sidebar.multiselect(
    "비교할 기업 선택",
    options=companies,
    default=companies,
)

periods = data["period"].unique().tolist()
start_period, end_period = st.sidebar.select_slider(
    "분기 범위 선택",
    options=periods,
    value=(periods[0], periods[-1]),
)

metric_map = {
    "점포당 평균 매출 (억원)": "avg_sales_per_store",
    "점포당 평균 영업이익 (억원)": "avg_profit_per_store",
    "전체 매출 (억원)": "sales",
    "전체 영업이익 (억원)": "profit",
}
selected_metric_label = st.sidebar.radio(
    "표시 지표 선택",
    options=list(metric_map.keys()),
    index=0,
)
metric = metric_map[selected_metric_label]

# 2-3 빈 선택 처리
start_idx = periods.index(start_period)
end_idx = periods.index(end_period)
selected_periods = periods[start_idx : end_idx + 1]

view = data[
    (data["company"].isin(selected_companies))
    & (data["period"].isin(selected_periods))
].copy()

if view.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다. 사이드바에서 기업과 분기 범위를 다시 선택해 주세요.")
    st.stop()

# 3-1 지표 카드: 선택 기간 분기당 평균 실적과 표시 관측 수(행 수)
col_kpi1, col_kpi2 = st.columns(2)
with col_kpi1:
    avg_val = view[metric].mean()
    st.metric(
        label=f"선택 조건 분기 평균 · {selected_metric_label}",
        value=f"{avg_val:,.2f} 억원",
    )
with col_kpi2:
    st.metric(
        label="표시 관측 수 (분기 × 기업)",
        value=f"{len(view):,} 건",
    )

st.divider()

# 2-9 한글 확인과 차트 세 개 (모두 Plotly 사용)
col1, col2, col3 = st.columns(3)

# 차트 1: 분기별 추이 (선 그래프)
with col1:
    fig_line = px.line(
        view,
        x="period",
        y=metric,
        color="company",
        markers=True,
        color_discrete_map=COLORS,
        title=f"분기별 {selected_metric_label} 추이",
        labels={"period": "분기", metric: selected_metric_label, "company": "기업"},
    )
    fig_line.update_layout(legend_title_text="기업")
    st.plotly_chart(fig_line, use_container_width=True)

# 차트 2: 기업별 선택 기간 평균 실적 (막대 그래프)
with col2:
    avg_by_company = (
        view.groupby("company", as_index=False)[metric]
        .mean()
        .round(2)
    )
    fig_bar_avg = px.bar(
        avg_by_company,
        x="company",
        y=metric,
        color="company",
        text_auto=".2f",
        color_discrete_map=COLORS,
        title=f"기업별 {selected_metric_label} 평균",
        labels={"company": "기업", metric: selected_metric_label},
    )
    fig_bar_avg.update_layout(showlegend=False)
    st.plotly_chart(fig_bar_avg, use_container_width=True)

# 차트 3: 기업별 기간 영업이익률 (막대 그래프: 영업이익 합계 ÷ 매출 합계 × 100)
with col3:
    margin_df = (
        view.groupby("company", as_index=False)[["sales", "profit"]]
        .sum()
    )
    margin_df["operating_margin"] = (margin_df["profit"] / margin_df["sales"] * 100).round(2)
    fig_bar_margin = px.bar(
        margin_df,
        x="company",
        y="operating_margin",
        color="company",
        text_auto=".2f",
        color_discrete_map=COLORS,
        title="기업별 기간 평균 영업이익률 (%)",
        labels={"company": "기업", "operating_margin": "영업이익률 (%)"},
    )
    fig_bar_margin.update_layout(showlegend=False)
    st.plotly_chart(fig_bar_margin, use_container_width=True)

# 4-1 표와 CSV 저장
st.subheader("상세 실적 데이터")
display_df = view.rename(
    columns={
        "period": "분기",
        "company": "기업",
        "sales": "전체 매출(억원)",
        "profit": "전체 영업이익(억원)",
        "stores": "점포 수(개)",
        "avg_sales_per_store": "점포당 평균 매출(억원)",
        "avg_profit_per_store": "점포당 평균 영업이익(억원)",
    }
)
st.dataframe(display_df, use_container_width=True, hide_index=True)

csv_bytes = view.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="현재 조회 데이터 CSV 다운로드",
    data=csv_bytes,
    file_name="emart_himart_sales_filtered.csv",
    mime="text/csv",
)