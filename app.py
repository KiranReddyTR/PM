import streamlit as st
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit.components.v1 as components

# Optional heavy packages
try:
    import docx2txt
except ImportError:
    docx2txt = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import spacy
    from spacy.cli import download
except ImportError:
    spacy = None

from streamlit_lottie import st_lottie

# -----------------------------
# Page config & dark theme
# -----------------------------
st.set_page_config(page_title="AI Resume Analyzer — Pro Edition", layout="wide")
st.markdown("""
<style>
.stApp { background: linear-gradient(180deg, #0a1121 0%, #0e1b35 100%); color: #e8ecf2; }
.stButton>button { background: linear-gradient(90deg,#0ea5e9,#6366f1); color: white; border:none; border-radius:8px; }
.metric-box { padding:1.5rem; border-radius:16px; background:linear-gradient(180deg, rgba(37,99,235,0.15), rgba(14,165,233,0.08)); text-align:center; }
.skill-section { background: rgba(255,255,255,0.05); padding:1rem; border-radius:12px; }
.pill { display:inline-block; padding:8px 12px; border-radius:999px; background:rgba(255,255,255,0.08); margin:5px; font-size:14px; }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# NLP model
# -----------------------------
if spacy:
    model_name = "en_core_web_md"
    try:
        nlp = spacy.load(model_name)
    except OSError:
        download(model_name)
        nlp = spacy.load(model_name)
else:
    nlp = None

# -----------------------------
# YouTube API
# -----------------------------
YOUTUBE_API_KEY = "YOUR_YOUTUBE_API_KEY"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# -----------------------------
# Session state
# -----------------------------
if "logged_in" not in st.session_state:
    st.session_state.update({
        "logged_in": False,
        "username": "",
        "password": "",
        "skills_analyzed": False,
        "missing_skills": [],
        "resume_skills": [],
        "job_skills": [],
        "resume_text": "",
        "job_text": "",
        "users": {},  # simple in-memory storage for demo
    })

# -----------------------------
# Lottie helper
# -----------------------------
def load_lottie_url(url):
    try:
        r = requests.get(url)
        if r.status_code==200:
            return r.json()
    except:
        return None
    return None

LOTTIE_UPLOAD = load_lottie_url("https://assets2.lottiefiles.com/packages/lf20_w51pcehl.json")
LOTTIE_SCORE = load_lottie_url("https://assets6.lottiefiles.com/packages/lf20_g8n0xqbm.json")

# -----------------------------
# Helper functions
# -----------------------------
def extract_text(uploaded_file):
    ext = uploaded_file.name.split(".")[-1].lower()
    if ext == "pdf":
        if PyPDF2:
            reader = PyPDF2.PdfReader(uploaded_file)
            return "\n".join([page.extract_text() or "" for page in reader.pages]) or "No text extracted."
        else:
            return "PDF parsing not available."
    elif ext in ["docx","doc"]:
        if docx2txt:
            return docx2txt.process(uploaded_file) or "No text extracted."
        else:
            return "DOCX parsing not available."
    elif ext == "txt":
        return uploaded_file.read().decode("utf-8") or "No text extracted."
    return "No text extracted."

def generate_summary(text):
    sentences = text.split(". ")[:3]
    return "... ".join(sentences) + "..." if sentences else "No content extracted."

def extract_skills(text):
    if nlp:
        doc = nlp(text)
        return [ent.text for ent in doc.ents if ent.label_=="ORG"]
    return []

def fetch_youtube_courses(skill):
    try:
        import googleapiclient.discovery
        youtube = googleapiclient.discovery.build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(q=f"{skill} course", part="snippet", maxResults=6, type="video")
        response = request.execute()
        return [{"Title": item["snippet"]["title"],
                 "Channel": item["snippet"]["channelTitle"],
                 "Video Link": f'https://www.youtube.com/watch?v={item["id"]["videoId"]}',
                 "Thumbnail": item["snippet"]["thumbnails"].get("medium",{}).get("url","")} for item in response.get("items",[])]
    except:
        return []

def plot_skill_distribution_pie(resume_skills, job_skills):
    resume_labels = resume_skills if resume_skills else ["No Skills Found"]
    job_labels = job_skills if job_skills else ["No Skills Found"]
    fig, axes = plt.subplots(1,2,figsize=(10,4))
    axes[0].pie([1]*len(resume_labels), labels=resume_labels, autopct='%1.1f%%')
    axes[0].set_title("Resume Skills")
    axes[1].pie([1]*len(job_labels), labels=job_labels, autopct='%1.1f%%')
    axes[1].set_title("Job Skills")
    st.pyplot(fig)

# -----------------------------
# Login / Signup page
# -----------------------------
def login_page():
    st.markdown("# 🔐 Login / Signup")
    menu = st.radio("Choose action:", ["Login","Create Account"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if menu=="Create Account":
        if st.button("Create Account"):
            if username in st.session_state.users:
                st.warning("User already exists!")
            else:
                st.session_state.users[username] = password
                st.success("Account created! Please login.")
    else:  # Login
        if st.button("Login"):
            if username in st.session_state.users and st.session_state.users[username]==password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"Welcome {username}!")
            else:
                st.error("Invalid credentials!")

# -----------------------------
# Main App Pages
# -----------------------------
if not st.session_state.logged_in:
    login_page()
else:
    page = st.sidebar.radio("📂 Navigate", ["📄 Upload Documents", "📝 Summaries", "🧠 Analysis", "📊 Insights & Courses"])
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.experimental_rerun()

    if page=="📄 Upload Documents":
        st.markdown("# 📂 Upload Documents")
        resume_file = st.file_uploader("📄 Upload Resume", type=["pdf","docx","txt"])
        job_file = st.file_uploader("💼 Upload Job Description", type=["pdf","docx","txt"])
        if resume_file: st.session_state.resume_text = extract_text(resume_file)
        if job_file: st.session_state.job_text = extract_text(job_file)
        if LOTTIE_UPLOAD: st_lottie(LOTTIE_UPLOAD, height=180)

    elif page=="📝 Summaries":
        st.header("📝 Summaries")
        if not st.session_state.resume_text or not st.session_state.job_text:
            st.warning("Upload both files first.")
        else:
            st.subheader("Resume Summary")
            st.info(generate_summary(st.session_state.resume_text))
            st.subheader("Job Description Summary")
            st.info(generate_summary(st.session_state.job_text))
            if st.button("Analyze Skills"):
                resume_skills = extract_skills(st.session_state.resume_text)
                job_skills = extract_skills(st.session_state.job_text)
                st.session_state.resume_skills = resume_skills
                st.session_state.job_skills = job_skills
                st.session_state.missing_skills = list(set(job_skills)-set(resume_skills))
                st.session_state.skills_analyzed = True
                st.success("Skills analysis done ✅")

    elif page=="🧠 Analysis":
        st.header("🧠 Resume Analysis")
        if not st.session_state.skills_analyzed:
            st.warning("Run analysis first.")
        else:
            st.subheader("Resume Skills")
            for s in st.session_state.resume_skills:
                st.markdown(f"<span class='pill'>{s}</span>", unsafe_allow_html=True)
            st.subheader("Job Description Skills")
            for s in st.session_state.job_skills:
                st.markdown(f"<span class='pill'>{s}</span>", unsafe_allow_html=True)
            st.subheader("Skill Comparison")
            plot_skill_distribution_pie(st.session_state.resume_skills, st.session_state.job_skills)

    elif page=="📊 Insights & Courses":
        st.header("📚 Missing Skills & Recommendations")
        if not st.session_state.skills_analyzed:
            st.warning("Run analysis first.")
        else:
            if st.session_state.missing_skills:
                st.write(", ".join(st.session_state.missing_skills))
                if st.button("Show Courses"):
                    all_courses = []
                    for skill in st.session_state.missing_skills:
                        all_courses.extend(fetch_youtube_courses(skill))
                    for video in all_courses:
                        colA,colB = st.columns([1,4])
                        with colA:
                            if video.get("Thumbnail"): st.image(video["Thumbnail"], width=160)
                        with colB:
                            st.markdown(f"**[{video['Title']}]({video['Video Link']})**")
                            st.markdown(f"Channel: {video['Channel']}")
                            vid_id = video['Video Link'].split('v=')[-1]
                            components.iframe(f"https://www.youtube.com/embed/{vid_id}", height=190)
            else:
                st.success("No missing skills!")
