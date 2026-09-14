import streamlit as st
import pandas as pd
import io

# पेज का लेआउट सेट करें (चौड़ा व्यू)
st.set_page_config(layout="wide", page_title="Student Scholarship Portal")

# =================================================================
# 0. PANEL COLUMNS (हर पैनल के लिए डेटा कॉलम)
# =================================================================
ADMISSION_COLUMNS = [
    "Admission No.", "Eligibility", "Unique ID", "Roll No.",
    "Application No.", "Enrollment No.", "Student Name", "Father Name",
    "Mother Name", "Date of Birth", "Category", "Subject",
    "Duration", "Mobile No.", "Email ID", "Address"
]

SCHOLARSHIP_ADMISSION_COLUMNS = [
    "Admission No.", "Unique ID", "Student Name", "Scholarship Name",
    "Scholarship Type", "Application No.", "Application Date",
    "Category", "Status"
]

SCHOLARSHIP_FEE_COLUMNS = [
    "Admission No.", "Unique ID", "Student Name", "Scholarship Amount",
    "Fee Paid", "Fee Due", "Payment Date", "Receipt No.", "Remarks"
]

# कौन सा पैनल किस DataFrame और किन कॉलम से जुड़ा है
DATA_PANELS = {
    "admission": {
        "state_key": "db_admission",
        "columns": ADMISSION_COLUMNS,
        "title": "🎓 Admission",
    },
    "scholarship_admission": {
        "state_key": "db_scholarship_admission",
        "columns": SCHOLARSHIP_ADMISSION_COLUMNS,
        "title": "📝 Scholarship Admission Data",
    },
    "scholarship_fee": {
        "state_key": "db_scholarship_fee",
        "columns": SCHOLARSHIP_FEE_COLUMNS,
        "title": "💰 Scholarship Fee Data",
    },
    "merge": {
        "state_key": "db_merge",
        "columns": None,
        "title": "🔗 Merge Data",
    },
}

# =================================================================
# 1. SESSION STATE INITIALIZATION
# =================================================================

# 1a. पैनल कॉन्फ़िग (नाम, विज़िबिलिटी, पासवर्ड) - Admin Panel से बदल सकते हैं
if "panels_config" not in st.session_state:
    st.session_state.panels_config = {
        "admission": {"label": "Admission", "visible": True, "password": ""},
        "scholarship_admission": {"label": "Scholarship Admission Data", "visible": True, "password": ""},
        "scholarship_fee": {"label": "Scholarship Fee Data", "visible": True, "password": ""},
        "merge": {"label": "Merge Data", "visible": True, "password": ""},
    }

# 1b. Admin Panel का अपना पासवर्ड
if "admin_password" not in st.session_state:
    st.session_state.admin_password = "admin123"

# 1c. इस सेशन में कौन-कौन से पैनल पहले से अनलॉक हैं
if "unlocked_panels" not in st.session_state:
    st.session_state.unlocked_panels = set()
if "admin_unlocked" not in st.session_state:
    st.session_state.admin_unlocked = False

# 1d. हर पैनल का डेटा (4 अलग DataFrame, हर एक बाद में एक ही Excel फ़ाइल में एक-एक Sheet बनेगा)
if "db_admission" not in st.session_state:
    st.session_state.db_admission = pd.DataFrame(columns=ADMISSION_COLUMNS)
if "db_scholarship_admission" not in st.session_state:
    st.session_state.db_scholarship_admission = pd.DataFrame(columns=SCHOLARSHIP_ADMISSION_COLUMNS)
if "db_scholarship_fee" not in st.session_state:
    st.session_state.db_scholarship_fee = pd.DataFrame(columns=SCHOLARSHIP_FEE_COLUMNS)
if "db_merge" not in st.session_state:
    st.session_state.db_merge = pd.DataFrame()


# =================================================================
# 2. HELPER FUNCTIONS
# =================================================================

def password_gate(panel_key: str) -> bool:
    """अगर पैनल पर पासवर्ड लगा है तो पहले उसे वेरिफाई करें। True = आगे दिखाओ।"""
    cfg = st.session_state.panels_config[panel_key]
    if not cfg["password"]:
        return True
    if panel_key in st.session_state.unlocked_panels:
        return True

    st.info("🔒 Yeh panel password se protected hai. Access karne ke liye password daalein.")
    pwd = st.text_input("Password", type="password", key=f"pwd_input_{panel_key}")
    if st.button("Unlock", key=f"unlock_btn_{panel_key}"):
        if pwd == cfg["password"]:
            st.session_state.unlocked_panels.add(panel_key)
            st.rerun()
        else:
            st.error("Galat password! Dobara try karein.")
    return False


