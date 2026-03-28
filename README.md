# Personal Spending Report

`sample_spending.csv` 또는 사용자가 업로드한 CSV를 바탕으로 소비 리포트를 보여주는 Streamlit 데모 앱입니다.

## Features

- CSV 업로드 지원, 업로드가 없으면 기본 샘플 데이터 사용
- 총지출, 평균지출, 최다 지출 카테고리 카드 표시
- 카테고리별 지출 합계 막대그래프
- 평균보다 많이 쓴 항목을 과소비 항목으로 분리 표시
- 사용자용 3줄 요약 코멘트 자동 생성

## Run

1. 의존성 설치

```bash
pip install -r requirements.txt
```

2. Streamlit 실행

```bash
streamlit run app.py
```

3. 브라우저에서 표시되는 로컬 주소를 열어 결과를 확인합니다.

## CSV Format

CSV는 아래 컬럼을 포함해야 합니다.

- `date`
- `category`
- `amount`
