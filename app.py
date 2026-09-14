import streamlit as st
import pandas as pd
import os
import json
import io
import re
import hashlib

# ==========================================================
# ⚙️ स्टेप 1: पेज का लेआउट सेट करें
# ==========================================================
st.set_page_config(layout="wide", page_title="Student Scholarship Portal")

# ==========================================================
# 📁 स्टेप 2: परमानेंट स्टोरेज फ़ाइलों के नाम/पाथ
#     (डेटा अब session_state की जगह डिस्क पर CSV/JSON फ़ाइलों में
#     सेव होगा, इसलिए ऐप रीस्टार्ट होने पर भी डेटा नहीं उड़ेगा)
# ==========================================================
ADMISSION_FILE = "admission_database.csv"
SCH_ADM_FILE = "scholarship_admission_database.csv"
SCH_FEE_FILE = "scholarship_fee_database.csv"
MERGE_FILE = "merge_database.csv"
CRED_FILE = "user_credentials.json"
PANEL_CONFIG_FILE = "panel_config.json"

# ==========================================================
# 0. हर पैनल के कॉलम (पहला कॉलम = उस पैनल की "Primary Key"।
#    Manual Entry में यह भरना ज़रूरी है, वरना खाली row सेव नहीं होगी)
# ==========================================================
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

PANEL_FILE_MAP = {
    "admission": ADMISSION_FILE,
    "scholarship_admission": SCH_ADM_FILE,
    "scholarship_fee": SCH_FEE_FILE,
    "merge": MERGE_FILE,
}

PANEL_COLUMNS_MAP = {
    "admission": ADMISSION_COLUMNS,
    "scholarship_admission": SCHOLARSHIP_ADMISSION_COLUMNS,
    "scholarship_fee": SCHOLARSHIP_FEE_COLUMNS,
    "merge": None,  # merge ka data dynamically banta hai
}

PANEL_ICONS = {
    "admission": "🎓",
    "scholarship_admission": "📝",
    "scholarship_fee": "💰",
    "merge": "🔀",
}

# ==========================================================
# डिफ़ॉल्ट Credentials (हर पैनल का अपना यूज़र + एक Super Admin)
# NOTE: यहाँ जो पासवर्ड लिखे हैं वो सिर्फ पहली बार डिफ़ॉल्ट सेट-अप के लिए हैं।
# फ़ाइल में सेव होने से पहले इन्हें hash कर दिया जाता है (नीचे load_credentials देखें)।
# ==========================================================
DEFAULT_CREDENTIALS_PLAIN = {
    "admin": {
        "password": "admin123", "role": "admin",
        "label": "👑 Super Admin (Sabhi Panels)"
    },
    "user_admission": {
        "password": "adm123", "role": "admission",
        "label": "🎓 Admission Panel User"
    },
    "user_sch_admission": {
        "password": "scha123", "role": "scholarship_admission",
        "label": "📝 Scholarship Admission Data User"
    },
    "user_sch_fee": {
        "password": "schf123", "role": "scholarship_fee",
        "label": "💰 Scholarship Fee Data User"
    },
    "user_merge": {
        "password": "mrg123", "role": "merge",
        "label": "🔀 Merge Data User"
    },
}

DEFAULT_PANEL_CONFIG = {
    "admission": {"label": "Admission", "visible": True},
    "scholarship_admission": {"label": "Scholarship Admission Data", "visible": True},
    "scholarship_fee": {"label": "Scholarship Fee Data", "visible": True},
    "merge": {"label": "Merge Data", "visible": True},
}


# ==========================================================
# 🔒 पासवर्ड को हमेशा hash करके ही डिस्क पर रखा जाता है
#    (plain text password file me kabhi save nahi hota)
# ==========================================================
def hash_password(plain_text: str) -> str:
    return hashlib.sha256(plain_text.encode("utf-8")).hexdigest()


