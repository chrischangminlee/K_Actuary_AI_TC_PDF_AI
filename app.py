import streamlit as st
import requests
import io
from dotenv import load_dotenv
import os
import google.generativeai as genai
from google.generativeai import types
import PyPDF2
import math
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image

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
* Gemini 2.0 flash model을 사용하여 PDF를 분석하고 있어 답변 생성 속도가 느립니다.
""")
st.sidebar.markdown('<p style="color: red; font-size: 0.8em;">(주의) 본 AI가 제공하는 답변은 참고용이며, 정확성을 보장할 수 없습니다. 보안을 위해 회사 기밀, 개인정보등은 제공하지 않기를 권장드리며, 반드시 실제 업무에 적용하기 전에 검토하시길 바랍니다.</p>', unsafe_allow_html=True)

st.sidebar.markdown("### 타 Link")
st.sidebar.markdown("[기업 AI 인사이트 플랫폼](https://chrischangminlee.github.io/Enterprise-AI-Platform/)")
st.sidebar.markdown("[기업 AI 연구소 유튜브](https://www.youtube.com/@EnterpriseAILab)")
st.sidebar.markdown("[기업 AI 정보 오픈카톡방](https://open.kakao.com/o/gbr6iuGh)")
st.sidebar.markdown("[개발자 링크드인](https://www.linkedin.com/in/chrislee9407/)")

# 메인 화면 인삿말
st.title("K-Actuary 약관 정보 추출 AI Agent")
st.write(
    "안녕하세요, K-Actuary 약관 정보 추출 AI Agent입니다.\n"
    "상품약관을 업로드 후 '상품의 정보를 추출해줘' 와 같은 프롬프트를 입력하시면, 계리 모델링에 필요한 정보를 추출합니다. 담보, 지급금액, 지급조건, 보장기간, 갱신형/비갱신형 여부, 담보별 면책기간, 담보별 감액 %, 감액기간, 지급형태, 무배당/배당 여부와 같은 정보를 추출 요청하여 보세요.\n"
)

# PDF 파일 업로드 위젯
pdf_file = st.file_uploader("보험약관 PDF 파일을 업로드하세요", type=["pdf"])
st.markdown("[예시 보험약관: 메리츠화재 공시실 - 상품종류:암보험 - 보험상품명: 무배당 메리츠 또 걸려도 또 받는 암보험2501(갱신형)약관 - 아래 약관 다운로드](https://www.meritzfire.com/disclosure/product-announcement/product-list.do#!/)")

# 예시 답변 추가
with st.expander("예시 답변"):
    # 이미지 파일 경로 설정 및 표시
    image_path = "example_response.png"
    
    if os.path.exists(image_path):
        example_image = Image.open(image_path)
        st.image(example_image, use_column_width=True)
    else:
        st.error("예시 답변 이미지를 찾을 수 없습니다.")

# 사용자 프롬프트 입력
user_prompt = st.text_input("프롬프트를 입력하세요", placeholder="예: 상품 정보 추출해줘")

def split_pdf_bytes(pdf_bytes, start_page, end_page):
    """PDF의 특정 페이지 범위를 추출하여 새 PDF 바이트로 반환"""
    try:
        # 원본 PDF 읽기
        pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
        pdf_writer = PdfWriter()
        
        # 지정된 페이지 범위 추가
        for page_num in range(start_page, min(end_page, len(pdf_reader.pages))):
            pdf_writer.add_page(pdf_reader.pages[page_num])
        
        # 새 PDF를 바이트로 변환
        output_bytes = io.BytesIO()
        pdf_writer.write(output_bytes)
        output_bytes.seek(0)
        return output_bytes.getvalue()
    except Exception as e:
        st.error(f"PDF 분할 중 오류 발생: {e}")
        return None

def analyze_pdf_chunk(model, pdf_chunk_bytes, prompt):
    """PDF 청크를 분석"""
    try:
        response = model.generate_content(
            [
                prompt,
                {"mime_type": "application/pdf", "data": pdf_chunk_bytes}
            ],
            generation_config={
                "temperature": 0.4,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
        )
        return response.text
    except Exception as e:
        return f"오류 발생: {e}"

def process_pdf_in_chunks(pdf_bytes, user_prompt, model):
    """PDF를 청크로 나누어 처리"""
    # 청크 설정
    chunk_size = 5     # 청크 크기 (한 번에 5페이지씩)
    
    # PDF 페이지 수 확인
    pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
    total_pages = len(pdf_reader.pages)
    
    # 처리할 페이지 수 계산 (모든 페이지 처리)
    pages_to_process = total_pages
    
    st.info(f"PDF 페이지 수: {total_pages}페이지, 모든 페이지를 분석합니다.")
    
    # 청크 수 계산
    chunks = math.ceil(pages_to_process / chunk_size)
    
    # 시스템 프롬프트
    chunk_prompt = (
        "당신은 보험 상품 약관에서 핵심 정보를 추출하는 AI 에이전트입니다. "
        "주어진 보험 상품 약관 PDF의 일부 페이지에서 아래 정보를 추출하세요. "
        "이 정보는 전체 약관의 일부분이며, 추출한 정보는 나중에 종합하여 분석할 것입니다.\n"
        "추출 가능한 정보만 간결하게 추출하고, 정보가 없는 항목은 '정보 없음'으로 표시하세요.\n"
        "- 담보\n"
        "- 지급금액\n"
        "- 지급조건\n"
        "- 보장기간\n"
        "- 갱신형/비갱신형 여부\n"
        "- 담보별 면책기간\n"
        "- 담보별 감액%\n"
        "- 감액기간\n"
        "- 지급형태\n"
        "- 무배당/배당 여부\n\n"
        "결과는 아래와 같은 형식의 리스트로 제공하세요:\n"
        "1. 담보명: [담보명]\n"
        "   - 지급금액: [지급금액]\n"
        "   - 지급조건: [지급조건]\n"
        "   - 보장기간: [보장기간]\n"
        "   - 면책기간: [면책기간]\n"
        "   - 감액% 및 감액기간: [감액정보]\n"
        "   - 지급형태: [지급형태]\n"
        "2. 무배당/배당 여부: [무배당/배당 정보]\n"
        "3. 갱신형/비갱신형 여부: [갱신형/비갱신형 정보]\n"
    )
    
    final_chunk_prompt = chunk_prompt + "\n\nUser Prompt: " + user_prompt
    
    # 진행 상태 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 결과 저장용 리스트
    chunk_results = []
    extraction_info = []
    
    # 각 청크 처리
    for i in range(chunks):
        chunk_start_page = i * chunk_size
        chunk_end_page = min((i + 1) * chunk_size, pages_to_process)
        
        status_text.text(f"처리 중... {i+1}/{chunks} 청크 (페이지 {chunk_start_page+1}-{chunk_end_page})")
        progress_bar.progress((i / chunks) * 0.8)  # 80%까지만 진행 (나머지 20%는 종합 분석용)
        
        # PDF 청크 추출
        chunk_pdf_bytes = split_pdf_bytes(pdf_bytes, chunk_start_page, chunk_end_page)
        if chunk_pdf_bytes:
            # 청크 분석
            chunk_result = analyze_pdf_chunk(model, chunk_pdf_bytes, final_chunk_prompt)
            if chunk_result and not chunk_result.startswith("오류 발생:"):
                chunk_results.append(chunk_result)
                extraction_info.append(f"페이지 {chunk_start_page+1}-{chunk_end_page}: {chunk_result[:100]}...")
    
    if chunk_results:
        # 종합 분석 프롬프트
        status_text.text("최종 정보 종합 중...")
        progress_bar.progress(0.9)  # 90%
        
        summary_prompt = (
            "당신은 보험 상품 약관에서 핵심 정보를 추출하는 AI 에이전트입니다. "
            "이전에 약관의 여러 부분에서 추출한 정보를 종합하여 하나의 일관된 결과물을 만들어주세요. "
            "전체 약관을 청크로 나누어서 분석을 한 것이니, 정보가 불충분하더라도 추출 가능한 내용을 최대한 체계적으로 정리하여 제공하세요. 정보가 부족하다는 말은 하지마세요.\n"
            "아래 형식으로 정보를 담보별로 구분하여 테이블 형태로 제공하세요:\n\n"
            "결과는 마크다운 테이블 형식으로 제공하세요. 예를 들어:\n"
            "| 상품 기본 정보 | |\n"
            "|---|---|\n"
            "| 무배당/배당 여부 | 무배당 |\n"
            "| 갱신형/비갱신형 여부 | 갱신형 |\n\n"
            "| 담보명 | 지급금액 | 지급조건 | 보장기간 | 면책기간 | 감액% 및 감액기간 | 지급형태 |\n"
            "|---|---|---|---|---|---|---|\n"
            "| 질병사망 | 1,000만원 | 질병으로 사망시 | 80세만기 | 없음 | 50%, 1년 | 일시금 |\n\n"
            "추출된 정보들이 서로 중복되거나 충돌할 수 있습니다. "
            "이런 경우 가장 정확하고 상세한 정보를 선택하여 종합적인 분석 결과를 제공해주세요.\n"
            "정보가 불충분하더라도 추출 가능한 내용만 체계적으로 정리하여 제공하세요. "
            "정보가 없는 경우는 '정보 없음'으로 표시하지 말고 해당 항목을 생략하세요.\n\n"
            "이전에 추출한 정보:\n"
        )
        
        # 모든 추출 결과 추가
        for i, result in enumerate(chunk_results):
            summary_prompt += f"\n--- 청크 {i+1} ---\n{result}\n---\n"
            
        summary_prompt += f"\n\nUser Prompt: {user_prompt}"
        
        try:
            # 종합 분석 수행
            final_response = model.generate_content(
                summary_prompt,
                generation_config={
                    "temperature": 0.4,
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 4096,
                }
            )
            
            progress_bar.progress(1.0)
            st.success(f"추출 완료! (전체 {total_pages}페이지)")
            
            return final_response.text, extraction_info
            
        except Exception as e:
            st.error(f"종합 분석 중 오류 발생: {e}")
            # 오류 발생 시 개별 청크 결과 합쳐서 반환
            combined_result = "\n\n".join(chunk_results)
            return combined_result, extraction_info
    else:
        return "정보 추출에 실패했습니다. 다시 시도해주세요.", []

# 전송 버튼
if st.button("전송"):
    if pdf_file is None:
        st.error("보험약관 pdf를 첨부하세요")
    else:
        # 업로드한 파일의 바이트 읽기
        pdf_bytes = pdf_file.read()
        
        # PDF 페이지 수 확인
        pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
        total_pages = len(pdf_reader.pages)
        st.info(f"PDF 페이지 수: {total_pages}페이지")
        
        # 모델 초기화
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # 시스템 프롬프트
        system_prompt = (
            "당신은 보험 상품 약관에서 핵심 정보를 추출하는 AI 에이전트입니다. "
            "주어진 보험 상품 약관 PDF에서 아래 2가지 정보를 테이블 형태로 제공하세요.담보별로 구분하여 테이블 형태로 제공하세요:\n"
            "전체 약관을 청크로 나누어서 분석을 한 것이니, 정보가 불충분하더라도 추출 가능한 내용을 최대한 체계적으로 정리하여 제공하세요. 정보가 부족하다는 말은 하지마세요.\n"
            "1 테이블: 상품명 별 기본 정보 (무배당/배당 여부: 상품명에 '무배당' 포함시 무배당, '배당형' 포함시 배당 여부, 갱신형/비갱신형 여부: 상품명에 '갱신형' 포함시 갱신형, '비갱신형' 포함시 비갱신형)\n"
            "2 테이블: 담보별로 구분하여 테이블 형태로 제공하세요:\n"
            "2. 담보별 정보 (담보별로 정보 구분하여 제공):\n"
            "- 담보명\n"
            "- 지급금액: 담보명이 있는 테이블에 '지급금액'과 같은 정보 참고\n"
            "- 지급조건: 담보명이 있는 테이블에 '지급조건'과 같은 정보 참고\n"
            "- 보장기간: 담보명이 있는 테이블에 '보장기간'과 같은 정보 참고\n"
            "- 면책기간: 담보명이 있는 테이블에 '면책기간'과 같은 정보 참고\n"
            "- 감액% 및 감액기간: 담보명이 있는 테이블에 '감액%'과 같은 정보 참고\n"
            "- 지급형태: 담보명이 있는 테이블에 '분할지급'과 같은 정보 참고\n\n"
            "결과는 마크다운 테이블 형식으로 제공하세요. 예를 들어:\n"
            "| 상품 기본 정보 | |\n"
            "|---|---|\n"
            "| 무배당/배당 여부 | 무배당 |\n"
            "| 갱신형/비갱신형 여부 | 갱신형 |\n\n"
            "| 담보명 | 지급금액 | 지급조건 | 보장기간 | 면책기간 | 감액% 및 감액기간 | 지급형태 |\n"
            "|---|---|---|---|---|---|---|\n"
            "| 질병사망 | 1,000만원 | 질병으로 사망시 | 80세만기 | 없음 | 50%, 1년 | 일시금 |\n"
        )
        
        final_chunk_prompt = system_prompt + "\n\nUser Prompt: " + user_prompt
        
        # 진행 상태 표시
        with st.spinner("PDF 분석 중..."):
            # 바로 청크 단위로 처리 시작
            result_text, extraction_info = process_pdf_in_chunks(pdf_bytes, user_prompt, model)
            
            # 결과에 마크다운 테이블이 포함되어 있는지 확인
            if "|---" in result_text and "| " in result_text:
                # 마크다운 테이블을 HTML로 렌더링
                st.markdown(result_text)
            else:
                # 일반 텍스트로 표시
                st.text_area("추출된 정보", value=result_text, height=300)
            
            # 디버깅 정보 (접기 가능)
            if extraction_info:
                with st.expander("디버깅 정보 (각 청크별 추출 내용)"):
                    for info in extraction_info:
                        st.write(info)
