import streamlit as st
import requests
import io
from dotenv import load_dotenv
import os
import google.generativeai as genai
from google.generativeai import types

# Load environment variables
load_dotenv()

# 페이지 기본 설정
st.set_page_config(page_title="K-Actuary 약관 정보 추출 AI Agent", layout="wide")

# API 키 설정
def get_api_key():
    """Get API key from environment variable or Streamlit secrets"""
    # Try to get from Streamlit secrets first (for production)
    if 'gemini_api_key' in st.secrets:
        return st.secrets['gemini_api_key']
    # Fallback to environment variable (for local development)
    return os.getenv('GEMINI_API_KEY')

# API 키 확인 및 설정
api_key = get_api_key()
if not api_key:
    st.error('Gemini API 키가 설정되지 않았습니다. .env 파일이나 Streamlit secrets에 API 키를 설정해주세요.')
    st.stop()

# Gemini API 설정
genai.configure(api_key=api_key)

# 왼쪽 사이드바 내용
st.sidebar.title("소개")
st.sidebar.markdown("""
본 AI 챗 서비스는 한국 계리업무를 수행하는 계리사를 위해 개발된 개인 프로젝트로 만들어진 AI Chatbot / Agent입니다.
                    
본 pdf 분석 AI Agent와 더불어 현재 다양한 유용한 기능들이 지속적으로 개발 중이며, 보다 향상된 서비스를 제공하기 위해 개선을 이어가고 있습니다.
* Gemini 1.5 flash model을 사용하여 PDF를 분석하고 있어 답변 생성 속도가 느립니다.
""")
st.sidebar.markdown('<p style="color: red; font-size: 0.8em;">(주의) 본 AI가 제공하는 답변은 참고용이며, 정확성을 보장할 수 없습니다. 보안을 위해 회사 기밀, 개인정보등은 제공하지 않기를 권장드리며, 반드시 실제 업무에 적용하기 전에 검토하시길 바랍니다.</p>', unsafe_allow_html=True)

st.sidebar.markdown("### 타 Link")
st.sidebar.markdown("[개발자 링크드인](https://www.linkedin.com/in/chrislee9407/)")
st.sidebar.markdown("[K-계리 AI 플랫폼](https://chrischangminlee.github.io/K_Actuary_AI_Agent_Platform/)")
st.sidebar.markdown("[K Actuary AI Agent](https://kactuaryagent.streamlit.app/)")

# 메인 화면 인삿말
st.title("K-Actuary 약관 정보 추출 AI Agent")
st.write(
    "안녕하세요, K-Actuary 약관 정보 추출 AI Agent입니다. "
    "상품약관을 업로드 후 '상품의 면책기간을 추출해줘' 와 같은 프롬프트를 입력하시면, 계리 모델링에 필요한 정보를 추출합니다. 담보, 지급금액, 지급조건, 보장기간, 갱신형/비갱신형 여부, 담보별 면책기간, 담보별 감액 %, 감액기간, 지급형태, 무배당/배당 여부와 같은 정보를 추출요청하여 보세요."
)

# PDF 파일 업로드 위젯
pdf_file = st.file_uploader("보험약관 PDF 파일을 업로드하세요", type=["pdf"])

# 사용자 프롬프트 입력
user_prompt = st.text_input("프롬프트를 입력하세요", placeholder="예: 상품의 면책기간을 추출해줘")

# 전송 버튼
if st.button("전송"):
    if pdf_file is None:
        st.error("보험약관 pdf를 첨부하세요")
    else:
        # 업로드한 파일의 바이트 읽기
        pdf_bytes = pdf_file.read()
        
        # 시스템 프롬프트
        system_prompt = (
            "당신은 보험 상품 약관에서 핵심 정보를 추출하는 AI 에이전트입니다. "
            "주어진 보험 상품 약관 PDF에서 아래 최대한 담보별로 정보를 명확하고 간결하게 추출하여서 테이블 형태로 제공하세요:\n"
            "- 담보\n"
            "- 지급금액\n"
            "- 지급조건\n"
            "- 보장기간\n"
            "- 갱신형/비갱신형 여부\n"
            "- 담보별 면책기간\n"
            "- 담보별 감액%\n"
            "- 감액기간\n"
            "- 지급형태\n"
            "- 무배당/배당 여부\n"
        )
        final_prompt = system_prompt + "\n\nUser Prompt: " + user_prompt

        # 모델 초기화
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 진행 상태 표시
        with st.spinner("PDF 분석 중..."):
            try:
                # PDF 직접 처리
                response = model.generate_content(
                    [
                        final_prompt,
                        {"mime_type": "application/pdf", "data": pdf_bytes}
                    ],
                    generation_config={
                        "temperature": 0.4,
                        "top_p": 0.8,
                        "top_k": 40,
                        "max_output_tokens": 2048,
                    }
                )
                
                st.success("추출 완료!")
                st.text_area("추출된 정보", value=response.text, height=300)
            except Exception as e:
                st.error("PDF 분석 중 오류가 발생했습니다.")
                st.error(e)
                st.info("PDF 파일이 너무 크거나 복잡할 수 있습니다. 다시 시도해보세요.")
