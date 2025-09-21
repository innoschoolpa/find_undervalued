# 🚀 Streamlit Cloud 배포 가이드

## 1. GitHub에 코드 업로드

### 필수 파일들
```
find_undervalued/
├── web_dashboard.py          # 메인 대시보드
├── advanced_system_upgrade.py # 시스템 고도화
├── lg_life_analysis.py       # LG생활건강 분석
├── qualitative_risk_analyzer.py
├── sector_specific_analyzer.py
├── enhanced_qualitative_integrated_analyzer.py
├── config.yaml
├── requirements.txt          # 필수 패키지 목록
└── README.md
```

### requirements.txt 생성
```txt
streamlit>=1.28.0
plotly>=5.15.0
scikit-learn>=1.3.0
pandas>=2.0.0
numpy>=1.24.0
pyyaml>=6.0
joblib>=1.3.0
aiohttp>=3.8.0
```

## 2. Streamlit Cloud 배포

1. **GitHub에 저장소 생성**
   - 새 저장소 생성 (예: `stock-analysis-dashboard`)
   - 모든 파일 업로드

2. **Streamlit Cloud 접속**
   - https://share.streamlit.io 접속
   - GitHub 계정으로 로그인

3. **앱 배포**
   - "New app" 클릭
   - Repository: `your-username/stock-analysis-dashboard`
   - Branch: `main`
   - Main file path: `web_dashboard.py`

## 3. 배포 완료 후 URL

배포가 완료되면 다음과 같은 URL이 생성됩니다:
```
https://stock-analysis-dashboard-your-username.streamlit.app
```

## 4. 네이버 API 설정

네이버 API 신청 시 웹 서비스 URL에 입력:
```
https://stock-analysis-dashboard-your-username.streamlit.app
```

## 5. 환경변수 설정 (선택사항)

Streamlit Cloud에서 환경변수 설정:
- `NAVER_API_KEY`: 네이버 API 키
- `NEWS_API_KEY`: 뉴스 API 키
- `ESG_API_KEY`: ESG API 키