def render_bulk_upload(panel_key: str, columns: list):
    """CSV se bulk data upload karne ka section."""
    st.subheader("📁 CSV Se Bulk Data Upload Karein")
    uploaded_file = st.file_uploader(
        "CSV फ़ाइल चुनें", type=["csv"], key=f"uploader_{panel_key}"
    )
    if uploaded_file is not None:
        try:
            uploaded_df = pd.read_csv(uploaded_file)
            if st.button("Upload CSV", type="primary", key=f"upload_btn_{panel_key}"):
                state_key = DATA_PANELS[panel_key]["state_key"]
                st.session_state[state_key] = pd.concat(
                    [st.session_state[state_key], uploaded_df], ignore_index=True
                )
                st.success("CSV डेटा सफलतापूर्वक जोड़ दिया गया है!")
        except Exception as e:
            st.error(f"फ़ाइल पढ़ने में त्रुटि: {e}")


def render_manual_entry(panel_key: str, columns: list):
    """Manually naya row add karne ka form (4 column grid)."""
    st.subheader("➕ Naya Data Add Karein")

    values = {}
    cols_widgets = st.columns(4)
    for i, col_name in enumerate(columns):
        with cols_widgets[i % 4]:
            values[col_name] = st.text_input(col_name, key=f"input_{panel_key}_{col_name}")

    if st.button("Save Data", use_container_width=True, key=f"save_btn_{panel_key}"):
        state_key = DATA_PANELS[panel_key]["state_key"]
        st.session_state[state_key] = pd.concat(
            [st.session_state[state_key], pd.DataFrame([values])], ignore_index=True
        )
        st.success("नया डेटा सुरक्षित कर लिया गया है!")
        st.rerun()


def render_table_and_actions(panel_key: str, df: pd.DataFrame, download_filename: str):
    """Live table + CSV download + Print button."""
    st.subheader("📊 Live Database")

    display_df = df.copy()
    display_df.index = display_df.index + 1
    display_df.index.name = "S. No."
    st.dataframe(display_df, use_container_width=True)

    st.subheader("📥 Actions")
    action_col1, action_col2 = st.columns(2)

    with action_col1:
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download as CSV",
            data=csv_data,
            file_name=download_filename,
            mime="text/csv",
            use_container_width=True,
            key=f"download_{panel_key}",
        )

    with action_col2:
        st.markdown(
            '<button onclick="window.print()" style="width:100%; height:38px; '
            'background-color:#ff4b4b; color:white; border:none; border-radius:4px; '
            'cursor:pointer;">Print Page / Save as PDF</button>',
            unsafe_allow_html=True,
        )


def render_data_panel(panel_key: str):
    """Ek complete data panel (upload + manual entry + table + actions)."""
    info = DATA_PANELS[panel_key]
    cfg = st.session_state.panels_config[panel_key]
    state_key = info["state_key"]
    columns = info["columns"]

    st.title(cfg["label"])

    render_bulk_upload(panel_key, columns)
    st.divider()
    render_manual_entry(panel_key, columns)
    st.divider()
    render_table_and_actions(
        panel_key, st.session_state[state_key], f"{panel_key}_database.csv"
    )


def render_merge_panel():
    """Admission, Scholarship Admission aur Scholarship Fee - teeno ka data ek sath jodna."""
    st.title(st.session_state.panels_config["merge"]["label"])

    st.subheader("⚙️ Merge Settings")
    key_column = st.selectbox(
        "Kis column ke aadhar par data merge karna hai?",
        ["Admission No.", "Unique ID"],
        key="merge_key_column",
    )

    if st.button("🔄 Generate / Refresh Merged Data", type="primary"):
        adm = st.session_state.db_admission.copy()
        sch_adm = st.session_state.db_scholarship_admission.copy()
        sch_fee = st.session_state.db_scholarship_fee.copy()

        # खाली key वाली rows merge से पहले हटा दें ताकि गलत जुड़ाव न हो
        adm = adm[adm[key_column].astype(str).str.strip() != ""] if key_column in adm.columns else adm
        sch_adm = sch_adm[sch_adm[key_column].astype(str).str.strip() != ""] if key_column in sch_adm.columns else sch_adm
        sch_fee = sch_fee[sch_fee[key_column].astype(str).str.strip() != ""] if key_column in sch_fee.columns else sch_fee

        merged = adm
        if key_column in sch_adm.columns:
            merged = pd.merge(
                merged, sch_adm, on=key_column, how="outer", suffixes=("", "_sch_adm")
            )
        if key_column in sch_fee.columns:
            merged = pd.merge(
                merged, sch_fee, on=key_column, how="outer", suffixes=("", "_sch_fee")
            )

        st.session_state.db_merge = merged
        st.success("Data merge ho gaya hai!")

    st.divider()
    render_table_and_actions("merge", st.session_state.db_merge, "merged_database.csv")


