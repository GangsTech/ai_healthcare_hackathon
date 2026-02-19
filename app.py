# ============================================================
# IMPORTS
# ============================================================
import streamlit as st
import pandas as pd
import os
from PIL import Image
from streamlit_drawable_canvas import st_canvas

from database import *
from ocr import extract_text
from ai_model import predict
from disease_detector import detect_disease
from pdf_generator import generate_pdf


# ============================================================
# PAGE CONFIG  (MUST BE FIRST STREAMLIT COMMAND)
# ============================================================
st.set_page_config(
    page_title="AI Healthcare Assistant",
    page_icon="🏥",
    layout="wide"
)

# ============================================================
# CUSTOM UI DESIGN
# ============================================================
st.markdown("""
<style>

.stApp {
    background: linear-gradient(135deg, #e3f2fd, #f8fafc);
}

.card {
    background: white;
    padding: 20px;
    border-radius: 15px;
    box-shadow: 0px 4px 20px rgba(0,0,0,0.08);
    margin-bottom: 20px;
}

.stButton>button {
    background-color: #1976D2;
    color: white;
    border-radius: 10px;
    padding: 8px 16px;
    border: none;
    font-weight: 600;
}

.stButton>button:hover {
    background-color: #125aa0;
}

section[data-testid="stSidebar"] {
    background-color: #0f172a;
}

h1,h2,h3 {
    color:#0f172a;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# TITLE
# ============================================================
st.markdown("""
<h1 style='text-align:center;font-size:40px;'>🏥 AI Healthcare Digitization System</h1>
<p style='text-align:center;color:gray;'>Smart Clinical Reports • Digital Records • AI Assisted Diagnosis</p>
""", unsafe_allow_html=True)


# ============================================================
# INIT
# ============================================================
create_tables()
create_default_management()

if not os.path.exists("signatures"):
    os.makedirs("signatures")


# ============================================================
# SESSION
# ============================================================
if "role" not in st.session_state:
    st.session_state.role = None

if "username" not in st.session_state:
    st.session_state.username = None


# ============================================================
# SIDEBAR
# ============================================================
if st.session_state.role == "management":
    menu = ["Create Doctor", "Create Patient", "System Monitor", "Logout"]
else:
    menu = ["Doctor Login", "Patient Login", "Management Login"]

choice = st.sidebar.selectbox("Menu", menu)


# ============================================================
# LOGIN
# ============================================================
if choice == "Management Login":
    st.subheader("Management Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if login_management(u,p):
            st.session_state.role="management"
            st.session_state.username=u
            st.rerun()
        else:
            st.error("Invalid credentials")


elif choice == "Doctor Login":
    st.subheader("Doctor Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if login_doctor(u,p):
            st.session_state.role="doctor"
            st.session_state.username=u
            st.rerun()
        else:
            st.error("Invalid credentials")


elif choice == "Patient Login":
    st.subheader("Patient Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if login_patient(u,p):
            st.session_state.role="patient"
            st.session_state.username=u
            st.rerun()
        else:
            st.error("Invalid credentials")


elif choice == "Logout":
    st.session_state.role=None
    st.session_state.username=None
    st.rerun()


# ============================================================
# MANAGEMENT DASHBOARD
# ============================================================
if st.session_state.role=="management":

    st.header("System Overview")
    d,p,r = get_total_counts()
    st.metric("Doctors",d)
    st.metric("Patients",p)
    st.metric("Reports",r)

    st.subheader("Create Doctor")
    du = st.text_input("Doctor Username")
    dp = st.text_input("Doctor Password", type="password")
    if st.button("Create Doctor"):
        add_doctor(du,dp)
        st.success("Doctor Created")

    st.subheader("Create Patient")
    pu = st.text_input("Patient Username")
    pp = st.text_input("Patient Password", type="password")
    if st.button("Create Patient"):
        add_patient(pu,pp)
        st.success("Patient Created")

    st.subheader("Doctor → Patient → Reports")
    rows = get_doctor_patient_reports()
    if rows:
        df = pd.DataFrame(rows,columns=[
            "Doctor","Patient","Name","Age","Disease","Risk","Date"
        ])
        st.dataframe(df)


# ============================================================
# DOCTOR DASHBOARD
# ============================================================
elif st.session_state.role=="doctor":

    st.success(f"Doctor: {st.session_state.username}")

    st.subheader("My Patients")
    patients = get_doctor_patients(st.session_state.username)

    if patients:
        plist=[p[0] for p in patients]
        selected = st.selectbox("Select Patient",plist)

        reports = get_patient_reports(selected)
        if reports:
            df=pd.DataFrame(reports,columns=[
                "Name",
                "Age",
                "Weight",
                "Height",
                "Disease",
                "BP",
                "Sugar",
                "Risk",
                "Prescription",
                "Signature",
                "Patient Photo",
                "Prescription Image",
                "Date"
                ])

            st.dataframe(df)

    st.subheader("Create New Report")

    patient_username = st.text_input("Patient Username")
    patient_name = st.text_input("Patient Name")
    age = st.number_input("Age",0,120)
    weight = st.number_input("Weight")
    height = st.number_input("Height")
    bp = st.number_input("Blood Pressure")
    sugar = st.number_input("Blood Sugar")
    prescription = st.text_area("Prescription")
    patient_photo = st.camera_input("Capture Patient Photo")

    image = st.file_uploader("Upload Prescription Image")

    st.subheader("Doctor Signature")
    canvas = st_canvas(
        stroke_width=3,
        stroke_color="black",
        background_color="white",
        height=150,
        width=400,
        drawing_mode="freedraw"
    )

    if st.button("Generate Report"):

        signature_path=None
        if canvas.image_data is not None:
            signature_path=f"signatures/{st.session_state.username}.png"
            Image.fromarray(canvas.image_data.astype("uint8")).save(signature_path)

        text=""
        if image:
            with open("temp.jpg","wb") as f:
                f.write(image.getbuffer())
            text=extract_text("temp.jpg")

        disease=detect_disease(text)

        label="Low Risk"
        if disease in ["Heart Disease","Kidney Disease"]:
            label="High Risk"
        elif bp>0 and sugar>0:
            r,_=predict(age,bp,sugar)
            label="High Risk" if r==1 else "Low Risk"

        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S")

        photo_path = None
        if patient_photo is not None:
            os.makedirs("patient_photos", exist_ok=True)
            photo_path = f"patient_photos/{patient_username}_{timestamp}.png"
            with open(photo_path, "wb") as f:
                f.write(patient_photo.getbuffer())

        prescription_image_path = None
        if image:
            os.makedirs("prescriptions", exist_ok=True)
            prescription_image_path = f"prescriptions/{patient_username}_{timestamp}.png"
            with open(prescription_image_path, "wb") as f:
                f.write(image.getbuffer())

        save_report((
            patient_username,
            st.session_state.username,
            patient_name,
            age,
            weight,
            height,
            disease,
            bp,
            sugar,
            label,
            prescription,
            signature_path,
            prescription_image_path,
            photo_path,
            timestamp
        ))

        pdf = generate_pdf({
            "patient_name":patient_name,
            "age":age,
            "weight":weight,
            "height":height,
            "bp":bp,
            "sugar":sugar,
            "disease":disease,
            "doctor":st.session_state.username,
            "date":timestamp,
            "signature":signature_path,
            "patient_photo": photo_path
        },patient_username)

        st.success("Report Generated")

        with open(pdf,"rb") as f:
            st.download_button("Download PDF",f)


# ============================================================
# PATIENT DASHBOARD
# ============================================================
elif st.session_state.role=="patient":

    st.success(f"Patient: {st.session_state.username}")

    rows = get_patient_reports(st.session_state.username)

    if rows:
        df = pd.DataFrame(rows, columns=[
            "Name",
            "Age",
            "Weight",
            "Height",
            "Disease",
            "BP",
            "Sugar",
            "Risk",
            "Prescription",
            "Signature",
            "Patient Photo",
            "Prescription Image",   # ✅ MISSING COLUMN ADDED
            "Date"
        ])

        st.dataframe(df)

        visit = st.selectbox(
            "Select Visit",
            [f"Visit {i+1} - {r[12]}" for i, r in enumerate(rows)]
        )

        idx = [f"Visit {i+1} - {r[12]}" for i, r in enumerate(rows)].index(visit)
        selected = rows[idx]

        # prescription Photo
        st.subheader("Prescription Photo")
        if selected[10]:
            st.image(selected[10], width=200)

        # patient Image
        st.subheader("Patient Image")
        if selected[11]:
            st.image(selected[11], width=200)

        # Doctor Signature
        st.subheader("Doctor Signature")
        if selected[9]:
            st.image(selected[9], width=200)

        if st.button("Download Selected Report PDF"):
            pdf = generate_pdf({
                "patient_name": selected[0],
                "age": selected[1],
                "weight": selected[2],
                "height": selected[3],
                "bp": selected[5],
                "sugar": selected[6],
                "disease": selected[4],
                "doctor": "Assigned Doctor",
                "date": selected[12],
                "signature": selected[9],
                "patient_photo": selected[10]
            }, st.session_state.username)

            with open(pdf, "rb") as f:
                st.download_button("Download PDF", f)

    else:
        st.info("No reports found")
