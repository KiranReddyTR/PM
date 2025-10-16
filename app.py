import streamlit as st
import requests
import pandas as pd
import pdfplumber
import docx2txt
import numpy as np
import matplotlib.pyplot as plt
from sentence_transformers import SentenceTransformer, util
import googleapiclient.discovery
import spacy
from spacy.cli import download
from streamlit_lottie import st_lottie
import streamlit.components.v1 as components

# -----------------------------
# Page config & theme
# -----------------------------
st.set_page_config(page_title="AI Resume Analyzer — Pro Edition", layout="wide")

# Custom CSS for dark theme
st.markdown("""
<style>
.stApp { background: linear-gradient(180deg, #0a1121 0%, #0e1b35 100%); color: #e8ecf2; }
.stButton>button { background: linear-gradient(90deg,#0ea5e9,#6366f1); color: white; border:none; border-radius:8px; }
.metric-box { padding:1.5rem; border-radius:16px; background:linear-gradient(180deg, rgba(37,99,235,0.15), rgba(14,165,233,0.08)); text-align:center; }
.skill-section { background: rgba(255,255,255,0.05); padding:1rem; border-radius:12px; }
.pill { display:inline-block; padding:8px 12px; border-radius:999px; background:rgba(255,255,255,0.08); margin:5px; font-size:14px; }
.card { padding: 1rem; border-radius: 12px; background: rgba(255,255,255,0.03); box-shadow: 0 6px 18px rgba(0,0,0,0.3); }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Load NLP model
# -----------------------------
model_name = "en_core_web_md"
try:
    nlp = spacy.load(model_name)
except OSError:
    download(model_name)
    nlp = spacy.load(model_name)

st_model = SentenceTransformer('all-MiniLM-L6-v2')

# YouTube API
YOUTUBE_API_KEY = "YOUR_YOUTUBE_API_KEY"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# -----------------------------
# Session state
# -----------------------------
if "skills_analyzed" not in st.session_state:
    st.session_state.skills_analyzed = False
    st.session_state.show_courses = False
    st.session_state.missing_skills = []
    st.session_state.matching_score = 0.0
    st.session_state.resume_skills = []
    st.session_state.job_skills = []
    st.session_state.resume_text = ""
    st.session_state.job_text = ""

# -----------------------------
# Helper functions
# -----------------------------
def fetch_youtube_courses(skill):
    try:
        youtube = googleapiclient.discovery.build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(q=f"{skill} course", part="snippet", maxResults=6, type="video")
        response = request.execute()
        return [
            {
                "Title": item["snippet"]["title"],
                "Channel": item["snippet"]["channelTitle"],
                "Video Link": f'https://www.youtube.com/watch?v={item["id"]["videoId"]}',
                "Thumbnail": item["snippet"]["thumbnails"].get("medium", {}).get("url", "")
            }
            for item in response.get("items", [])
        ]
    except:
        return []

def extract_text(uploaded_file):
    if uploaded_file:
        ext = uploaded_file.name.split(".")[-1].lower()
        if ext == "pdf":
            with pdfplumber.open(uploaded_file) as pdf:
                return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()]) or "No text extracted."
        elif ext in ["docx", "doc"]:
            return docx2txt.process(uploaded_file) or "No text extracted."
        elif ext == "txt":
            return uploaded_file.read().decode("utf-8") or "No text extracted."
    return "No text extracted."

def generate_summary(text):
    sentences = text.split(". ")[:3]
    return "... ".join(sentences) + "..." if sentences else "No content extracted."

def extract_skills(text):
    doc = nlp(text)
    skills = set()
    for ent in doc.ents:
        if ent.label_ == "ORG":
            skills.add(ent.text)
    return list(skills)

def calculate_matching_score(resume_text, job_text):
    embeddings = st_model.encode([resume_text, job_text], convert_to_tensor=True)
    return round(float(util.pytorch_cos_sim(embeddings[0], embeddings[1])[0]), 2) * 100

def plot_skill_distribution_pie(resume_skills, job_skills):
    resume_labels = list(resume_skills) if resume_skills else ["No Skills Found"]
    resume_sizes = [1] * len(resume_skills) if resume_skills else [1]
    job_labels = list(job_skills) if job_skills else ["No Skills Found"]
    job_sizes = [1] * len(job_skills) if job_skills else [1]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].pie(resume_sizes, labels=resume_labels, autopct='%1.1f%%', startangle=90)
    axes[0].set_title("Resume Skills")
    axes[1].pie(job_sizes, labels=job_labels, autopct='%1.1f%%', startangle=90)
    axes[1].set_title("Job Skills")
    st.pyplot(fig)

def load_lottie_url(url: str):
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()
    except:
        return None
    return None

LOTTIE_UPLOAD = load_lottie_url("https://assets2.lottiefiles.com/packages/lf20_w51pcehl.json")
LOTTIE_ANALYZE = load_lottie_url("https://assets7.lottiefiles.com/private_files/lf30_p9bui5ul.json")
LOTTIE_SCORE = load_lottie_url("https://assets6.lottiefiles.com/packages/lf20_g8n0xqbm.json")

# -----------------------------
# Navigation
# -----------------------------
page = st.sidebar.radio("📂 Navigate", ["📄 Upload Documents", "📝 Summaries", "🧠 Analysis", "📊 Insights & Courses"])
if st.sidebar.button("Reset All"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.experimental_rerun()

# -----------------------------
# Page 1: Upload Documents
# -----------------------------
if page == "📄 Upload Documents":
    st.markdown("# 📂 Upload Your Documents")
    col1, col2 = st.columns(2)
    with col1:
        resume_file = st.file_uploader("📄 Upload Resume", type=["pdf", "docx", "txt"])
        if resume_file:
            st.session_state.resume_text = extract_text(resume_file)
            st.success("Resume Uploaded Successfully!")
            if LOTTIE_UPLOAD: st_lottie(LOTTIE_UPLOAD, height=180)
    with col2:
        job_file = st.file_uploader("💼 Upload Job Description", type=["pdf", "docx", "txt"])
        if job_file:
            st.session_state.job_text = extract_text(job_file)
            st.success("Job Description Uploaded Successfully!")

# -----------------------------
# Page 2: Summaries
# -----------------------------
elif page == "📝 Summaries":
    st.header("📝 Resume & Job Description Summaries")
    if not st.session_state.resume_text or not st.session_state.job_text:
        st.warning("Please upload both Resume and Job Description first.")
    else:
        colA, colB = st.columns(2)
        with colA: st.subheader("🧾 Resume Summary"); st.info(generate_summary(st.session_state.resume_text))
        with colB: st.subheader("💼 Job Description Summary"); st.info(generate_summary(st.session_state.job_text))
        if st.button("Analyze Skills & Matching Score"):
            resume_skills = extract_skills(st.session_state.resume_text)
            job_skills = extract_skills(st.session_state.job_text)
            st.session_state.skills_analyzed = True
            st.session_state.resume_skills = resume_skills
            st.session_state.job_skills = job_skills
            st.session_state.missing_skills = list(set(job_skills)-set(resume_skills))
            st.session_state.matching_score = calculate_matching_score(st.session_state.resume_text, st.session_state.job_text)
            st.success("Analysis complete ✅")

# -----------------------------
# Page 3: Analysis
# -----------------------------
elif page == "🧠 Analysis":
    st.header("🧠 AI Resume Analysis Dashboard")
    if not st.session_state.skills_analyzed:
        st.warning("Run analysis first from the Summaries page.")
    else:
        st.subheader("📊 Resume Matching Score")
        if LOTTIE_SCORE: st_lottie(LOTTIE_SCORE, height=180)
        st.markdown(f"<div class='metric-box'><h1 style='font-size:60px'>{st.session_state.matching_score:.1f}%</h1><p>Overall Similarity</p></div>", unsafe_allow_html=True)
        st.subheader("🧾 Extracted Skills")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Resume Skills"); st.markdown("<div class='skill-section'>", unsafe_allow_html=True)
            for s in st.session_state.resume_skills: st.markdown(f"<span class='pill'>{s}</span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with col2:
            st.markdown("### Job Description Skills"); st.markdown("<div class='skill-section'>", unsafe_allow_html=True)
            for s in st.session_state.job_skills: st.markdown(f"<span class='pill'>{s}</span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        st.subheader("📈 Visual Skill Comparison")
        plot_skill_distribution_pie(st.session_state.resume_skills, st.session_state.job_skills)

# -----------------------------
# Page 4: Insights & Courses
# -----------------------------
elif page == "📊 Insights & Courses":
    st.header("📚 Personalized Insights & YouTube Recommendations")
    if not st.session_state.skills_analyzed:
        st.warning("Please run the analysis first.")
    else:
        st.subheader("⚙️ Missing Skills")
        if st.session_state.missing_skills:
            st.write(", ".join(st.session_state.missing_skills))
            if st.button("Show Recommended Courses"):
                all_courses = []
                for skill in st.session_state.missing_skills: all_courses.extend(fetch_youtube_courses(skill))
                if all_courses:
                    for video in all_courses:
                        colA, colB = st.columns([1,4])
                        with colA: 
                            if video.get('Thumbnail'): st.image(video['Thumbnail'], width=160)
                        with colB:
                            st.markdown(f"**[{video['Title']}]({video['Video Link']})**")
                            st.markdown(f"Channel: {video['Channel']}")
                            vid_id = video['Video Link'].split('v=')[-1]
                            components.iframe(f"https://www.youtube.com/embed/{vid_id}", height=190)
                else: st.warning("No courses found or API quota reached.")
        else: st.success("Great! No missing skills detected.")