def build_full_excel_export() -> bytes:
    """4 panels ka data - ek hi Excel file me, har panel ek alag Sheet."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        st.session_state.db_admission.to_excel(writer, sheet_name="Admission", index=False)
        st.session_state.db_scholarship_admission.to_excel(
            writer, sheet_name="Scholarship Admission", index=False
        )
        st.session_state.db_scholarship_fee.to_excel(
            writer, sheet_name="Scholarship Fee", index=False
        )
        st.session_state.db_merge.to_excel(writer, sheet_name="Merge Data", index=False)
    return output.getvalue()


def render_admin_panel():
    """Admin panel: panels ko hide/unhide karna, naam badalna, password set karna."""
    st.title("⚙️ Admin Panel")

    if not st.session_state.admin_unlocked:
        st.info("🔒 Admin Panel access karne ke liye password daalein.")
        pwd = st.text_input("Admin Password", type="password", key="admin_pwd_input")
        if st.button("Login", type="primary", key="admin_login_btn"):
            if pwd == st.session_state.admin_password:
                st.session_state.admin_unlocked = True
                st.rerun()
            else:
                st.error("Galat admin password!")
        return

    st.success("Aap Admin Panel me login hain.")
    st.divider()

    st.subheader("🗂️ Panels Manage Karein (Naam / Show-Hide / Password)")

    for panel_key in ["admission", "scholarship_admission", "scholarship_fee", "merge"]:
        cfg = st.session_state.panels_config[panel_key]
        with st.expander(f"Panel: {cfg['label']}", expanded=False):
            new_label = st.text_input(
                "Panel ka naam", value=cfg["label"], key=f"admin_label_{panel_key}"
            )
            new_visible = st.checkbox(
                "Yeh panel menu me dikhe (Visible)",
                value=cfg["visible"],
                key=f"admin_visible_{panel_key}",
            )
            new_password = st.text_input(
                "Panel Password (khaali chhodein = koi password nahi)",
                value=cfg["password"],
                type="password",
                key=f"admin_password_{panel_key}",
            )

            if st.button("Save Changes", key=f"admin_save_{panel_key}"):
                st.session_state.panels_config[panel_key]["label"] = new_label
                st.session_state.panels_config[panel_key]["visible"] = new_visible
                st.session_state.panels_config[panel_key]["password"] = new_password
                # Agar password badla/hataya gaya hai to unlock status reset karein
                st.session_state.unlocked_panels.discard(panel_key)
                st.success(f"'{new_label}' panel update ho gaya!")
                st.rerun()

    st.divider()
    st.subheader("🔑 Admin Panel Ka Password Badlein")
    new_admin_pwd = st.text_input(
        "Naya Admin Password", type="password", key="new_admin_pwd"
    )
    if st.button("Update Admin Password", key="update_admin_pwd_btn"):
        if new_admin_pwd.strip():
            st.session_state.admin_password = new_admin_pwd
            st.success("Admin password update ho gaya!")
        else:
            st.warning("Password khaali nahi ho sakta.")

    st.divider()
    st.subheader("📦 Sabhi Panels Ka Data - Ek Excel File Me (Har Panel Ek Sheet)")
    excel_bytes = build_full_excel_export()
    st.download_button(
        label="Download Full Database (Excel - 4 Sheets)",
        data=excel_bytes,
        file_name="student_scholarship_full_database.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.divider()
    if st.button("🚪 Admin Panel Se Logout"):
        st.session_state.admin_unlocked = False
        st.rerun()


# =================================================================
# 3. SIDEBAR NAVIGATION
# =================================================================

st.sidebar.title("📚 Panel Menu")

label_to_key = {}
menu_options = []
for key in ["admission", "scholarship_admission", "scholarship_fee", "merge"]:
    cfg = st.session_state.panels_config[key]
    if cfg["visible"]:
        menu_options.append(cfg["label"])
        label_to_key[cfg["label"]] = key

menu_options.append("⚙️ Admin Panel")

choice = st.sidebar.radio("Panel Chunein", menu_options)

st.sidebar.divider()
st.sidebar.caption(
    "Hidden panels sirf Admin Panel se hi wapas visible kiye ja sakte hain."
)

# =================================================================
# 4. ROUTING - Jo panel select hua use render karein
# =================================================================

if choice == "⚙️ Admin Panel":
    render_admin_panel()
else:
    selected_key = label_to_key[choice]
    if password_gate(selected_key):
        if selected_key == "merge":
            render_merge_panel()
        else:
            render_data_panel(selected_key)
