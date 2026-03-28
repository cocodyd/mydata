from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── 페이지 설정 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="마이데이터 AI 분석 데모",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(180deg, #f0f4ff 0%, #fafbff 100%); }
    .block-container { padding-top: 1.8rem; padding-bottom: 2rem; max-width: 1200px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── 상수 ──────────────────────────────────────────────────────────────────────
SEGMENT_COLORS: dict[str, str] = {
    "VIP": "#FFB300",
    "일반": "#43A047",
    "절약형": "#1E88E5",
    "비활성": "#757575",
}

SEGMENT_EMOJI: dict[str, str] = {
    "VIP": "👑",
    "일반": "👤",
    "절약형": "💰",
    "비활성": "😴",
}

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "dummy_data.csv")


# ── 데이터 로드 ────────────────────────────────────────────────────────────────
@st.cache_data
def load_data() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


def format_won(amount: float) -> str:
    if amount >= 100_000_000:
        return f"{amount / 100_000_000:.1f}억원"
    if amount >= 10_000:
        return f"{amount / 10_000:.0f}만원"
    return f"{amount:,.0f}원"


# ── 사이드바 ───────────────────────────────────────────────────────────────────
def build_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.title("🔎 필터 설정")

    segments = st.sidebar.multiselect(
        "고객 세그먼트",
        options=["VIP", "일반", "절약형", "비활성"],
        default=["VIP", "일반", "절약형", "비활성"],
    )

    age_min, age_max = int(df["age"].min()), int(df["age"].max())
    age_range = st.sidebar.slider("나이 범위", age_min, age_max, (age_min, age_max))

    income_min = int(df["income"].min() / 10_000)
    income_max = int(df["income"].max() / 10_000)
    income_range = st.sidebar.slider(
        "월소득 범위 (만원)", income_min, income_max, (income_min, income_max)
    )

    gender = st.sidebar.multiselect("성별", ["M", "F"], default=["M", "F"])

    filtered = df[
        df["segment"].isin(segments)
        & df["age"].between(age_range[0], age_range[1])
        & df["income"].between(income_range[0] * 10_000, income_range[1] * 10_000)
        & df["gender"].isin(gender)
    ]

    st.sidebar.markdown("---")
    st.sidebar.metric("선택된 고객", f"{len(filtered)}명", f"전체 {len(df)}명 중")

    return filtered


# ── 탭 1 : 전체 개요 ───────────────────────────────────────────────────────────
def tab_overview(df: pd.DataFrame) -> None:
    # KPI 카드
    col1, col2, col3, col4, col5 = st.columns(5)
    kpis = [
        ("총 고객 수", f"{len(df):,}명", ""),
        ("평균 월소득", format_won(df["income"].mean()), ""),
        ("평균 월지출", format_won(df["monthly_spending"].mean()), ""),
        ("평균 신용점수", f"{df['credit_score'].mean():.0f}점", ""),
        ("평균 저축률", f"{df['savings_rate'].mean():.1%}", ""),
    ]
    for col, (title, val, sub) in zip([col1, col2, col3, col4, col5], kpis):
        col.metric(title, val, sub or None)

    st.markdown("---")

    col_pie, col_bar = st.columns(2)

    with col_pie:
        seg_cnt = df["segment"].value_counts().reset_index()
        seg_cnt.columns = ["segment", "count"]
        fig = px.pie(
            seg_cnt,
            values="count",
            names="segment",
            title="고객 세그먼트 분포",
            color="segment",
            color_discrete_map=SEGMENT_COLORS,
            hole=0.42,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label+value")
        fig.update_layout(margin=dict(t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col_bar:
        seg_agg = (
            df.groupby("segment")
            .agg(평균월소득=("income", "mean"), 평균월지출=("monthly_spending", "mean"))
            .reset_index()
        )
        fig2 = go.Figure()
        for col_name, opacity in [("평균월소득", 1.0), ("평균월지출", 0.65)]:
            fig2.add_trace(
                go.Bar(
                    name=col_name,
                    x=seg_agg["segment"],
                    y=seg_agg[col_name] / 10_000,
                    marker_color=[SEGMENT_COLORS[s] for s in seg_agg["segment"]],
                    opacity=opacity,
                )
            )
        fig2.update_layout(
            title="세그먼트별 평균 소득 / 지출 (만원)",
            barmode="group",
            xaxis_title="세그먼트",
            yaxis_title="금액 (만원)",
            margin=dict(t=50, b=20),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # 요약 테이블
    st.subheader("세그먼트별 주요 지표 요약")
    summary = (
        df.groupby("segment")
        .agg(
            고객수=("customer_id", "count"),
            평균나이=("age", "mean"),
            평균월소득=("income", "mean"),
            평균월지출=("monthly_spending", "mean"),
            평균저축률=("savings_rate", "mean"),
            평균신용점수=("credit_score", "mean"),
            평균거래횟수=("transaction_count", "mean"),
        )
        .round(1)
        .reset_index()
    )
    summary["평균월소득"] = summary["평균월소득"].apply(format_won)
    summary["평균월지출"] = summary["평균월지출"].apply(format_won)
    summary["평균저축률"] = summary["평균저축률"].apply(lambda x: f"{x:.1%}")
    st.dataframe(summary, use_container_width=True, hide_index=True)


# ── 탭 2 : 세그먼트 분석 ─────────────────────────────────────────────────────
def tab_segment(df: pd.DataFrame) -> None:
    st.subheader("세그먼트별 심층 분석")

    col1, col2 = st.columns(2)

    with col1:
        fig = px.box(
            df,
            x="segment",
            y="income",
            color="segment",
            color_discrete_map=SEGMENT_COLORS,
            title="세그먼트별 월소득 분포",
            labels={"income": "월소득 (원)", "segment": "세그먼트"},
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.scatter(
            df,
            x="income",
            y="monthly_spending",
            color="segment",
            color_discrete_map=SEGMENT_COLORS,
            title="월소득 vs 월지출",
            labels={"income": "월소득 (원)", "monthly_spending": "월지출 (원)"},
            hover_data=["customer_id", "age", "credit_score"],
            opacity=0.8,
        )
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        fig = px.violin(
            df,
            x="segment",
            y="savings_rate",
            color="segment",
            color_discrete_map=SEGMENT_COLORS,
            title="세그먼트별 저축률 분포",
            labels={"savings_rate": "저축률", "segment": "세그먼트"},
            box=True,
        )
        fig.update_layout(yaxis_tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        fig = px.scatter(
            df,
            x="days_since_last_transaction",
            y="transaction_count",
            color="segment",
            color_discrete_map=SEGMENT_COLORS,
            size="income",
            title="거래 활성도 분석",
            labels={
                "days_since_last_transaction": "마지막 거래 후 경과일",
                "transaction_count": "월 거래 횟수",
            },
            hover_data=["customer_id", "segment"],
            opacity=0.75,
        )
        st.plotly_chart(fig, use_container_width=True)

    # 레이더 차트
    st.subheader("세그먼트 특성 비교 (레이더 차트)")
    seg_avg = (
        df.groupby("segment")
        .agg(
            income=("income", "mean"),
            monthly_spending=("monthly_spending", "mean"),
            transaction_count=("transaction_count", "mean"),
            savings_rate=("savings_rate", "mean"),
            credit_score=("credit_score", "mean"),
        )
        .reset_index()
    )

    # 0-1 정규화
    for c in ["income", "monthly_spending", "transaction_count", "savings_rate", "credit_score"]:
        lo, hi = seg_avg[c].min(), seg_avg[c].max()
        seg_avg[c + "_n"] = (seg_avg[c] - lo) / (hi - lo) if hi != lo else 0.5

    categories = ["월소득", "월지출", "거래횟수", "저축률", "신용점수"]
    norm_cols = [c + "_n" for c in ["income", "monthly_spending", "transaction_count", "savings_rate", "credit_score"]]

    fig = go.Figure()
    for _, row in seg_avg.iterrows():
        vals = [row[c] for c in norm_cols] + [row[norm_cols[0]]]
        fig.add_trace(
            go.Scatterpolar(
                r=vals,
                theta=categories + [categories[0]],
                fill="toself",
                name=row["segment"],
                line_color=SEGMENT_COLORS.get(row["segment"], "#888"),
                opacity=0.6,
            )
        )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="세그먼트별 특성 비교 (정규화 0~1)",
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)


# ── 탭 3 : 고객 상세 ──────────────────────────────────────────────────────────
def tab_detail(df: pd.DataFrame) -> None:
    st.subheader("고객 상세 데이터")

    credit_min = st.slider("최소 신용점수 필터", 500, 1000, 500)
    detail = df[df["credit_score"] >= credit_min].copy()

    disp = detail.copy()
    disp["income"] = disp["income"].apply(format_won)
    disp["monthly_spending"] = disp["monthly_spending"].apply(format_won)
    disp["loan_balance"] = disp["loan_balance"].apply(format_won)
    disp["savings_rate"] = disp["savings_rate"].apply(lambda x: f"{x:.1%}")
    disp.columns = [
        "고객ID", "나이", "성별", "월소득", "월지출",
        "거래횟수", "마지막거래(일전)", "저축률", "대출잔액",
        "신용점수", "보유계좌수", "세그먼트",
    ]

    st.markdown(f"**{len(disp):,}명** 표시 중")
    st.dataframe(disp, use_container_width=True, hide_index=True)

    csv_bytes = detail.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="⬇️ CSV 다운로드",
        data=csv_bytes,
        file_name="mydata_filtered.csv",
        mime="text/csv",
    )


# ── 탭 4 : AI 인사이트 ────────────────────────────────────────────────────────
RECOMMENDATIONS: dict[str, list[str]] = {
    "VIP": [
        "👑 **프리미엄 자산관리 서비스 제안** — 평균 소득이 높은 VIP 고객에게 맞춤형 투자 포트폴리오 상담을 제공하세요.",
        "💳 **프리미엄 카드 업그레이드** — 월 거래 빈도가 높으므로 포인트 적립률이 높은 플래티넘 카드를 추천하세요.",
        "🏡 **부동산·투자 크로스셀링** — 대출 잔액이 있는 VIP에게 금리 우대 및 담보대출 재구성을 제안하세요.",
        "📱 **VIP 전담 PB 연결** — 실시간 자산 현황 알림과 전담 매니저 1:1 채널을 제공하세요.",
    ],
    "일반": [
        "📊 **자산 증대 플랜** — 저축률 향상을 위한 자동이체 적금 및 목돈 마련 상품을 추천하세요.",
        "💡 **생활비 절약 서비스** — 지출 패턴 분석 기반으로 카테고리별 절약 팁과 할인 혜택을 제공하세요.",
        "📈 **중위험 투자 상품** — 안정적인 소득을 바탕으로 중위험-중수익 펀드 또는 ETF를 소개하세요.",
        "🔄 **대출 금리 최적화** — 보유 대출의 금리를 점검하고 더 낮은 금리 상품으로 전환을 안내하세요.",
    ],
    "절약형": [
        "🏦 **고금리 예·적금 우선 안내** — 최고 금리 정기예금 및 특판 상품을 제일 먼저 안내하세요.",
        "🏆 **저축 챌린지 프로그램** — 월별 저축 목표 달성 시 보너스 이자를 제공하는 캠페인을 기획하세요.",
        "🛡️ **보장성 보험 리뷰** — 안정 지향 성향을 고려해 실손의료보험 및 종신보험 재점검을 제안하세요.",
        "💡 **ISA 계좌 절세 투자** — 소액 투자 진입 장벽을 낮춰 절세 투자 첫 경험을 도와드리세요.",
    ],
    "비활성": [
        "📩 **재활성화 캠페인** — 특별 이자율 혜택과 함께 서비스 재이용을 개인화 메시지로 권유하세요.",
        "🎁 **복귀 혜택 제공** — 앱 재접속 시 포인트 적립 또는 수수료 면제 쿠폰으로 활성화를 유도하세요.",
        "📞 **1:1 맞춤 상담** — 비활성 원인 파악을 위한 짧은 설문 또는 상담 연결 서비스를 제공하세요.",
        "📱 **앱 UX 가이드 발송** — 주요 기능 튜토리얼 푸시 알림으로 서비스 재진입 장벽을 낮추세요.",
    ],
    "전체": [
        "🗂️ **통합 포트폴리오 분석** — 세그먼트 데이터를 종합해 CLV(고객 생애 가치) 예측 모델을 구축하세요.",
        "🎯 **세그먼트별 맞춤 마케팅** — 각 고객 그룹의 특성에 맞는 차별화된 커뮤니케이션 전략을 수립하세요.",
        "🔄 **세그먼트 이동 모니터링** — 고객의 세그먼트 변화를 추적해 상향/하향 이동 패턴을 분석하세요.",
        "⚡ **실시간 이상 거래 탐지** — 비활성 고객의 갑작스러운 고액 거래를 이상 징후로 모니터링하세요.",
    ],
}


def tab_insights(df: pd.DataFrame) -> None:
    st.subheader("AI 기반 고객 인사이트")

    selected = st.selectbox(
        "분석할 세그먼트",
        ["전체", "VIP", "일반", "절약형", "비활성"],
        format_func=lambda s: f"{SEGMENT_EMOJI.get(s, '')} {s}",
    )

    analysis = df if selected == "전체" else df[df["segment"] == selected]

    if analysis.empty:
        st.warning("선택된 조건에 해당하는 고객이 없습니다.")
        return

    # 주요 지표 + 추천 전략
    col_metrics, col_reco = st.columns([1, 1], gap="large")

    with col_metrics:
        st.markdown("### 📈 주요 지표")
        spend_ratio = analysis["monthly_spending"].mean() / analysis["income"].mean()
        high_loan_cnt = (analysis["loan_balance"] > 10_000_000).sum()
        rows = [
            ("평균 월소득", format_won(analysis["income"].mean())),
            ("평균 월지출", format_won(analysis["monthly_spending"].mean())),
            ("소득 대비 지출률", f"{spend_ratio:.1%}"),
            ("평균 저축률", f"{analysis['savings_rate'].mean():.1%}"),
            ("평균 신용점수", f"{analysis['credit_score'].mean():.0f}점"),
            ("평균 거래횟수", f"{analysis['transaction_count'].mean():.1f}회/월"),
            ("마지막 거래 경과", f"{analysis['days_since_last_transaction'].mean():.1f}일 전"),
            ("고액 대출자 비율", f"{high_loan_cnt}/{len(analysis)}명 ({high_loan_cnt/len(analysis):.1%})"),
        ]
        st.dataframe(
            pd.DataFrame(rows, columns=["지표", "값"]),
            use_container_width=True,
            hide_index=True,
        )

    with col_reco:
        st.markdown("### 💡 AI 추천 전략")
        for rec in RECOMMENDATIONS[selected]:
            st.markdown(f"> {rec}")
            st.markdown("")

    # 리스크 분석
    st.markdown("---")
    st.subheader("⚠️ 리스크 분석")

    c1, c2, c3 = st.columns(3)
    high_loan = analysis[analysis["loan_balance"] > 10_000_000]
    low_credit = analysis[analysis["credit_score"] < 600]
    risk_group = analysis[
        (analysis["days_since_last_transaction"] > 30) & (analysis["loan_balance"] > 5_000_000)
    ]

    c1.metric("고액 대출 고객", f"{len(high_loan)}명", f"{len(high_loan)/len(analysis)*100:.1f}%")
    c2.metric("저신용 고객 (600 미만)", f"{len(low_credit)}명", f"{len(low_credit)/len(analysis)*100:.1f}%")
    c3.metric("비활성+대출 위험군", f"{len(risk_group)}명", f"{len(risk_group)/len(analysis)*100:.1f}%")

    fig = px.bar(
        df.groupby("segment")["loan_balance"].mean().reset_index(),
        x="segment",
        y="loan_balance",
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        title="세그먼트별 평균 대출 잔액",
        labels={"loan_balance": "평균 대출 잔액 (원)", "segment": "세그먼트"},
        text_auto=".3s",
    )
    st.plotly_chart(fig, use_container_width=True)

    # 신용점수 히스토그램
    fig2 = px.histogram(
        analysis,
        x="credit_score",
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        nbins=20,
        title="신용점수 분포",
        labels={"credit_score": "신용점수", "count": "고객 수"},
        barmode="overlay",
        opacity=0.7,
    )
    st.plotly_chart(fig2, use_container_width=True)


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main() -> None:
    df_full = load_data()
    filtered = build_sidebar(df_full)

    st.title("🏦 마이데이터 AI 분석 대시보드")
    st.caption("80명의 더미 고객 데이터 기반 — VIP · 일반 · 절약형 · 비활성 4개 세그먼트 분석")
    st.markdown("---")

    if filtered.empty:
        st.warning("선택된 조건에 해당하는 고객이 없습니다. 필터를 조정해주세요.")
        return

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 전체 개요", "🔍 세그먼트 분석", "👤 고객 상세", "🤖 AI 인사이트"]
    )

    with tab1:
        tab_overview(filtered)
    with tab2:
        tab_segment(filtered)
    with tab3:
        tab_detail(filtered)
    with tab4:
        tab_insights(filtered)


if __name__ == "__main__":
    main()
