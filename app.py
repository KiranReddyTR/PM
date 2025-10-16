import streamlit as st
import requests
import re
import PyPDF2
import docx2txt
import googleapiclient.discovery
import streamlit.components.v1 as components
from streamlit_lottie import st_lottie
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------
# 🔹 BASIC PAGE CONFIG & STYLE
# ---------------------------
st.set_page_config(page_title="ProFileMatch — AI Resume Analyzer", layout="wide")

st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #0a1121 0%, #0e1b35 100%);
    color: #e8ecf2;
}
.title {
    font-size: 60px;
    font-weight: 700;
    text-align: center;
    background: linear-gradient(90deg, silver, black);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 1rem;
}
.button-grand > button {
    background: linear-gradient(90deg, #6366f1, #0ea5e9);
    color: white !important;
    border: none;
    border-radius: 12px;
    font-size: 18px;
    padding: 0.75rem 1.5rem;
    box-shadow: 0 6px 20px rgba(14,165,233,0.4);
}
.metric-box {
    background: linear-gradient(180deg, rgba(37,99,235,0.15), rgba(14,165,233,0.08));
    padding: 1.5rem;
    border-radius: 16px;
    text-align: center;
    margin-top: 1.5rem;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# 🔹 LOTTIE LOADER
# ---------------------------
def load_lottie_url(url):
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()
    except:
        return None
    return None

LOTTIE_LOGIN = load_lottie_url("https://assets2.lottiefiles.com/packages/lf20_w51pcehl.json")
LOTTIE_UPLOAD = load_lottie_url("https://assets8.lottiefiles.com/packages/lf20_jcikwtux.json")
LOTTIE_ANALYZE = load_lottie_url("https://assets6.lottiefiles.com/packages/lf20_g8n0xqbm.json")

# ---------------------------
# 🔹 MODEL FUNCTIONS
# ---------------------------

def extract_text(file):
    """Extract text from PDF, DOCX, or TXT"""
    if file.name.endswith('.pdf'):
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page in reader.pages:
            text += page.extract_text() or ''
        return text
    elif file.name.endswith('.docx'):
        return docx2txt.process(file)
    elif file.name.endswith('.txt'):
        return file.read().decode("utf-8")
    else:
        return ""

def extract_skills(text):
    """Extract potential skills from text using keywords"""
    common_skills = [
        'python', 'excel', 'sql', 'power bi', 'tableau', 'communication',
        'leadership', 'analysis', 'machine learning', 'data visualization',
        'java', 'c++', 'data analytics', 'teamwork', 'critical thinking'
    ]
    text = text.lower()
    found = [skill for skill in common_skills if skill in text]
    return list(set(found))

def analyze_resume_vs_job(resume_text, job_text):
    """Compare resume and job text for similarity & skill gap"""
    vectorizer = CountVectorizer().fit_transform([resume_text, job_text])
    similarity = cosine_similarity(vectorizer)[0][1]
    match_score = round(similarity * 100, 2)

    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(job_text)
    missing_skills = [s for s in job_skills if s not in resume_skills]

    return {
        "match_score": match_score,
        "resume_skills": resume_skills,
        "job_skills": job_skills,
        "missing_skills": missing_skills
    }

def fetch_youtube_courses(skill):
    """Fetch top YouTube videos for the given skill"""
    api_key = "YOUR_YOUTUBE_API_KEY"  # Replace with your key
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
    request = youtube.search().list(part="snippet", maxResults=2, q=f"{skill} tutorial", type="video")
    response = request.execute()

    videos = []
    for item in response.get("items", []):
        videos.append({
            "Title": item["snippet"]["title"],
            "Channel": item["snippet"]["channelTitle"],
            "Thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
            "Video Link": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
        })
    return videos

# ---------------------------
# 🔹 LOGIN SYSTEM
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 class='title'>ProFileMatch</h1>", unsafe_allow_html=True)
    st_lottie(LOTTIE_LOGIN, height=180)

    with st.form("login_form"):
        st.subheader("🔐 Login or Create Account")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("Login")

        if login_button:
            if username and password:
                st.session_state.logged_in = True
                st.success(f"Welcome, {username}! 🎉")
                st.experimental_rerun()
            else:
                st.error("Please enter both username and password.")

# ---------------------------
# 🔹 MAIN APP
# ---------------------------
else:
    page = st.sidebar.radio("📂 Navigate", ["📄 Upload Resume", "🧠 Analysis", "📚 Courses"])
    st.sidebar.markdown("---")
    if st.sidebar.button("🔒 Logout"):
        st.session_state.logged_in = False
        st.experimental_rerun()

    if page == "📄 Upload Resume":
        st.markdown("<h1 class='title'>📄 Upload Your Documents</h1>", unsafe_allow_html=True)
        st_lottie(LOTTIE_UPLOAD, height=180)
        col1, col2 = st.columns(2)

        with col1:
            resume_file = st.file_uploader("📄 Upload Resume", type=["pdf", "docx", "txt"])
        with col2:
            job_file = st.file_uploader("💼 Upload Job Description", type=["pdf", "docx", "txt"])

        if resume_file and job_file:
            st.session_state.resume_text = extract_text(resume_file)
            st.session_state.job_text = extract_text(job_file)
            st.success("✅ Files uploaded successfully!")

    elif page == "🧠 Analysis":
        st.markdown("<h1 class='title'>🧠 Resume Analysis Dashboard</h1>", unsafe_allow_html=True)

        if "resume_text" not in st.session_state or "job_text" not in st.session_state:
            st.warning("⚠️ Please upload your files first.")
        else:
            if st.button("🔍 Analyze Resume"):
                results = analyze_resume_vs_job(st.session_state.resume_text, st.session_state.job_text)
                st.session_state.analysis_results = results
                st.success("✅ Analysis complete!")

            if "analysis_results" in st.session_state:
                results = st.session_state.analysis_results
                st_lottie(LOTTIE_ANALYZE, height=150)
                st.markdown(
                    f"<div class='metric-box'><h1 style='font-size:60px'>{results['match_score']}%</h1><p>Overall Similarity</p></div>",
                    unsafe_allow_html=True,
                )
                st.subheader("🧾 Resume Skills")
                st.write(", ".join(results["resume_skills"]) or "None found")
                st.subheader("💼 Job Description Skills")
                st.write(", ".join(results["job_skills"]) or "None found")
                st.subheader("⚙️ Missing Skills")
                if results["missing_skills"]:
                    st.write(", ".join(results["missing_skills"]))
                else:
                    st.success("🎯 Great! No missing skills detected.")

    elif page == "📚 Courses":
        st.markdown("<h1 class='title'>📚 Recommended YouTube Courses</h1>", unsafe_allow_html=True)
        if "analysis_results" not in st.session_state:
            st.warning("Please run the analysis first.")
        else:
            missing_skills = st.session_state.analysis_results["missing_skills"]
            if not missing_skills:
                st.success("🎉 You're all caught up!")
            else:
                for skill in missing_skills:
                    st.markdown(f"### 🔹 {skill}")
                    courses = fetch_youtube_courses(skill)
                    if courses:
                        for c in courses:
                            colA, colB = st.columns([1, 4])
                            with colA:
                                st.image(c["Thumbnail"], width=160)
                            with colB:
                                st.markdown(f"**[{c['Title']}]({c['Video Link']})**")
                                st.markdown(f"Channel: {c['Channel']}")
                                vid_id = c["Video Link"].split("v=")[-1]
                                components.iframe(f"https://www.youtube.com/embed/{vid_id}", height=190)
