# K-Actuary 약관 정보 추출 AI Agent

보험 약관에서 중요 정보를 자동으로 추출하는 Streamlit 기반 AI 애플리케이션입니다.

## 기능

- PDF 형식의 보험 약관 업로드
- Gemini AI를 활용한 주요 보험 정보 자동 추출
- 사용자 정의 질문에 대한 응답

## 설치 방법

1. 저장소 클론
```bash
git clone [your-repository-url]
cd [repository-name]
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 필요한 패키지 설치
```bash
pip install -r requirements.txt
```

## 환경 변수 설정

1. `.env` 파일 생성:
```bash
GEMINI_API_KEY=your-gemini-api-key-here
```

2. Streamlit Cloud 배포 시:
   - Streamlit Cloud의 앱 설정에서 secrets 섹션에 Gemini API 키를 추가하세요.

## 실행 방법

로컬에서 실행:
```bash
streamlit run app.py
```

## 배포

이 앱은 Streamlit Cloud에 배포할 수 있습니다:
1. GitHub에 코드를 푸시
2. Streamlit Cloud에서 새 앱 배포
3. GitHub 저장소 연결
4. Secrets 설정에서 Gemini API 키 추가

## 주의사항

- API 키를 직접 코드에 포함하지 마세요
- `.env` 파일은 절대 GitHub에 커밋하지 마세요
- 회사 기밀이나 개인정보가 포함된 약관은 업로드하지 마세요
- Gemini AI의 응답은 참고용이며, 정확성을 보장할 수 없습니다 