def build_default_credentials_hashed():
    hashed = {}
    for username, info in DEFAULT_CREDENTIALS_PLAIN.items():
        hashed[username] = {
            "password": hash_password(info["password"]),
            "role": info["role"],
            "label": info["label"],
        }
    return hashed


# ==========================================================
# 📁 स्टेप 3: डेटा सहेजने / लोड करने वाले कोर फंक्शन्स (JSON)
# ==========================================================

def load_credentials():
    if os.path.exists(CRED_FILE):
        try:
            with open(CRED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data:
                    return data
        except Exception:
            pass
    hashed_defaults = build_default_credentials_hashed()
    with open(CRED_FILE, "w", encoding="utf-8") as f:
        json.dump(hashed_defaults, f, ensure_ascii=False, indent=4)
    return hashed_defaults


def save_credentials(cred_dict):
    with open(CRED_FILE, "w", encoding="utf-8") as f:
        json.dump(cred_dict, f, ensure_ascii=False, indent=4)


def load_panel_config():
    if os.path.exists(PANEL_CONFIG_FILE):
        try:
            with open(PANEL_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data:
                    return data
        except Exception:
            pass
    with open(PANEL_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_PANEL_CONFIG, f, ensure_ascii=False, indent=4)
    return DEFAULT_PANEL_CONFIG.copy()


def save_panel_config(cfg_dict):
    with open(PANEL_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg_dict, f, ensure_ascii=False, indent=4)


# ==========================================================
# 📁 स्टेप 4: डेटा सहेजने / लोड करने वाले कोर फंक्शन्स (CSV)
# ==========================================================

def load_panel_data(panel_key):
    file_path = PANEL_FILE_MAP[panel_key]
    columns = PANEL_COLUMNS_MAP[panel_key]
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        df = pd.DataFrame(columns=columns if columns else [])
        df.to_csv(file_path, index=False)
        return df
    try:
        df = pd.read_csv(file_path, dtype=str).fillna("")
        if columns:
            for col in columns:
                if col not in df.columns:
                    df[col] = ""
        return df.reset_index(drop=True)
    except Exception:
        return pd.DataFrame(columns=columns if columns else [])


def save_panel_data(panel_key, df):
    file_path = PANEL_FILE_MAP[panel_key]
    df.fillna("").astype(str).to_csv(file_path, index=False)


def sanitize_sheet_name(name: str, used_names: set) -> str:
    """Excel sheet ke naam me kuch special characters allowed nahi hote (\\ / ? * [ ] :)
    aur naam 31 characters se lamba bhi nahi ho sakta. Yahan naam ko safe banaya jaata hai
    aur agar do panels ka naam ek jaisa ho jaaye to uske aage number laga dete hain,
    taaki Excel file banate waqt koi error na aaye."""
    clean = re.sub(r'[\\/\?\*\[\]:]', "-", str(name)).strip()
    if not clean:
        clean = "Sheet"
    clean = clean[:31]
    final_name = clean
    counter = 2
    while final_name in used_names:
        suffix = f" ({counter})"
        final_name = clean[: 31 - len(suffix)] + suffix
        counter += 1
    used_names.add(final_name)
    return final_name


def build_full_excel_export(panel_config):
    """4 panels ka permanent data - ek hi Excel file me, har panel ek alag Sheet."""
    output = io.BytesIO()
    used_names = set()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for key in ["admission", "scholarship_admission", "scholarship_fee", "merge"]:
            df = load_panel_data(key)
            raw_label = panel_config.get(key, {}).get("label") or key
            sheet_name = sanitize_sheet_name(raw_label, used_names)
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()


# ==========================================================
# 🧠 स्टेप 5: सेशन स्टेट इनिशियलाइज़ेशन
# ==========================================================
if "credentials" not in st.session_state:
    st.session_state.credentials = load_credentials()
if "panel_config" not in st.session_state:
    st.session_state.panel_config = load_panel_config()
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "current_role" not in st.session_state:
    st.session_state.current_role = None
if "current_label" not in st.session_state:
    st.session_state.current_label = None
# 🆕 हर पैनल के फॉर्म/फ़ाइल-अपलोडर को सेव करने के बाद खाली (reset) करने के लिए काउंटर
if "form_key_counter" not in st.session_state:
    st.session_state.form_key_counter = {
        "admission": 0, "scholarship_admission": 0, "scholarship_fee": 0
    }
if "uploader_key_counter" not in st.session_state:
    st.session_state.uploader_key_counter = {
        "admission": 0, "scholarship_admission": 0, "scholarship_fee": 0
    }


# ==========================================================
# 🔐 स्टेप 6: लॉगिन पेज
# ==========================================================

def render_login():
    st.title("🔐 Student Scholarship Portal - Login")
    st.caption("Apna username aur password daal kar login karein.")

    col1, col2 = st.columns([1, 2])
    with col1:
        username = st.text_input("Username").strip()
        password = st.text_input("Password", type="password")
        if st.button("Login", type="primary", use_container_width=True):
            creds = st.session_state.credentials
            if not username or not password:
                st.error("Username aur Password dono bharna zaroori hai!")
            elif username in creds and creds[username]["password"] == hash_password(password):
                st.session_state.logged_in = True
                st.session_state.current_user = username
                st.session_state.current_role = creds[username]["role"]
                st.session_state.current_label = creds[username]["label"]
                st.rerun()
            else:
                st.error("Galat username ya password!")


# ==========================================================
# 🧩 स्टेप 7: डेटा पैनल के लिए Reusable Helper Functions
# ==========================================================

def render_bulk_upload(panel_key, current_df):
    st.subheader("📁 CSV Se Bulk Data Upload Karein")
    uploader_key = f"uploader_{panel_key}_{st.session_state.uploader_key_counter[panel_key]}"
    uploaded_file = st.file_uploader(
        "CSV फ़ाइल चुनें", type=["csv"], key=uploader_key
    )
    if uploaded_file is not None:
        try:
            uploaded_df = pd.read_csv(uploaded_file, dtype=str).fillna("")
            if st.button("Upload CSV", type="primary", key=f"upload_btn_{panel_key}"):
                new_df = pd.concat([current_df, uploaded_df], ignore_index=True)
                save_panel_data(panel_key, new_df)
                # 🆕 Uploader ko khaali karne ke liye uska key badal dete hain
                st.session_state.uploader_key_counter[panel_key] += 1
                st.success("CSV डेटा सफलतापूर्वक जोड़ दिया गया है (permanently save ho gaya)!")
                st.rerun()
        except Exception as e:
            st.error(f"फ़ाइल पढ़ने में त्रुटि: {e}")


def render_manual_entry(panel_key, columns):
    st.subheader("➕ Naya Data Add Karein")
    counter = st.session_state.form_key_counter[panel_key]
    primary_key_col = columns[0]

    values = {}
    cols_widgets = st.columns(4)
    for i, col_name in enumerate(columns):
        with cols_widgets[i % 4]:
            label = col_name + " *" if col_name == primary_key_col else col_name
            values[col_name] = st.text_input(
                label, key=f"input_{panel_key}_{counter}_{col_name}"
            ).strip()

    st.caption(f"* {primary_key_col} bharna zaroori hai.")

    if st.button("Save Data", use_container_width=True, key=f"save_btn_{panel_key}_{counter}"):
        if not values[primary_key_col]:
            st.error(f"'{primary_key_col}' khaali nahi ho sakta — pehle yeh bharein.")
        else:
            current_df = load_panel_data(panel_key)
            new_df = pd.concat([current_df, pd.DataFrame([values])], ignore_index=True)
            save_panel_data(panel_key, new_df)
            # 🆕 Form ke fields ko khaali karne ke liye counter badal dete hain
            st.session_state.form_key_counter[panel_key] += 1
            st.success("नया डेटा permanently सुरक्षित कर लिया गया है!")
            st.rerun()


def render_table_and_actions(panel_key, df, download_filename):
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


def render_data_panel(panel_key):
    cfg = st.session_state.panel_config[panel_key]
    columns = PANEL_COLUMNS_MAP[panel_key]

    st.title(f"{PANEL_ICONS[panel_key]} {cfg['label']}")

    df = load_panel_data(panel_key)

    render_bulk_upload(panel_key, df)
    st.divider()
    render_manual_entry(panel_key, columns)
    st.divider()
    render_table_and_actions(panel_key, load_panel_data(panel_key), f"{panel_key}_database.csv")


def render_merge_panel():
    cfg = st.session_state.panel_config["merge"]
    st.title(f"{PANEL_ICONS['merge']} {cfg['label']}")

    st.subheader("⚙️ Merge Settings")
    key_column = st.selectbox(
        "Kis column ke aadhar par data merge karna hai?",
        ["Admission No.", "Unique ID"],
        key="merge_key_column",
    )

    if st.button("🔄 Generate / Refresh Merged Data", type="primary"):
        adm = load_panel_data("admission")
        sch_adm = load_panel_data("scholarship_admission")
        sch_fee = load_panel_data("scholarship_fee")

        # खाली key वाली rows merge से पहले हटा दें ताकि गलत जुड़ाव न हो
        if key_column in adm.columns:
            adm = adm[adm[key_column].astype(str).str.strip() != ""]
        if key_column in sch_adm.columns:
            sch_adm = sch_adm[sch_adm[key_column].astype(str).str.strip() != ""]
        if key_column in sch_fee.columns:
            sch_fee = sch_fee[sch_fee[key_column].astype(str).str.strip() != ""]

        merged = adm.copy()

        # 🆕 FIX: pehle jo columns (Student Name, Unique ID, Category waghera) merged me
        # pehle se maujood hain, unhe dusri baar merge nahi karte — sirf naye/extra columns
        # hi jode jaate hain. Isse messy "_sch_adm" / "_sch_fee" wale duplicate columns
        # nahi banenge aur merged table saaf rahegi.
        for extra_df in [sch_adm, sch_fee]:
            if key_column not in extra_df.columns:
                continue
            new_cols = [key_column] + [c for c in extra_df.columns if c not in merged.columns]
            merged = pd.merge(merged, extra_df[new_cols], on=key_column, how="outer")

        save_panel_data("merge", merged)
        st.success("Data merge ho gaya hai aur permanently save ho gaya!")
        st.rerun()

    st.divider()
    render_table_and_actions("merge", load_panel_data("merge"), "merged_database.csv")


# ==========================================================
# ⚙️ स्टेप 8: Admin Panel
# ==========================================================

def render_admin_panel():
    st.title("⚙️ Admin Panel")
    st.success(f"Aap Admin Panel me login hain: {st.session_state.current_label}")
    st.divider()

    # ---------- 8a. Panels ka naam / show-hide manage karna ----------
    st.subheader("🗂️ Panels Manage Karein (Naam / Show-Hide)")
    panel_config = st.session_state.panel_config

    for panel_key in ["admission", "scholarship_admission", "scholarship_fee", "merge"]:
        cfg = panel_config[panel_key]
        with st.expander(f"{PANEL_ICONS[panel_key]} Panel: {cfg['label']}", expanded=False):
            new_label = st.text_input(
                "Panel ka naam", value=cfg["label"], key=f"admin_label_{panel_key}"
            )
            new_visible = st.checkbox(
                "Yeh panel menu me dikhe (Visible)",
                value=cfg["visible"], key=f"admin_visible_{panel_key}",
            )
            if st.button("Save Panel Changes", key=f"admin_save_panel_{panel_key}"):
                if not new_label.strip():
                    st.error("Panel ka naam khaali nahi ho sakta.")
                else:
                    panel_config[panel_key]["label"] = new_label.strip()
                    panel_config[panel_key]["visible"] = new_visible
                    save_panel_config(panel_config)
                    st.session_state.panel_config = panel_config
                    st.success(f"'{new_label}' panel update ho gaya!")
                    st.rerun()

    st.divider()

    # ---------- 8b. Har panel ke user ka naam / password update karna ----------
    st.subheader("🔑 Panel Users - Naam / Password Update Karein")
    creds = st.session_state.credentials

    role_to_panel_key = {
        "admin": None,
        "admission": "admission",
        "scholarship_admission": "scholarship_admission",
        "scholarship_fee": "scholarship_fee",
        "merge": "merge",
    }

    for username, info in creds.items():
        panel_key = role_to_panel_key.get(info["role"])
        display_title = f"👑 {username} (Super Admin)" if info["role"] == "admin" else f"{PANEL_ICONS.get(panel_key,'')} {username}"
        with st.expander(display_title, expanded=False):
            new_label = st.text_input(
                "Display Naam", value=info["label"], key=f"cred_label_{username}"
            )
            new_password = st.text_input(
                "Naya Password (khaali chhodein = password wahi rahega)",
                value="", type="password", key=f"cred_password_{username}",
            )
            if st.button("Update User", key=f"cred_save_{username}"):
                if not new_label.strip():
                    st.error("Display naam khaali nahi ho sakta.")
                else:
                    creds[username]["label"] = new_label.strip()
                    if new_password.strip():
                        creds[username]["password"] = hash_password(new_password.strip())
                    save_credentials(creds)
                    st.session_state.credentials = creds
                    # Agar khud apna hi naam/password badla hai, to current session bhi update karein
                    if username == st.session_state.current_user:
                        st.session_state.current_label = creds[username]["label"]
                    st.success(f"'{username}' ka data update ho gaya!")
                    st.rerun()

    st.divider()

    # ---------- 8c. Poora data ek Excel file me download ----------
    st.subheader("📦 Sabhi Panels Ka Data - Ek Excel File Me (Har Panel Ek Sheet)")
    excel_bytes = build_full_excel_export(panel_config)
    st.download_button(
        label="Download Full Database (Excel - 4 Sheets)",
        data=excel_bytes,
        file_name="student_scholarship_full_database.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


# ==========================================================
# 🚦 स्टेप 9: मुख्य रूटिंग - Login check + Sidebar navigation
# ==========================================================

if not st.session_state.logged_in:
    render_login()
    st.stop()

st.sidebar.title("📚 Panel Menu")
st.sidebar.success(f"👤 {st.session_state.current_label}")
if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.session_state.current_role = None
    st.session_state.current_label = None
    st.rerun()

st.sidebar.divider()

role = st.session_state.current_role
panel_config = st.session_state.panel_config

menu_options = []
label_to_key = {}
for key in ["admission", "scholarship_admission", "scholarship_fee", "merge"]:
    cfg = panel_config[key]
    if not cfg["visible"]:
        continue
    if role != "admin" and role != key:
        continue
    display = f"{PANEL_ICONS[key]} {cfg['label']}"
    menu_options.append(display)
    label_to_key[display] = key

if role == "admin":
    menu_options.append("⚙️ Admin Panel")

if not menu_options:
    st.warning("Aapke liye abhi koi panel available nahi hai. Admin se sampark karein.")
    st.stop()

choice = st.sidebar.radio("Panel Chunein", menu_options)
st.sidebar.divider()
st.sidebar.caption("Data ab permanently CSV/JSON files me save hota hai.")

# ==========================================================
# 🧭 स्टेप 10: चुने गए पैनल को रेंडर करना
# ==========================================================

if choice == "⚙️ Admin Panel":
    render_admin_panel()
else:
    selected_key = label_to_key[choice]
    if selected_key == "merge":
        render_merge_panel()
    else:
        render_data_panel(selected_key)
