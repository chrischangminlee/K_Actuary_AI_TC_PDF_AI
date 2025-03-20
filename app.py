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

# 고급 설정 섹션
with st.expander("고급 설정"):
    starting_page = st.number_input("시작 페이지 번호", min_value=1, value=1, help="약관의 주요 내용이 시작되는 페이지 번호")
    col1, col2 = st.columns(2)
    with col1:
        chunk_size = st.number_input("청크 크기 (페이지)", min_value=1, max_value=10, value=5, help="한 번에 처리할 페이지 수")
    with col2:
        max_chunks = st.number_input("최대 청크 수", min_value=1, value=10, help="처리할 최대 청크 수 (페이지 * 청크 수 = 총 분석 페이지)")

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
        st.error(f"청크 분석 중 오류 발생: {e}")
        return ""

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
        
        # 사용자 지정 시작 페이지 적용 (인덱스는 0부터 시작하므로 1을 빼줌)
        start_page_idx = starting_page - 1
        if start_page_idx >= total_pages:
            st.error(f"시작 페이지 번호({starting_page})가 총 페이지 수({total_pages})보다 큽니다.")
            st.stop()
        
        available_pages = total_pages - start_page_idx
        max_processable_pages = chunk_size * max_chunks
        pages_to_process = min(available_pages, max_processable_pages)
        end_page_idx = start_page_idx + pages_to_process
        
        st.info(f"PDF 페이지 수: {total_pages}페이지, 분석 범위: {starting_page}~{end_page_idx} ({pages_to_process}페이지)")
        
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
            "- 무배당/배당 여부\n"
        )
        
        final_chunk_prompt = chunk_prompt + "\n\nUser Prompt: " + user_prompt
        
        # 모델 초기화
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 진행 상태 표시
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 결과 저장용 리스트
        chunk_results = []
        extraction_info = []
        
        # 각 청크 처리
        for i in range(chunks):
            chunk_start_page = start_page_idx + (i * chunk_size)
            chunk_end_page = min(start_page_idx + ((i + 1) * chunk_size), end_page_idx)
            
            status_text.text(f"처리 중... {i+1}/{chunks} 청크 (페이지 {chunk_start_page+1}-{chunk_end_page})")
            progress_bar.progress((i / chunks) * 0.8)  # 80%까지만 진행 (나머지 20%는 종합 분석용)
            
            # PDF 청크 추출
            chunk_pdf_bytes = split_pdf_bytes(pdf_bytes, chunk_start_page, chunk_end_page)
            if chunk_pdf_bytes:
                # 청크 분석
                chunk_result = analyze_pdf_chunk(model, chunk_pdf_bytes, final_chunk_prompt)
                if chunk_result:
                    chunk_results.append(chunk_result)
                    extraction_info.append(f"페이지 {chunk_start_page+1}-{chunk_end_page}: {chunk_result[:100]}...")
        
        if chunk_results:
            # 종합 분석 프롬프트
            status_text.text("최종 정보 종합 중...")
            progress_bar.progress(0.9)  # 90%
            
            summary_prompt = (
                "당신은 보험 상품 약관에서 핵심 정보를 추출하는 AI 에이전트입니다. "
                "이전에 약관의 여러 부분에서 추출한 정보를 종합하여 하나의 일관된 결과물을 만들어주세요. "
                "아래 형식으로 정보를 담보별로 구분하여 테이블 형태로 제공하세요:\n"
                "1. 상품 기본 정보 (무배당/배당 여부, 갱신형/비갱신형 등 상품 전체에 해당하는 정보)\n\n"
                "2. 담보별 정보 (담보별로 정보 구분하여 제공):\n"
                "- 담보명\n"
                "- 지급금액\n"
                "- 지급조건\n"
                "- 보장기간\n"
                "- 면책기간\n"
                "- 감액% 및 감액기간\n"
                "- 지급형태\n\n"
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
                st.success(f"추출 완료! ({starting_page}~{end_page_idx}페이지)")
                st.text_area("추출된 정보", value=final_response.text, height=300)
                
                # 디버깅 정보 (접기 가능)
                with st.expander("디버깅 정보 (각 청크별 추출 내용)"):
                    for info in extraction_info:
                        st.write(info)
                
            except Exception as e:
                st.error(f"종합 분석 중 오류 발생: {e}")
                # 오류 발생 시 개별 청크 결과 표시
                combined_result = "\n\n".join(chunk_results)
                st.text_area("개별 청크 분석 결과", value=combined_result, height=300)
        else:
            st.error("정보 추출에 실패했습니다. 다시 시도해주세요.")
