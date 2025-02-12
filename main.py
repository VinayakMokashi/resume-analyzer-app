import streamlit as st
from groq import Groq
import PyPDF2
import io
import os
import time
import logging

os.write(1,b'Something was executed.\n')

# Configure Streamlit page
st.set_page_config(
    page_title="Resume Analyzer",
    page_icon="📝",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .analysis-box {
        padding: 20px;
        border-radius: 10px;
        background-color: #f0f2f6;
        margin: 10px 0;
    }
    .match-score {
        font-size: 24px;
        font-weight: bold;
        color: #0066cc;
    }
    </style>
    """, unsafe_allow_html=True)

def initialize_groq_client():
    """Initialize and return Groq client"""
    return Groq(api_key=os.environ.get("GROQ_API_KEY"))

def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        return None

def analyze_resume(client, resume_text, job_description):
    """Analyze resume against job description using Groq API"""
    prompt = f"""
    As an expert resume analyzer, review the following resume against the job description.
    Provide a detailed analysis including:
    1. Match Score (0-100)
    2. Key Qualifications Match
    3. Missing Skills/Requirements
    4. Strengths
    5. Areas for Improvement
    6. Suggested Resume Improvements
    
    Resume:
    {resume_text}
    
    Job Description:
    {job_description}
    
    Provide the analysis in a clear, structured format.
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek-r1-distill-qwen-32b",
            messages=[
                {"role": "system", "content": "You are an expert resume analyzer and career coach."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error during analysis: {str(e)}")
        return None

def main():
    st.title("📝 Resume Analyzer")
    st.write("Upload your resume and paste the job description to get a detailed analysis")

    # Initialize Groq client
    client = initialize_groq_client()

    # File upload for resume
    uploaded_file = st.file_uploader("Upload your resume (PDF)", type=['pdf'])
    
    # Job description input
    job_description = st.text_area(
        "Paste the job description here",
        height=200,
        help="Paste the complete job description including requirements and qualifications"
    )

    # Create columns for resume text and analysis
    if uploaded_file and job_description:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Extracted Resume Text")
            # Extract and display resume text
            resume_text = extract_text_from_pdf(uploaded_file)
            if resume_text:
                st.text_area("Extracted Text", resume_text, height=400)
            
        with col2:
            st.subheader("Analysis")
            if st.button("Analyze Resume"):
                with st.spinner("Analyzing your resume..."):
                    # Add a small delay to show the spinner
                    time.sleep(1)
                    analysis = analyze_resume(client, resume_text, job_description)
                    logging.debug("Analysis results: %s", analysis)
                    if analysis:
                        st.markdown(f'<div class="analysis-box">{analysis}</div>', 
                                  unsafe_allow_html=True)
                        
                        # Add download button for analysis
                        analysis_bytes = analysis.encode()
                        st.download_button(
                            label="Download Analysis",
                            data=analysis_bytes,
                            file_name="resume_analysis.txt",
                            mime="text/plain"
                        )

    # Add helpful information
    with st.expander("💡 Tips for better results"):
        st.markdown("""
        ### For best results:
        1. Make sure your PDF is text-searchable (not scanned)
        2. Include the complete job description
        3. Ensure your resume is up-to-date
        4. Include relevant keywords from the job description
        
        ### What we analyze:
        - Skills match
        - Experience alignment
        - Education requirements
        - Technical qualifications
        - Soft skills
        - Keywords match
        """)

if __name__ == "__main__":
    main()