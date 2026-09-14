import streamlit as st
import pandas as pd
import os
import re
import base64
import json
import io
import time
import re as _re_notice_link  # 🟢 Notice Board me URL detect karke clickable link banane ke liye
import html as _html_escape_lib  # 🟢 Notice text ko safely HTML-escape karne ke liye
import requests  # 🟢 P10 naam-transliteration (Google Input Tools) ke liye
import streamlit.components.v1 as components  # 🟢 यह लाइन यहाँ नीचे जोड़नी है

# 🟢 P10 प्रिंट ट्रांसलेशन फीचर के लिए लाइब्रेरी (अगर इंस्टॉल नहीं है तो feature अपने आप डिसेबल हो जाएगा)
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except Exception:
    TRANSLATOR_AVAILABLE = False

# ==========================================================
# ⚙️ स्टेप 1: पेज का लेआउट सेट करें और डिफ़ॉल्ट थीम्स बनाएं
# ==========================================================
st.set_page_config(layout="wide", page_title="Permanent Shared Live Database")

# डेटा स्टोरेज फ़ाइलों के पाथ और नाम परिभाषा
DB_FILE = "shared_student_database.csv"
STAGE_FILE = "merge_stage_database.csv"
CRED_FILE = "user_credentials_v15.json"
MAP_FILE = "column_mapping_schema.json"
PANEL_NAME_FILE = "panel_names_schema.json"
TWIN_MAP_FILE = "twin_column_mapping_schema.json"
PRE_LOGIN_CONFIG_FILE = "pre_login_view_config.json"
DYNAMIC_LISTS_FILE = "p1_dynamic_lists_schema.json"

# 🟢 ADD THIS MISSING LINE HERE:
NOTICE_FILE = "notice_board_schema.json" 

# 🟢 P12 SYLLABUS MANAGER: subject-wise syllabus (file ya link) yahin store hoga
SYLLABUS_FILE = "subject_syllabus_schema.json"
SYLLABUS_UPLOAD_DIR = "syllabus_uploads"
# 🟢 Syllabus ke liye Year options — app me baaki jagah (P4/P10 etc.) jo standard Year
# labels use hote hain (1st Year, 2nd Year...) wahi yahan bhi use kar rahe hain, taaki
# poori app me Year ka matlab hamesha ek jaisa rahe.
SYLLABUS_YEAR_OPTIONS = ["1st Year", "2nd Year", "3rd Year", "4th Year", "5th Year", "6th Year"]
# 🟢 नया: PG (Post-Graduate) जैसे कोर्सेज़ के लिए Semester-wise Syllabus विकल्प — जैसे 2 Year का
# PG कोर्स हो to 4 Semester (1st Sem. से 4th Sem.) बनते हैं। P10 पैनल में जो Semester labels
# already इस्तेमाल होते हैं, वही यहाँ भी इस्तेमाल कर रहे हैं ताकि पूरी app में नाम एक जैसे रहें।
SYLLABUS_SEM_OPTIONS = [
    "1st Sem.", "2nd Sem.", "3rd Sem.", "4th Sem.", "5th Sem.", "6th Sem.",
    "7th Sem.", "8th Sem.", "9th Sem.", "10th Sem.", "11th Sem.", "12th Sem."
]

# डिफ़ॉल्ट कॉन्फ़िगरेशन बैकअप डिक्शनरी
DEFAULT_PRE_LOGIN_CONFIG = {
    "show_header_text": True,
    "header_mantra": "ॐ श्री गुरवे नमः",
    "system_title": "Permanent Shared Live Database System",
    "header_mantra_font_size": 24,   # 🟢 Mantra line ka font size (px)
    "header_title_font_size": 32,    # 🟢 Main title line ka font size (px)
    "notice_board_border_color": "#FF5733",
    "notice_board_bg_color": "#f9f9f9",
    "logo_width": 110,
    "logo_height": 110,
    "logo_fit_mode": "contain"
}

DEFAULT_DYNAMIC_LISTS = {
    "file_types": [
        "admission file", "admission fee file", "unique id file", 
        "roll no file", "enrollment file", "promotion file", "result file"
    ],
    "academic_years": [str(year) for year in range(2014, 2027)],
    "academic_sessions": [f"{year}-{str(year+1)[2:]}" for year in range(2014, 2027)]
}

DEFAULT_NOTICE = (
    "1. यह एक पूर्णतः सुरक्षित, लाइव क्लाउड स्टूडेंट डेटाबेस मैनेजमेंट सिस्टम है।\n"
    "2. डेटा प्रविष्टि, सुधार, स्कॉलरशिप वेरिफिकेशन या परीक्षा परिणाम अपडेट करने के लिए अधिकृत यूजर क्रेडेंशियल्स का उपयोग करें।\n"
    "3. बिना लॉगिन के डेटाबेस तक पहुँच पूर्णतः प्रतिबंधित है। किसी भी समस्या के लिए सुपर-एडमिन से संपर्क करें।"
)

DEFAULT_CREDENTIALS = {
    "admin": {"password": "admin15master", "role": "full_admin", "label": "👑 Super Admin (Selected Panels Control)"},
    "p1_entry": {"password": "entry1123", "role": "p1_role", "label": "📝 P1: Student Data Onboarding Operator"},
    "p2_admission": {"password": "adm2123", "role": "p2_role", "label": "🎓 P2: Admission Control Manager"},
    "p3_scholarship": {"password": "sch6123", "role": "p3_role", "label": "💰 P3: Portal & Scholarship Tracker"},
    "p4_cce": {"password": "cce7123", "role": "p4_role", "label": "🖨️ P4: CCE panel & File Format Upload"},
    "p5_notice": {"password": "not11123", "role": "p5_role", "label": "📢 P5: System Informer Block"},
    "p6_merge": {"password": "mrg13123", "role": "p6_role", "label": "🔀 P6: Merge & Approve Panel"},
    "p7_viewer": {"password": "view14123", "role": "p7_role", "label": "👁️ P7: Multi-Panel Inspection Window"}
}

DEFAULT_PANELS = {
    "P1": "Panal entry", "P2": "Admission panel", "P3": "Scholarship panel",
    "P4": "CCE panel", "P5": "notice board info", "P6": "🔀 Merge & Approve Panel",
    "P7": "Panal viewer", "P8": "Panel admin"
}

DEFAULT_COLUMNS = [
    "Admission Year", "Admission Session", "Eligibility Name", "Admission Application Number",
    "Admission Date", "Unique ID", "Roll No.", "Application Enrollment No.",
    "Enrollment No.", "Student Name", "Father Name", "Mother Name", "Date of Birth",
    "Category", "Subject Code", "Subject", "Duration", "Mobile Number", "Email ID", "Address", "Status",
    "Current Year", "Application Number", "Student Abc Id", "Gender", "Admission Category", "Degree",
    "Branch", "Minor Subjects", "Vocational Subjects", "MDC Subjects", "PW/Ap/CE Subjects",
    "Admssion & Enrollment Fees", "Scholarship Name", "Payment Date", "Target Panel Visibility",
    "CCE Marks Obtained", "CCE Attendance Status", "Promotion Status", "Marks Obtained", "Result Status", "Exam Remarks",
    # 🟢 P2 पैनल की पूरी कॉलम लिस्ट के लिए नए जोड़े गए फ़ील्ड्स (फ़िलहाल खाली रहेंगे,
    # ज़रूरत अनुसार P1 एंट्री या एडमिन एडिट से भरे जा सकते हैं / बाद में अनुपयोगी होने पर हटाए जा सकते हैं)
    "Merit (%)", "Obtain (%)", "Bonus (%)", "Weightage (%)", "Class", "Ncc Type",
    "IsDisabled", "Final Status", "Subject Selection Status"
]

# ==========================================================
# 📁 स्टेप 2: डेटा सहेजने और लोड करने वाले कोर फंक्शन्स
# ==========================================================

# 🟢 नया यूटिलिटी फंक्शन: Student Name / Father Name / Mother Name जैसे नाम वाले
# कॉलम्स को हमेशा "Riya Sharma" जैसे Proper Case (हर शब्द का पहला अक्षर Capital) में
# दिखाने के लिए। यह load_live_data और load_stage_data दोनों में लगाया गया है, इसलिए
# चाहे कोई भी बड़े/छोटे अक्षरों में डेटा अपलोड/एंटर करे, हर पैनल में (स्क्रीन पर देखने से
# लेकर प्रिंट तक) यह हमेशा Proper Case में ही दिखेगा — क्योंकि सभी पैनल इसी live_db से डेटा लेते हैं।
NAME_CASE_COLUMNS = ["Student Name", "Father Name", "Mother Name"]

def to_proper_name_case(name_val):
    s = str(name_val).strip()
    if not s or s.lower() == "nan":
        return s
    return " ".join(word.capitalize() for word in s.split(" "))

def apply_name_proper_case(df):
    for name_col in NAME_CASE_COLUMNS:
        if name_col in df.columns:
            df[name_col] = df[name_col].apply(to_proper_name_case)
    return df

def load_pre_login_config():
    if os.path.exists(PRE_LOGIN_CONFIG_FILE):
        try:
            with open(PRE_LOGIN_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict): return data
        except: return DEFAULT_PRE_LOGIN_CONFIG.copy()
    return DEFAULT_PRE_LOGIN_CONFIG.copy()

def save_pre_login_config(config_dict):
    with open(PRE_LOGIN_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_dict, f, ensure_ascii=False, indent=4)

# 🟢 P12 SYLLABUS MANAGER: har Subject + Year ke combination ke liye File-upload YA
# Link — dono me se koi bhi ek tarika chuna ja sakta hai. Data yahan nested format me
# save hota hai: { Subject: { Year: {"type","value","file_name"} } }
def load_syllabus_data():
    if os.path.exists(SYLLABUS_FILE):
        try:
            with open(SYLLABUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict): return data
        except: return {}
    return {}

def save_syllabus_data(data_dict):
    with open(SYLLABUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data_dict, f, ensure_ascii=False, indent=4)

# 🟢 FIX: Ab har Subject ke liye utne hi Years dikhenge jitni uski asli "Duration"
# (jaise 3 saal ka course ho to sirf 1st/2nd/3rd Year hi dikhega, 4th/5th/6th nahi) —
# Duration wahi column hai jo already "Current Year" auto-calculate karne me use hoti hai.
def get_subject_syllabus_year_count(subject_name, df):
    try:
        if "Duration" not in df.columns or "Subject" not in df.columns:
            return len(SYLLABUS_YEAR_OPTIONS)
        sub_rows = df[df["Subject"].astype(str).str.strip() == str(subject_name).strip()]
        durations = pd.to_numeric(sub_rows["Duration"], errors="coerce").dropna()
        if durations.empty:
            return len(SYLLABUS_YEAR_OPTIONS)
        # Us Subject ke jitne bhi students hain, unme sabse zyada baar aaya Duration
        # lete hain — taaki kisi ek galat/typo entry se poori list na bigde
        mode_vals = durations.mode()
        chosen = int(mode_vals.iloc[0]) if not mode_vals.empty else int(durations.iloc[0])
        chosen = max(1, chosen)
        return min(chosen, len(SYLLABUS_YEAR_OPTIONS))
    except Exception:
        return len(SYLLABUS_YEAR_OPTIONS)

def load_dynamic_lists():
    if os.path.exists(DYNAMIC_LISTS_FILE):
        try:
            with open(DYNAMIC_LISTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "file_types" in data and "academic_years" in data and "academic_sessions" in data:
                    return data
        except: return DEFAULT_DYNAMIC_LISTS.copy()
    return DEFAULT_DYNAMIC_LISTS.copy()

def save_dynamic_lists(lists_dict):
    with open(DYNAMIC_LISTS_FILE, "w", encoding="utf-8") as f:
        json.dump(lists_dict, f, ensure_ascii=False, indent=4)

def load_credentials():
    if os.path.exists(CRED_FILE):
        try:
            with open(CRED_FILE, "r") as f: return json.load(f)
        except: return DEFAULT_CREDENTIALS.copy()
    else:
        with open(CRED_FILE, "w") as f: json.dump(DEFAULT_CREDENTIALS, f)
        return DEFAULT_CREDENTIALS.copy()

def load_panel_names():
    if os.path.exists(PANEL_NAME_FILE):
        try:
            with open(PANEL_NAME_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return DEFAULT_PANELS.copy()
    return DEFAULT_PANELS.copy()

def save_panel_names(panel_dict):
    with open(PANEL_NAME_FILE, "w", encoding="utf-8") as f:
        json.dump(panel_dict, f, ensure_ascii=False, indent=4)

def load_column_mappings():
    if os.path.exists(MAP_FILE):
        try:
            with open(MAP_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def load_notice_board():
    if os.path.exists(NOTICE_FILE):
        try:
            with open(NOTICE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("notice_text", DEFAULT_NOTICE)
        except: return DEFAULT_NOTICE
    return DEFAULT_NOTICE

def save_notice_board(text):
    with open(NOTICE_FILE, "w", encoding="utf-8") as f:
        json.dump({"notice_text": text}, f, ensure_ascii=False, indent=4)

# 🟢 NOTICE BOARD LINK FEATURE:
# Agar Notice me admin koi link (http://..., https://..., ya www....) type karta hai,
# to use is function se pehle HTML-escape karke, phir us link ko clickable <a> tag me
# badal dete hain — jisse user Notice Board par us link par touch/click karke seedhe
# us page par pahunch jaaye (naya tab me khulega, taaki Notice Board wala tab band na ho).
_NOTICE_URL_PATTERN = _re_notice_link.compile(
    r'((?:https?://|www\.)[^\s<>\"\']+)', _re_notice_link.IGNORECASE
)

def linkify_notice_line(line_text):
    """Ek line ke andar jitne bhi URL (http/https/www) mile, unhe safe clickable <a> tag me convert karta hai.
    Baaki normal text HTML-escape karke as-is rakha jaata hai (taaki koi bhi galti se HTML/script
    likh de to bhi wo tootn na paaye)."""
    escaped = _html_escape_lib.escape(line_text)

    def _make_link(match):
        raw_url = match.group(1)
        # Trailing punctuation (., ,, ), आदि) ko link ke bahar rakho taaki link kharab na ho
        trailing = ""
        while raw_url and raw_url[-1] in ".,);:!?\u0964":
            trailing = raw_url[-1] + trailing
            raw_url = raw_url[:-1]
        href = raw_url if raw_url.lower().startswith("http") else "https://" + raw_url
        return (
            f'<a href="{href}" target="_blank" rel="noopener noreferrer" '
            f'style="color:#1465de; text-decoration:underline; font-weight:600;">{raw_url}</a>{trailing}'
        )

    return _NOTICE_URL_PATTERN.sub(_make_link, escaped)

# 🆕 P5 डायनेमिक कॉलम मैपिंग लोडर फंक्शन
def load_twin_mappings():
    if os.path.exists(TWIN_MAP_FILE):
        try:
            with open(TWIN_MAP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

# 🆕 P5 डायनेमिक कॉलम मैपिंग सेवर फंक्शन
def save_twin_mappings(mapping_dict):
    with open(TWIN_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping_dict, f, ensure_ascii=False, indent=4)

def load_live_data():
    if not os.path.exists(DB_FILE) or os.path.getsize(DB_FILE) == 0:
        df_empty = pd.DataFrame(columns=DEFAULT_COLUMNS)
        df_empty.to_csv(DB_FILE, index=False)
        return df_empty
    try:
        df = pd.read_csv(DB_FILE, dtype=str)
        for col in DEFAULT_COLUMNS:
            if col not in df.columns: df[col] = ""
        df = df.fillna("").reset_index(drop=True)
        df = apply_name_proper_case(df)
        
        # 🔄 P5 डायनेमिक लोड-टाइम सिंक इंजन (Twin Sync)
        twin_maps = load_twin_mappings()
        for source_col, target_col in twin_maps.items():
            if source_col in df.columns and target_col in df.columns:
                # दोनों तरफ से डेटा अलाइन करें ताकि किसी भी पैनल को खाली डेटा न दिखे
                mask1 = (df[source_col].astype(str).str.strip() != "") & (df[target_col].astype(str).str.strip() == "")
                df.loc[mask1, target_col] = df.loc[mask1, source_col]
                
                mask2 = (df[target_col].astype(str).str.strip() != "") & (df[source_col].astype(str).str.strip() == "")
                df.loc[mask2, source_col] = df.loc[mask2, target_col]
        return df
    except:
        return pd.DataFrame(columns=DEFAULT_COLUMNS)

def save_live_data(df_to_save):
    if df_to_save.empty:
        df_to_save.fillna("").astype(str).to_csv(DB_FILE, index=False)
        return

    df_temp = df_to_save.copy()
    
    # 🔄 P5 डायनेमिक सेव-टाइम सिंक इंजन (Twin Sync)
    twin_maps = load_twin_mappings()
    for source_col, target_col in twin_maps.items():
        if source_col in df_temp.columns and target_col in df_temp.columns:
            for idx, row in df_temp.iterrows():
                src_val = str(row.get(source_col, "")).strip()
                tgt_val = str(row.get(target_col, "")).strip()
                
                if src_val != "" and tgt_val == "":
                    df_temp.at[idx, target_col] = src_val
                elif tgt_val != "" and src_val == "":
                    df_temp.at[idx, source_col] = tgt_val
                elif src_val != tgt_val and src_val != "":
                    # यदि दोनों कॉलम में अलग डेटा है, तो प्राथमिक रूप से सोर्स कॉलम का डेटा सिंक करें
                    df_temp.at[idx, target_col] = src_val

    # 🛑 नो न्यू कॉलम पॉलिसी: केवल ओरिजिनल DEFAULT_COLUMNS ही सीएसवी फ़ाइल में सेव होंगे
    final_cols_to_save = [col for col in DEFAULT_COLUMNS if col in df_temp.columns]
    df_temp[final_cols_to_save].fillna("").astype(str).to_csv(DB_FILE, index=False)

def load_stage_data():
    if not os.path.exists(STAGE_FILE) or os.path.getsize(STAGE_FILE) == 0:
        return pd.DataFrame(columns=DEFAULT_COLUMNS + ["Uploaded File Name"])
    try:
        df = pd.read_csv(STAGE_FILE, dtype=str)
        df = df.fillna("").reset_index(drop=True)
        df = apply_name_proper_case(df)

        # 🟢 सेफ्टी-नेट फिक्स: पुराने मैनुअल एंट्री बग की वजह से कुछ पेंडिंग रिकॉर्ड्स में
        # "Date Of Birth" / "Email" / "Enrollment No" जैसे गलत-नाम वाले कॉलम बन गए होंगे।
        # यहाँ उनका डेटा सही स्कीमा कॉलम ("Date of Birth" / "Email ID" / "Enrollment No.") में
        # कॉपी करके गलत कॉलम हटा दिया जाता है, ताकि कोई डेटा गुम न हो।
        legacy_fix_map = {"Date Of Birth": "Date of Birth", "Email": "Email ID", "Enrollment No": "Enrollment No."}
        for bad_col, good_col in legacy_fix_map.items():
            if bad_col in df.columns:
                if good_col not in df.columns:
                    df[good_col] = ""
                mask = (df[good_col].astype(str).str.strip() == "") & (df[bad_col].astype(str).str.strip() != "")
                df.loc[mask, good_col] = df.loc[mask, bad_col]
                df = df.drop(columns=[bad_col])

        return df.reset_index(drop=True)
    except:
        return pd.DataFrame(columns=DEFAULT_COLUMNS + ["Uploaded File Name"])

def save_stage_data(df_to_save):
    df_to_save.fillna("").astype(str).to_csv(STAGE_FILE, index=False)

def get_image_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as image_file:
            return f"data:image/png;base64,{base64.b64encode(image_file.read()).decode()}"
    return ""

# ==========================================================
# 🧠 स्टेप 3: सेशन स्टेट वेरिएबल्स इनिशियलाइज़ेशन
# ==========================================================
if "pre_login_config" not in st.session_state or not isinstance(st.session_state.pre_login_config, dict):
    st.session_state.pre_login_config = load_pre_login_config()

if "dynamic_lists" not in st.session_state:
    st.session_state.dynamic_lists = load_dynamic_lists()

if "p1_dropdown_schemas" not in st.session_state:
    st.session_state.p1_dropdown_schemas = {
        "file_types": [
            "admission file", "admission fee file", "unique id file", 
            "roll no file", "enrollment file", "promotion file", "result file"
        ],
        "academic_years": [str(year) for year in range(2014, 2027)],
        "academic_sessions": [f"{year}-{str(year+1)[2:]}" for year in range(2014, 2027)]
    }

if "credentials" not in st.session_state or len(st.session_state.credentials) < 14:
    st.session_state.credentials = load_credentials()

if "column_mappings" not in st.session_state: 
    st.session_state.column_mappings = load_column_mappings()

if "panel_names" not in st.session_state or len(st.session_state.panel_names) < 15:
    st.session_state.panel_names = load_panel_names()

if "notice_text" not in st.session_state:
    st.session_state.notice_text = load_notice_board()

if "user_role" not in st.session_state: st.session_state.user_role = None  
if "logged_username" not in st.session_state: st.session_state.logged_username = None
if "show_login_form" not in st.session_state: st.session_state.show_login_form = False
if "admin_columns_order" not in st.session_state: st.session_state.admin_columns_order = DEFAULT_COLUMNS.copy()
if "admin_lock_state" not in st.session_state: st.session_state.admin_lock_state = True
if "admin_unhide_edit" not in st.session_state: st.session_state.admin_unhide_edit = False
if "admin_unhide_move" not in st.session_state: st.session_state.admin_unhide_move = False
if "admin_hide_master_data" not in st.session_state: st.session_state.admin_hide_master_data = False
if "cce_foil_generated" not in st.session_state: st.session_state.cce_foil_generated = False
if "p10_reg_list_generated" not in st.session_state: st.session_state.p10_reg_list_generated = False

# 🆕 फ़ाइल अपलोडर को खाली करने के लिए काउंटर (P1 ऑटो-क्लियर मैकेनिज्म हेतु)
if "uploader_key_counter" not in st.session_state:
    st.session_state.uploader_key_counter = 0

for k in DEFAULT_PANELS.keys():
    if f"hide_panel_{k}" not in st.session_state: st.session_state[f"hide_panel_{k}"] = False

# ==========================================================
# 🧠 स्टेप 3.5: मास्टर रिपॉजिटरी लोड और ऑटो-ईयर कैलकुलेशन इंजन (Duration Based)
# ==========================================================
# 1. डेटाबेस से मूल डेटा लोड करें
live_db = load_live_data()

# 2. कोर्स Duration के आधार पर लाइव ऑटोमैटिक ईयर कैलकुलेशन इंजन
if not live_db.empty and "Admission Year" in live_db.columns:
    try:
        # एडमिशन ईयर कॉलम से सबसे हाईएस्ट (लेटेस्ट) साल ढूंढें
        valid_years = pd.to_numeric(live_db["Admission Year"], errors='coerce').dropna()
        if not valid_years.empty:
            highest_admission_year = int(valid_years.max())
            
            # प्रत्येक रो के लिए लाइव एडमिशन ईयर और कोर्स Duration के आधार पर कैलकुलेट करें
            def calculate_current_academic_year(row):
                try:
                    row_admission_year = row.get("Admission Year", "")
                    student_status = str(row.get("Status", "")).strip().upper()
                    
                    # Duration कॉलम का मान निकालें और स्पेस साफ़ करें
                    duration_val = str(row.get("Duration", "")).strip()
                    
                    # 🚨 नियम: यदि Duration कॉलम खाली है, nan है, तो सीधे अलर्ट दिखाएँ
                    if not duration_val or duration_val == "" or duration_val.lower() == "nan" or duration_val == "0":
                        return "plz Fill the Duretion"
                    
                    max_duration = int(float(duration_val))
                    adm_yr = int(float(row_admission_year))
                    year_diff = highest_admission_year - adm_yr
                    
                    # यदि अंतर कोर्स की अवधि के अंदर है (जैसे 1st Year से 6th Year तक)
                    if 0 <= year_diff < max_duration:
                        if year_diff == 0: return "1st Year"
                        elif year_diff == 1: return "2nd Year"
                        elif year_diff == 2: return "3rd Year"
                        elif year_diff == 3: return "4th Year"
                        elif year_diff == 4: return "5th Year"
                        elif year_diff == 5: return "6th Year"
                        else: return f"{year_diff + 1}th Year"
                    
                    # यदि अंतर कोर्स की अवधि के बराबर या उससे ज़्यादा हो चुका है
                    elif year_diff >= max_duration:
                        if student_status == "EX-STUDENT":
                            return "EX-STUDENT"
                        else:
                            return "Passout"
                    else:
                        return "1st Year"
                except:
                    return "plz Fill the Duretion"
            
            # पूरे डेटाबेस ग्रिड को लाइव अपडेट करें
            live_db["Current Year"] = live_db.apply(calculate_current_academic_year, axis=1)
            if "Year" in live_db.columns:
                live_db["Year"] = live_db["Current Year"]
                
    except Exception as auto_yr_err:
        st.error(f"करंट ईयर ऑटो-कैलकुलेशन इंजन में तकनीकी समस्या: {auto_yr_err}")

# पी12 और कॉलम मैपिंग के लिए यूटिलिटी फ़ंक्शंस
def get_display_name(internal_col_name):
    return st.session_state.column_mappings.get(internal_col_name, internal_col_name)

def get_panel_title(panel_id):
    return st.session_state.panel_names.get(panel_id, DEFAULT_PANELS[panel_id])

def save_p1_dropdown_schemas():
    P1_SCHEMA_FILE = "p1_dropdown_config_schema.json"
    with open(P1_SCHEMA_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.p1_dropdown_schemas, f, ensure_ascii=False, indent=4)

# ==========================================================
# 🎨 स्टेप 4: डायनेमिक सीएसएस (CSS) रेंडरिंग इंजन (परफेक्ट स्क्रीन हाइड फिक्स)
# ==========================================================
b_color = st.session_state.pre_login_config.get("notice_board_border_color", "#FF5733")
bg_color = st.session_state.pre_login_config.get("notice_board_bg_color", "#f9f9f9")

st.markdown(f"""
    <style>
    /* 📋 स्क्रीन पर इस कंटेनर को पूरी तरह गायब रखें (ताकि नीचे कोई लिस्ट न दिखे) */
    .print-only-container {{
        display: none !important;
    }}
    
    @media print {{
        /* 1. स्क्रीन की बाकी सारी चीजें (हेडर, फॉर्म, बटन्स और ऐप की ओरिजिनल ग्रिड) छुपाएं */
        header, [data-testid="stHeader"], [data-testid="stSidebar"], 
        [data-testid="stDecoration"], [data-testid="stNotification"], 
        [data-testid="stForm"], .header-container, .notice-board,
        .print-hide, iframe, div.element-container, div[data-testid="stDataFrame"] {{
            display: none !important;
        }}
        
        /* 2. प्रिंट लेते समय इस कंटेनर और इसके अंदर की टेबल को एक्टिव करें */
        .print-only-container {{
            display: block !important;
        }}
        .print-only-container table {{
            display: table !important;
            width: 100% !important;
            border-collapse: collapse !important;
            font-family: Arial, sans-serif !important;
            font-size: 11px !important;
            color: #000 !important;
        }}
        .print-only-container th {{
            background-color: #f2f2f2 !important;
            border: 1px solid #111 !important;
            padding: 6px !important;
            font-weight: bold !important;
            text-align: center !important;
        }}
        .print-only-container td {{
            border: 1px solid #111 !important;
            padding: 5px !important;
            text-align: left !important;
        }}
        
        @page {{ 
            margin: 8mm; 
            size: A4 landscape; 
        }}
    }}
    
    /* स्क्रीन डिस्प्ले के लिए सामान्य CSS */
    .header-container {{ display: flex; align-items: center; gap: 20px; margin-bottom: 20px; }}
    .header-text {{ display: flex; flex-direction: column; }}
    .header-text h3 {{ margin: 0 !important; padding: 0 !important; color: #1465de; }}
    .header-text h1 {{ margin: 0 !important; }}
    
    .notice-board {{
        background-color: {bg_color};
        border-left: 6px solid {b_color};
        padding: 15px;
        margin-bottom: 25px;
        border-radius: 4px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    .notice-title {{ font-weight: bold; color: #333; margin-bottom: 8px; font-size: 18px; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================================
# 🛑स्टेप 5: सुरक्षित लॉगिन ऑथेंटिकेशन गेटवे (Bold Mantra & Shadow Border Added)
# ==========================================================
if st.session_state.user_role is None:
    show_header = st.session_state.pre_login_config.get("show_header_text", True)
    mantra = st.session_state.pre_login_config.get("header_mantra", "ॐ श्री गुरवे नमः")
    sys_title = st.session_state.pre_login_config.get("system_title", "Permanent Shared Live Database System")
    logo_file_path = st.session_state.pre_login_config.get("logo_path", "logo pratap.png")
    logo_w = st.session_state.pre_login_config.get("logo_width", 110)
    logo_h = st.session_state.pre_login_config.get("logo_height", 110)
    logo_fit = st.session_state.pre_login_config.get("logo_fit_mode", "contain")
    mantra_font_px = int(st.session_state.pre_login_config.get("header_mantra_font_size", 24))  # 🟢 FONT SIZE OPTION
    title_font_px = int(st.session_state.pre_login_config.get("header_title_font_size", 32))    # 🟢 FONT SIZE OPTION
    
    if show_header:
        img_base64 = get_image_base64(logo_file_path)
        
        # 🎨 यहाँ लोगो पर 'box-shadow' बॉर्डर और मंत्र को 'font-weight: bold' किया गया है
        header_html = f"""
        <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 20px; font-family: sans-serif;">
            <div style="flex-shrink: 0; width: {logo_w}px; height: {logo_h}px; display: flex; align-items: center; justify-content: center; overflow: hidden; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.15), 0 0 1px rgba(0,0,0,0.2); border: 1px solid #e2e8f0;">
                {"<img src='" + img_base64 + "' style='width: 100%; height: 100%; object-fit: " + logo_fit + "; display: block;'>" if img_base64 else "<h1 style='margin: 0;'>🏛️</h1>"}
            </div>
            <div style="display: flex; flex-direction: column; justify-content: center;">
                <h3 style="margin: 0 !important; padding: 0 !important; color: #1465de; font-weight: bold !important; font-size: {mantra_font_px}px; letter-spacing: 0.5px;">{mantra}</h3>
                <h1 style="margin: 5px 0 0 0 !important; padding: 0 !important; color: #212529; font-size: {title_font_px}px; font-weight: bold;">{sys_title}</h1>
            </div>
        </div>
        <hr style="margin-top: 10px; margin-bottom: 25px; border: 0; border-top: 1px solid #eee;">
        """
        st.markdown(header_html, unsafe_allow_html=True)

    # 📢 कॉलेज सूचना पटल (Official Notice Board)
    # 🟢 FIX: ab har line ke andar agar koi link (http/https/www) hai to use HTML-escape karne
    # ke baad clickable <a> tag me convert kar dete hain — Notice Board par click/touch karte hi
    # user seedhe us link ke page par (naye tab me) pahunch jaayega.
    formatted_notice = "".join([f"<p>{linkify_notice_line(line.strip())}</p>" for line in st.session_state.notice_text.split('\n') if line.strip()])
    st.markdown(f"""
        <div class="notice-board">
            <div class="notice-title">📢 कॉलेज सूचना पटल (Official Notice Board)</div>
            {formatted_notice}
        </div>
    """, unsafe_allow_html=True)

    # ==========================================================
    # 📚 STUDENT SYLLABUS LOOKUP (बिना लॉगिन के, Desk Board पर ही)
    # P12 (Admin) me jo Subject + Year ke hisab se Syllabus File/Link
    # save ki jaati hai, wahi yahan student khud Subject aur Year
    # chunkar dekh/download kar sakta hai — koi login nahi chahiye.
    # ==========================================================
    _p_syllabus_data = load_syllabus_data()
    # 🟢 Fix: "__mode__" sirf Year/Semester mode yaad rakhne wali internal key hai (koi
    # asli Syllabus entry nahi) — isliye is akeli key ke aadhar par Subject ko "Syllabus
    # available" mat maano, warna khaali Subject bhi list me dikhne lagega.
    _p_syllabus_subjects = sorted([
        s for s, yrs in _p_syllabus_data.items()
        if any(k != "__mode__" for k in yrs)
    ])
    if _p_syllabus_subjects:
        st.markdown("---")
        st.markdown("### 📚 अपना Syllabus देखें (Check Your Syllabus)")
        st.caption("नीचे अपना Subject और Year/Semester चुनें — Syllabus File या Link तुरंत यहीं मिल जाएगी।")

        _p_col_subj, _p_col_year = st.columns(2)
        with _p_col_subj:
            _p_sel_subject = st.selectbox(
                "📘 अपना Subject चुनें:",
                options=_p_syllabus_subjects,
                key="p_public_syllabus_subject_select"
            )
        with _p_col_year:
            # 🟢 नया: Subject ya to Year-wise (SYLLABUS_YEAR_OPTIONS) ya Semester-wise
            # (SYLLABUS_SEM_OPTIONS — जैसे PG के 2 Year = 4 Semester) मोड में सेव हुआ हो सकता
            # है, इसलिए दोनों लिस्ट में से जो भी इस Subject में असल में मौजूद हैं वही दिखाएँ।
            _p_subj_years_available = [
                y for y in (SYLLABUS_YEAR_OPTIONS + SYLLABUS_SEM_OPTIONS)
                if y in _p_syllabus_data.get(_p_sel_subject, {})
            ]
            if _p_subj_years_available:
                _p_sel_year = st.selectbox(
                    "🗓️ अपना Year/Semester चुनें:",
                    options=_p_subj_years_available,
                    key="p_public_syllabus_year_select"
                )
            else:
                _p_sel_year = None
                st.info("इस Subject के लिए अभी किसी भी Year/Semester की Syllabus उपलब्ध नहीं है।")

        if _p_sel_year:
            _p_result = _p_syllabus_data.get(_p_sel_subject, {}).get(_p_sel_year, {})
            if _p_result.get("type") == "file" and _p_result.get("value") and os.path.exists(_p_result["value"]):
                st.success(f"✅ **{_p_sel_subject} — {_p_sel_year}** की Syllabus मिल गई!")
                try:
                    with open(_p_result["value"], "rb") as _p_fh:
                        st.download_button(
                            "⬇️ Syllabus Download करें",
                            data=_p_fh.read(),
                            file_name=_p_result.get("file_name", os.path.basename(_p_result["value"])),
                            key="p_public_syllabus_download_btn",
                            use_container_width=True,
                            type="primary"
                        )
                except Exception:
                    st.error("⚠️ फ़ाइल पढ़ने में समस्या आई — कृपया एडमिन से संपर्क करें।")
            elif _p_result.get("type") == "link" and _p_result.get("value"):
                st.success(f"✅ **{_p_sel_subject} — {_p_sel_year}** की Syllabus मिल गई!")
                st.markdown(
                    f'<a href="{_p_result["value"]}" target="_blank" rel="noopener noreferrer" '
                    f'style="display:inline-block; padding:10px 18px; background:#1465de; color:white; '
                    f'border-radius:6px; text-decoration:none; font-weight:600;">🔗 Syllabus खोलें (नए टैब में)</a>',
                    unsafe_allow_html=True
                )
            else:
                st.info("इस Subject/Year के लिए अभी Syllabus उपलब्ध नहीं है।")

    if not st.session_state.show_login_form:
        if st.button("🔐 Click Here to Open Secure Login System", type="primary", use_container_width=True):
            st.session_state.show_login_form = True
            st.rerun()
            
    if st.session_state.show_login_form:
        st.markdown("---")
        st.subheader("🔒 Enter Secure Gateway Credentials")
        col_l1, col_l2 = st.columns(2)
        
        with col_l1:
            user_list_options = list(st.session_state.credentials.keys())
            def get_lbl(uid): return st.session_state.credentials[uid].get("label", uid)
            user_input = st.selectbox("👤 Select Your User ID / Panel Account:", options=user_list_options, format_func=get_lbl)
            
        with col_l2:
            password_input = st.text_input("🔑 Enter Secure Password:", type="password")
            
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("🔓 Verify & Access System", type="primary", use_container_width=True):
                if user_input in st.session_state.credentials and st.session_state.credentials[user_input]["password"] == password_input:
                    st.session_state.user_role = st.session_state.credentials[user_input]["role"]
                    st.session_state.logged_username = user_input
                    st.session_state.show_login_form = False
                    st.success("✅ क्रेडेंशियल स्वीकृत! पैनल में प्रवेश किया जा रहा है...")
                    st.rerun()
                else:
                    st.error("❌ गलत पासवर्ड दर्ज किया गया है!")
                    
        with c_btn2:
            if st.button("❌ Close Login Windows", type="secondary", use_container_width=True):
                st.session_state.show_login_form = False
                st.rerun()

# ==========================================================
# 🧭 स्टेप 6: पोस्ट-लॉगिन वर्कस्पेस और पैनल राउटिंग इंजन
# ==========================================================
else:
    role = st.session_state.user_role
    username = st.session_state.logged_username
    
    # 🏛️ हर पैनल के ऊपर भी इमेज जैसा हॉरिजॉन्टल हेडर दिखाएं
    show_header = st.session_state.pre_login_config.get("show_header_text", True)
    mantra = st.session_state.pre_login_config.get("header_mantra", "ॐ श्री गुरवे नमः")
    sys_title = st.session_state.pre_login_config.get("system_title", "Permanent Shared Live Database System")
    logo_file_path = st.session_state.pre_login_config.get("logo_path", "logo pratap.png")
    logo_w = st.session_state.pre_login_config.get("logo_width", 110)
    logo_h = st.session_state.pre_login_config.get("logo_height", 110)
    logo_fit = st.session_state.pre_login_config.get("logo_fit_mode", "contain")
    # 🟢 FONT SIZE OPTION: panel ke andar header thoda chhota rehta hai, isliye yahan
    # Part-2 me set kiye gaye size ka ~75% le rahe hain (login page jaisa bada nahi, lekin
    # ratio bana rehta hai — jitna bada Mantra/Title font Part-2 me set karoge, utna hi
    # yahan bhi proportionally bada/chhota dikhega).
    mantra_font_px = max(10, int(round(int(st.session_state.pre_login_config.get("header_mantra_font_size", 24)) * 0.75)))
    title_font_px = max(10, int(round(int(st.session_state.pre_login_config.get("header_title_font_size", 32)) * 0.75)))
    
    if show_header:
        img_base64 = get_image_base64(logo_file_path)
        
        # 🎨 पैनल के अंदर प्रीमियम शैडो बॉर्डर और बोल्ड लुक
        panel_header_html = f"""
        <div class="print-hide" style="display: flex; align-items: center; gap: 15px; margin-bottom: 15px; font-family: sans-serif;">
            <div style="flex-shrink: 0; width: {logo_w}px; height: {logo_h}px; display: flex; align-items: center; justify-content: center; overflow: hidden; border-radius: 6px; box-shadow: 0 3px 8px rgba(0,0,0,0.12); border: 1px solid #e2e8f0;">
                {"<img src='" + img_base64 + "' style='width: 100%; height: 100%; object-fit: " + logo_fit + "; display: block;'>" if img_base64 else "<h2 style='margin: 0;'>🏛️</h2>"}
            </div>
            <div style="display: flex; flex-direction: column; justify-content: center;">
                <h4 style="margin: 0 !important; padding: 0 !important; color: #1465de; font-weight: bold !important; font-size: {mantra_font_px}px;">{mantra}</h4>
                <h2 style="margin: 3px 0 0 0 !important; padding: 0 !important; color: #212529; font-size: {title_font_px}px; font-weight: bold;">{sys_title}</h2>
            </div>
        </div>
        <div class="print-hide"><hr style="margin-top: 5px; margin-bottom: 15px; border: 0; border-top: 1px solid #eee;"></div>
        """
        st.markdown(panel_header_html, unsafe_allow_html=True)

    # 🚪 सक्रिय सत्र और लॉगआउट ब्लॉक
    st.markdown('<div class="print-hide">', unsafe_allow_html=True)
    col_top1, col_top2 = st.columns(2)
    with col_top1:
        st.success(f"🔑 सक्रिय सत्र: {username.upper()} | भूमिका अधिकार: {role.upper()}")
    with col_top2:
        if st.button("🔒 Secure Logout / Exit System", type="primary", use_container_width=True):
            st.session_state.user_role = None
            st.session_state.logged_username = None
            st.session_state.cce_foil_generated = False
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("---")

    allowed_panels = []
    if role == "full_admin":
        allowed_panels = list(DEFAULT_PANELS.keys()) 
    elif role == "p1_role": allowed_panels = ["P1"]
    elif role == "p2_role": allowed_panels = ["P2"]
    elif role == "p3_role": allowed_panels = ["P3"]
    elif role == "p4_role": allowed_panels = ["P4"]
    elif role == "p5_role": allowed_panels = ["P5"]
    elif role == "p6_role": allowed_panels = ["P6"]
    elif role == "p7_role": allowed_panels = ["P7"]

    active_tabs_names = [f"{p} : {get_panel_title(p)}" for p in allowed_panels if not st.session_state.get(f"hide_panel_{p}", False) or role == "full_admin"]
    
    if not active_tabs_names:
        st.warning("⚠️ वर्तमान में आपकी भूमिका के लिए कोई भी पैनल एक्टिव नहीं किया गया है।")
    else:
        selected_tab_ui = st.sidebar.radio("🧭 Navigate Active Modules:", options=active_tabs_names)
        
        # 🎯 यहाँ फिक्स किया गया है (अंतिम भाग [0] को जोड़कर इसे दोबारा स्ट्रिंग बनाया गया है)
        current_panel_id = selected_tab_ui.split(" : ")[0]

        # ----------------------------------------------------------------------
        # P1: PANEL ENTRY MODULE (3 Scroll Lists & Multi-Format Upload System)
        # ----------------------------------------------------------------------

# ==========================================================
# 🔽🔽🔽 EXTRACTED PANELS: P1, P2, P3, P4, P5, P12, P6, P8 🔽🔽🔽
# ==========================================================

        if current_panel_id == "P1":
            st.header(f"📝 {get_panel_title('P1')} (Student Data Onboarding)")
            entry_method = st.selectbox(
                "⚙️ डेटा एंट्री का माध्यम चुनें:", 
                options=["📁 फ़ाइल बल्क अपलोड (Bulk File Upload)", "➕ नया छात्र मैनुअल फॉर्म (Manual Form Entry)"]
            )
            
            # 📁 बल्क फ़ाइल अपलोड सब-सिस्टम
            if entry_method == "📁 फ़ाइल बल्क अपलोड (Bulk File Upload)":
                st.subheader("📊 Select Target Configurations Before Upload")
                col_sc1, col_sc2, col_sc3 = st.columns(3)
                
                with col_sc1:
                    p1_file_type = st.selectbox(
                        "1. फ़ाइल प्रकार चुनें (Select File Type):",
                        options=["-- चुनें --"] + st.session_state.p1_dropdown_schemas["file_types"],
                        key="p1_scroll_file_type"
                    )
                with col_sc2:
                    p1_admission_year = st.selectbox(
                        "2. Admission Year चुनें:",
                        options=["-- चुनें --"] + st.session_state.p1_dropdown_schemas["academic_years"],
                        key="p1_scroll_admission_year"
                    )
                with col_sc3:
                    p1_admission_session = st.selectbox(
                        "3. Admission Session चुनें:",
                        options=["-- चुनें --"] + st.session_state.p1_dropdown_schemas["academic_sessions"],
                        key="p1_session_scroll_secure_bulk_main"
                    )

                if (p1_file_type == "-- चुनें --" or p1_admission_year == "-- चुनें --" or p1_admission_session == "-- चुनें --"):
                    st.info("💡 कृपया फ़ाइल अपलोड विंडो खोलने के लिए ऊपर दिए गए तीनों विकल्पों (File Segment, Year और Session) का चयन करें।")
                else:
                    st.success(f"✅ कॉन्फ़िगरेशन锁: **{p1_file_type.upper()}** | वर्ष: **{p1_admission_year}** | सत्र: **{p1_admission_session}**")
                    
                    uploader_unique_key = f"p1_bulk_uploader_widget_run_{st.session_state.get('uploader_key_counter', 0)}"
                    
                    uploaded_files = st.file_uploader(
                        f"अपलोड करने के लिए '{p1_file_type}' की फ़ाइलें चुनें (अधिकतम 5):", 
                        type=["csv", "xlsx", "xls"],
                        accept_multiple_files=True,
                        key=uploader_unique_key
                    )
                    
                    if uploaded_files:
                        if len(uploaded_files) > 5:
                            st.warning("⚠️ कृपया एक बार में केवल 1 से 5 फ़ाइलें ही अपलोड करें।")
                        
                        if st.button("Upload & Send to System Database Now", type="primary", use_container_width=True):
                            try:
                                success_count = 0
                                current_stage_db = load_stage_data()
                                all_new_dfs = [current_stage_db]
                                
                                for uploaded_file in uploaded_files:
                                    if uploaded_file.name.endswith('.csv'):
                                        uploaded_df = pd.read_csv(uploaded_file, dtype=str).fillna("")
                                    elif uploaded_file.name.endswith('.xlsx'):
                                        uploaded_df = pd.read_excel(uploaded_file, engine='openpyxl', dtype=str).fillna("")
                                    elif uploaded_file.name.endswith('.xls'):
                                        try:
                                            uploaded_df = pd.read_excel(uploaded_file, engine='xlrd', dtype=str).fillna("")
                                        except:
                                            uploaded_file.seek(0) 
                                            html_tables = pd.read_html(uploaded_file)
                                            uploaded_df = html_tables[0].astype(str).fillna("") if html_tables else pd.DataFrame()
                                    
                                    if uploaded_df.empty:
                                        st.error(f"❌ फ़ाइल '{uploaded_file.name}' के अंदर कोई मान्य डेटा नहीं मिला।")
                                        continue

                                    uploaded_df = uploaded_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

                                    # 🧠 स्मार्ट कॉलम मैचिंग: अपलोड फ़ाइल के हेडर अलग-अलग तरीके से लिखे हो सकते हैं
                                    # (जैसे "Enrollment No", "DOB", "Email", "Scholarship" आदि) — इन्हें सही इंटरनल
                                    # कॉलम नाम ("Enrollment No.", "Date of Birth", "Email ID", "Scholarship Name")
                                    # से ऑटोमैटिक मैच करके डेटा गायब होने से बचाएँ।
                                    def _normalize_col_name(name):
                                        return re.sub(r"[^a-z0-9]", "", str(name).strip().lower())

                                    normalized_lookup = {}
                                    for internal_col in DEFAULT_COLUMNS:
                                        normalized_lookup[_normalize_col_name(internal_col)] = internal_col
                                        normalized_lookup[_normalize_col_name(get_display_name(internal_col))] = internal_col

                                    # आम तौर पर एक्सेल/CSV में इस्तेमाल होने वाले जाने-पहचाने वैरिएशन
                                    manual_aliases = {
                                        "enrollmentno": "Enrollment No.",
                                        "enrollmentnumber": "Enrollment No.",
                                        "enrollmentnum": "Enrollment No.",
                                        "universityenrollmentno": "Enrollment No.",
                                        "dob": "Date of Birth",
                                        "dateofbirth": "Date of Birth",
                                        "birthdate": "Date of Birth",
                                        "email": "Email ID",
                                        "emailid": "Email ID",
                                        "emailaddress": "Email ID",
                                        "mailid": "Email ID",
                                        "scholarship": "Scholarship Name",
                                        "scholarshipname": "Scholarship Name",
                                        "scholarshiptitle": "Scholarship Name",
                                    }
                                    for _alias_key, _alias_target in manual_aliases.items():
                                        normalized_lookup.setdefault(_alias_key, _alias_target)

                                    rename_map_for_upload = {}
                                    for col in uploaded_df.columns:
                                        if col in DEFAULT_COLUMNS:
                                            continue  # पहले से ही एकदम सही (exact) इंटरनल नाम है
                                        norm_key = _normalize_col_name(col)
                                        if norm_key in normalized_lookup:
                                            target_internal_col = normalized_lookup[norm_key]
                                            # अगर सही इंटरनल कॉलम पहले से ही फ़ाइल में अलग से मौजूद है, तो टकराव से बचें
                                            if target_internal_col in uploaded_df.columns:
                                                continue
                                            rename_map_for_upload[col] = target_internal_col

                                    if rename_map_for_upload:
                                        uploaded_df = uploaded_df.rename(columns=rename_map_for_upload)
                                    
                                    for col in DEFAULT_COLUMNS:
                                        if col not in uploaded_df.columns: 
                                            uploaded_df[col] = ""
                                    
                                    uploaded_df["Admission Year"] = p1_admission_year
                                    uploaded_df["Admission Session"] = p1_admission_session
                                    uploaded_df["Target Panel Visibility"] = "Pending Approval"
                                    
                                    if "Uploaded File Type" not in uploaded_df.columns:
                                        uploaded_df["Uploaded File Type"] = p1_file_type
                                    
                                    cleaned_uploaded_df = uploaded_df[DEFAULT_COLUMNS].copy()
                                    cleaned_uploaded_df["Uploaded File Name"] = uploaded_file.name
                                    
                                    all_new_dfs.append(cleaned_uploaded_df)
                                    success_count += 1
                                
                                if success_count > 0:
                                    updated_stage_df = pd.concat(all_new_dfs, ignore_index=True)
                                    save_stage_data(updated_stage_df)
                                    st.session_state.uploader_key_counter += 1
                                    st.success(f"🎉 कुल {success_count} फ़ाइलें (CSV/XLSX) सफलतापूर्वक 'merge & approve panel' में भेज दी गई हैं!")
                                    st.balloons()
                                    st.rerun()
                            except Exception as e: 
                                st.error(f"फ़ाइल प्रोसेसिंग चक्र में तकनीकी त्रुटि आई: {e}")
                                
            # ➕ नया छात्र मैनुअल फॉर्म सब-सिस्टम
            elif entry_method == "➕ नया छात्र मैनुअल फॉर्म (Manual Form Entry)":
                with st.form(key="student_add_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        admission_year = st.selectbox("Admission Year *", options=st.session_state.p1_dropdown_schemas["academic_years"])
                        app_number = st.text_input("Application Number *")
                        abc_id = st.text_input("Student Abc Id")
                        s_name = st.text_input("Student Name *")
                        f_name = st.text_input("Father Name")
                        m_name = st.text_input("Mother Name")
                        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
                        dob = st.text_input("Date Of Birth (DD-MM-YYYY)")
                        category = st.selectbox("Category", ["General", "OBC", "SC", "ST"])
                        adm_category = st.selectbox("Admission Category", ["General", "OBC", "SC", "ST"])
                        degree = st.text_input("Degree")
                        branch = st.text_input("Branch")
                    with col2:
                        admission_session = st.selectbox("Admission Session *", options=st.session_state.p1_dropdown_schemas["academic_sessions"])
                        minor_sub = st.text_input("Minor Subjects")
                        vocational_sub = st.text_input("Vocational Subjects")
                        mdc_sub = st.text_input("MDC Subjects")
                        pw_ap_ce_sub = st.text_input("PW/Ap/CE Subjects")
                        mobile = st.text_input("Mobile Number")
                        email = st.text_input("Email")
                        address = st.text_area("Address", height=68)
                        enroll_no = st.text_input("Enrollment No")
                        fees_paid = st.text_input("Admssion & Enrollment Fees")
                        scholarship_name = st.text_input("Scholarship Name")
                        payment_date = st.text_input("Payment Date (DD-MM-YYYY)")
                    
                    st.markdown("<p style='color:gray;'>* चिन्ह वाले फ़ील्ड्स डेटाबेस ट्रैकिंग के लिए महत्वपूर्ण हैं।</p>", unsafe_allow_html=True)
                    submit_student = st.form_submit_button("Save Student Data Systematically", type="primary", use_container_width=True)
                    
                if submit_student:
                    if s_name.strip() == "" or app_number.strip() == "": 
                        st.warning("⚠️ Student Name और Application Number भरना अनिवार्य है।")
                    else:
                        new_row = {c: "" for c in DEFAULT_COLUMNS}
                        # 🟢 फिक्स: पहले यहाँ "Date Of Birth", "Email", "Enrollment No" जैसे गलत-केस/नाम
                        # वाली keys इस्तेमाल होती थीं, जो DEFAULT_COLUMNS की असली keys
                        # ("Date of Birth", "Email ID", "Enrollment No.") से मेल नहीं खाती थीं — इसलिए
                        # डेटा एक अलग (गलत) कॉलम में चला जाता था और असली कॉलम हमेशा खाली दिखता था।
                        # अब सही स्कीमा नामों का उपयोग किया गया है ताकि DOB, Email और Enrollment No
                        # हर जगह सही तरीके से दिखें।
                        new_row.update({
                            "Application Number": app_number, "Student Abc Id": abc_id, 
                            "Student Name": s_name, "Father Name": f_name, "Mother Name": m_name,                             "Gender": gender, "Date of Birth": dob, "Category": category, 
                            "Admission Category": adm_category, "Degree": degree, "Branch": branch, 
                            "Minor Subjects": minor_sub, "Vocational Subjects": vocational_sub, 
                            "MDC Subjects": mdc_sub, "PW/Ap/CE Subjects": pw_ap_ce_sub, 
                            "Mobile Number": mobile, "Email ID": email, "Address": address, 
                            "Enrollment No.": enroll_no, "Admssion & Enrollment Fees": fees_paid, 
                            "Scholarship Name": scholarship_name, "Payment Date": payment_date,
                            "Admission Year": admission_year, "Admission Session": admission_session,  
                            "Status": "Regular Student", "Current Year": "1", "Target Panel Visibility": "Pending Approval"
                        })
                        new_df = pd.DataFrame([new_row])
                        new_df["Uploaded File Name"] = "Manual Form Entry"
                        
                        # Route manual entries directly to merge stage room 
                        updated_stage_df = pd.concat([load_stage_data(), new_df], ignore_index=True)
                        save_stage_data(updated_stage_df)
                        st.success("🎉 Record successfully sent in merge & approve panel!")
                        st.rerun()

        # ----------------------------------------------------------------------
        # P2: PANEL ADMISSION MODULE (Displays Only Content Explicitly Approved for P2)
        # ----------------------------------------------------------------------
        elif current_panel_id == "P2":
            st.header(f"🎓 {get_panel_title('P2')} (Admission Control & Payment Tracker)")
            
            # 🔍 Isolated Firewall Query Filter Rule
            p2_authorized_db = live_db[live_db["Target Panel Visibility"] == "P2"].copy()
            
            if p2_authorized_db.empty: 
                st.warning("⚠️ डेटाबेस वर्तमान में खाली है या इस पैनल के लिए कोई अधिकृत स्वीकृत (Approved) डेटा उपलब्ध नहीं है।")
            else:
                # 🟢 Fix: "Student Abc Id" ko galti se "Student Abc ld" (typo) mein rename kar diya jaata tha,
                # jisse yeh column aage 'Student Abc Id' naam se dhoondhne par nahi milta tha aur khaali dikhta tha.
                # 🟢 फिक्स: पहले यहाँ "Application Number" को "Admission Application Number" में
                # rename कर दिया जाता था, जबकि दोनों DEFAULT_COLUMNS में अलग-अलग असली कॉलम हैं।
                # इससे rename + duplicate-column-drop के दौरान असली "Application Number" का डेटा
                # हमेशा के लिए खो जाता था और P2 में यह कॉलम खाली दिखता था। अब इसे हटा दिया गया है
                # ताकि "Application Number" अपना असली डेटा बनाए रखे।
                column_mapping_fixes = {
                    "Unique Id": "Unique ID",
                    "Date Of Birth": "Date of Birth", "Duretion": "Duration", 
                    "Email Id": "Email ID", "Year": "Current Year"
                }
                p2_authorized_db = p2_authorized_db.rename(columns=column_mapping_fixes)
                p2_authorized_db = p2_authorized_db.loc[:, ~p2_authorized_db.columns.duplicated()].copy()

                # सभी कॉलम के डेटा को साफ़ और स्ट्रिंग (String) में बदलें
                for c in p2_authorized_db.columns:
                    p2_authorized_db[c] = p2_authorized_db[c].astype(str).str.strip()

                # ==================================================================
                # 🎛️ Advanced Matrix Filters System
                # ==================================================================
                st.markdown('<div class="print-hide">', unsafe_allow_html=True)
                st.subheader("🔍 Advanced Matrix Filters System")
                
                col_p2_1, col_p2_2, col_p2_3, col_p2_4 = st.columns(4)
                
                with col_p2_1:
                    year_list = ["All Years"] + sorted([y for y in p2_authorized_db["Admission Year"].unique() if y and y.lower() != "nan"])
                    p2_filter_year = st.selectbox("1. Select Admission Year:", options=year_list, key="p2_scroll_filter_year_v18")
                
                temp_db_for_sub = p2_authorized_db.copy()
                if p2_filter_year != "All Years":
                    temp_db_for_sub = temp_db_for_sub[temp_db_for_sub["Admission Year"] == p2_filter_year]

                with col_p2_2:
                    subject_list = ["All Subjects"] + sorted([s for s in temp_db_for_sub["Subject"].unique() if s and s.lower() != "nan"])
                    p2_filter_subject = st.selectbox("2. Select Subject:", options=subject_list, key="p2_scroll_filter_subject_v18")
                
                with col_p2_3:
                    # 🟢 Fix: "Subject" ko yahan se hata diya gaya hai kyunki uska apna dedicated
                    # dropdown (2. Select Subject) upar hi maujood hai — dono jagah Subject rakhne se
                    # confusing double-filtering hoti thi. Ab "Subject" ki jagah is dropdown mein
                    # nahi dikhega (jab bhi "All Subjects" ho ya na ho, "Column Filter Target" hamesha
                    # baaki dusre columns hi dikhayega).
                    ignore_cols = ["Target Panel Visibility", "Uploaded File Name", "Uploaded File Type", "Subject"]
                    available_cols = [c for c in p2_authorized_db.columns if c not in ignore_cols]
                    p2_selected_col = st.selectbox("3. Select Column Filter Target:", options=available_cols, key="p2_scroll_filter_column_name_v18")
                
                dependent_db = p2_authorized_db.copy()
                if p2_filter_year != "All Years":
                    dependent_db = dependent_db[dependent_db["Admission Year"] == p2_filter_year]
                if p2_filter_subject != "All Subjects":
                    dependent_db = dependent_db[dependent_db["Subject"] == p2_filter_subject]

                with col_p2_4:
                    raw_vals = dependent_db[p2_selected_col].unique()
                    val_list = ["All Values"] + sorted([v for v in raw_vals if v and v.lower() != "nan"])
                    p2_selected_val = st.selectbox(f"4. Filter Value for '{p2_selected_col}':", options=val_list, key="p2_scroll_filter_value_data_v18")
                
                # Payment Date Range Filter
                st.markdown("---")
                if "p2_show_date_filter_section" not in st.session_state:
                    st.session_state.p2_show_date_filter_section = True
                hdr_dt_1, hdr_dt_2 = st.columns([6, 1])
                with hdr_dt_1:
                    st.subheader("📆 Filter Records By Payment Date Range")
                with hdr_dt_2:
                    st.write("")
                    if st.button("🙈 Hide" if st.session_state.p2_show_date_filter_section else "👁️ Unhide",
                                 key="p2_toggle_date_filter_section", use_container_width=True):
                        st.session_state.p2_show_date_filter_section = not st.session_state.p2_show_date_filter_section

                start_date = pd.to_datetime("2024-01-01")
                end_date = pd.to_datetime("2026-12-31")

                if st.session_state.p2_show_date_filter_section:
                    use_date_filter = st.checkbox("Enable Payment Date Range Filter (तारीख सीमा फ़िल्टर सक्रिय करें)", value=False, key="p2_enable_date_filter_secure_v18")

                    if use_date_filter:
                        col_dt1, col_dt2 = st.columns(2)
                        with col_dt1:
                            start_date = st.date_input("कब से (From Date):", value=pd.to_datetime("2024-01-01"), key="p2_start_date_secure_v18")
                        with col_dt2:
                            end_date = st.date_input("कब तक (To Date):", value=pd.to_datetime("2026-12-31"), key="p2_end_date_secure_v18")
                else:
                    st.caption("🙈 यह सेक्शन फ़िलहाल छुपा हुआ है। (Unhide करने पर पिछली सेटिंग बनी रहेगी)")

                use_date_filter = st.session_state.get("p2_enable_date_filter_secure_v18", False)
                start_date = st.session_state.get("p2_start_date_secure_v18", pd.to_datetime("2024-01-01"))
                end_date = st.session_state.get("p2_end_date_secure_v18", pd.to_datetime("2026-12-31"))
                
                st.markdown('</div>', unsafe_allow_html=True)

                # ==================================================================
                # ⚡ Filters Execution Engine
                # ==================================================================
                admission_display_db = p2_authorized_db.copy()
                
                if p2_filter_year != "All Years":
                    admission_display_db = admission_display_db[admission_display_db["Admission Year"] == p2_filter_year]
                
                if p2_filter_subject != "All Subjects":
                    admission_display_db = admission_display_db[admission_display_db["Subject"] == p2_filter_subject]
                
                if p2_selected_val != "All Values":
                    admission_display_db = admission_display_db[admission_display_db[p2_selected_col] == p2_selected_val]

                if use_date_filter:
                    try:
                        admission_display_db["_parsed_date"] = pd.to_datetime(admission_display_db["Payment Date"], dayfirst=True, errors="coerce")
                        admission_display_db = admission_display_db[
                            (admission_display_db["_parsed_date"] >= pd.to_datetime(start_date)) & 
                            (admission_display_db["_parsed_date"] <= pd.to_datetime(end_date))
                        ]
                        admission_display_db = admission_display_db.drop(columns=["_parsed_date"], errors="ignore")
                    except Exception as date_err:
                        st.error(f"तिथि फ़ॉर्मेट मिलान में तकनीकी त्रुटि: {date_err}")

                # ==================================================================
                # ✍️ Print Header Text Boxes Customizer
                # ==================================================================
                st.markdown("---")
                if "p2_show_header_customizer_section" not in st.session_state:
                    st.session_state.p2_show_header_customizer_section = True
                hdr_pc_1, hdr_pc_2 = st.columns([6, 1])
                with hdr_pc_1:
                    st.subheader("✍️ प्रिंट हेडर कस्टमाइज़र (Print Header Text Customizer)")
                with hdr_pc_2:
                    st.write("")
                    if st.button("🙈 Hide" if st.session_state.p2_show_header_customizer_section else "👁️ Unhide",
                                 key="p2_toggle_header_customizer_section", use_container_width=True):
                        st.session_state.p2_show_header_customizer_section = not st.session_state.p2_show_header_customizer_section

                # 🔄 Header 3 & Header 4 ऑटो-सिंक इंजन — जब भी ऊपर "Advanced Matrix Filters System" में
                # Year/Subject (बॉक्स 3 के लिए) या Column Filter Target/Filter Value (बॉक्स 4 के लिए) बदलें,
                # ये टेक्स्ट बॉक्स अपने आप नई चुनी हुई वैल्यू के हिसाब से रीफ़्रेश हो जाएंगे।
                # (पहले सिर्फ पहली बार वाली default value सेट होती थी, बाद में year/subject बदलने पर भी
                # बॉक्स पुरानी वैल्यू पर ही अटका रहता था — यही bug अब ठीक कर दिया गया है)
                default_header_3 = f"Session: {p2_filter_year} | Subject: {p2_filter_subject}"
                default_header_4 = f"{p2_selected_col}: {p2_selected_val}" if p2_selected_val != "All Values" else ""

                _h3_track_key = "_p2_h3_last_filters"
                if st.session_state.get(_h3_track_key) != (p2_filter_year, p2_filter_subject):
                    st.session_state["p2_custom_head_line_3_final_fixed"] = default_header_3
                    st.session_state[_h3_track_key] = (p2_filter_year, p2_filter_subject)

                _h4_track_key = "_p2_h4_last_filters"
                if st.session_state.get(_h4_track_key) != (p2_selected_col, p2_selected_val):
                    st.session_state["p2_custom_head_line_4_final_fixed"] = default_header_4
                    st.session_state[_h4_track_key] = (p2_selected_col, p2_selected_val)

                if st.session_state.p2_show_header_customizer_section:
                    st.caption("नीचे दिए गए बॉक्स में आप जो भी लिखेंगे, वह प्रिंट रिपोर्ट के पहले पेज पर सबसे ऊपर दिखाई देगा। "
                                "बॉक्स 3 और 4 अपने आप ऊपर चुने गए Year/Subject और Column Filter Target/Filter Value के हिसाब से अपडेट होते हैं "
                                "(बॉक्स 4 सिर्फ तभी दिखेगा जब 'Filter Value for...' में 'All Values' के अलावा कोई खास वैल्यू चुनी गई हो — जरूरत न हो तो यह खाली/print में गायब रहेगा)।")

                    col_tb1, col_tb2, col_tb3, col_tb4 = st.columns(4)
                    with col_tb1:
                        custom_header_1 = st.text_input("1. हेडर लाइन 1 (उदा. कॉलेज का नाम):", value="GOVT. K.R.G. POST-GRADUATE AUTONOMOUS COLLEGE, GWALIOR (M.P.)", key="p2_custom_head_line_1_final_fixed")
                    with col_tb2:
                        custom_header_2 = st.text_input("2. हेडर लाइन 2 (उदा. रिपोर्ट का प्रकार):", value="ADMISSION CONTROL & FEES PAYMENT REPORT SHEET", key="p2_custom_head_line_2_final_fixed")
                    with col_tb3:
                        custom_header_3 = st.text_input("3. हेडर लाइन 3 (उदा. आदेश संख्या या कोई विशेष नोट):", value=default_header_3, key="p2_custom_head_line_3_final_fixed")
                    with col_tb4:
                        custom_header_4 = st.text_input(f"4. Select Column Filter Target: (Filter Value for '{p2_selected_col}'):", value=default_header_4, key="p2_custom_head_line_4_final_fixed")
                else:
                    st.caption("🙈 यह सेक्शन फ़िलहाल छुपा हुआ है। (Unhide करने पर पिछली सेटिंग बनी रहेगी)")

                custom_header_1 = st.session_state.get("p2_custom_head_line_1_final_fixed", "GOVT. K.R.G. POST-GRADUATE AUTONOMOUS COLLEGE, GWALIOR (M.P.)")
                custom_header_2 = st.session_state.get("p2_custom_head_line_2_final_fixed", "ADMISSION CONTROL & FEES PAYMENT REPORT SHEET")
                custom_header_3 = st.session_state.get("p2_custom_head_line_3_final_fixed", default_header_3)
                custom_header_4 = st.session_state.get("p2_custom_head_line_4_final_fixed", default_header_4)
                
                # ==================================================================
                # 👁️ NEW: Multi-Select Column Filter (कॉलम यहाँ से सेलेक्ट करें)
                # ==================================================================
                st.markdown("---")
                if "p2_show_columns_section" not in st.session_state:
                    st.session_state.p2_show_columns_section = True
                hdr_cs_1, hdr_cs_2 = st.columns([6, 1])
                with hdr_cs_1:
                    st.subheader("👁️ Select Columns to Display & Print")
                with hdr_cs_2:
                    st.write("")
                    if st.button("🙈 Hide" if st.session_state.p2_show_columns_section else "👁️ Unhide",
                                 key="p2_toggle_columns_section", use_container_width=True):
                        st.session_state.p2_show_columns_section = not st.session_state.p2_show_columns_section

                # 🟢 फिक्स: यहाँ पहले कॉलम नाम असली डेटा कॉलम्स से मेल नहीं खाते थे
                # (जैसे "Date Of Birth" vs असली कॉलम "Date of Birth", "Email" vs "Email ID",
                # "Enrollment No" vs "Enrollment No.") — इसी वजह से DOB, Email और Enrollment No
                # हमेशा खाली दिखते थे। अब नाम बिल्कुल सही स्कीमा फॉर्मेट में फिक्स किए गए हैं।
                # 🟢 P2 की पूरी column list (आपने जो सटीक 29 कॉलम बताए थे, वही यहाँ लगाए गए हैं —
                # "SRNo" ऊपर अलग से हर हाल में S. No. के रूप में जुड़ता है इसलिए इस लिस्ट में नहीं है)
                all_possible_p2_cols = [
                    "Student Name", "Gender", "Enrollment No.", "Father Name", "Mother Name", "Address",
                    "Eligibility Name", "Degree", "Branch", "Minor Subjects", "Vocational Subjects",
                    "MDC Subjects", "PW/Ap/CE Subjects", "Date of Birth", "Application Number",
                    "Mobile Number", "Email ID", "Category", "Admission Category", "Merit (%)",
                    "Obtain (%)", "Bonus (%)", "Weightage (%)", "Class", "Ncc Type", "IsDisabled",
                    "Final Status", "Scholarship Name", "Subject Selection Status"
                ]

                if st.session_state.p2_show_columns_section:
                    # ड्रॉपडाउन लिस्ट जो स्क्रीन और प्रिंट दोनों को कंट्रोल करेगी
                    chosen_render_cols = st.multiselect(
                        "रिपोर्ट में देखने के लिए आवश्यक कॉलम्स चुनें:",
                        options=all_possible_p2_cols,
                        default=all_possible_p2_cols, # डिफ़ॉल्ट रूप से सभी सेलेक्ट रहेंगे
                        key="p2_columns_multiselect_dropdown_v20"
                    )

                    # 🖨️ नया फ़ीचर: प्रिंट ओरिएंटेशन चुनने का विकल्प (Portrait / Landscape)
                    print_orientation = st.selectbox(
                        "🖨️ प्रिंट पेज का लेआउट चुनें (Choose Print Orientation):",
                        options=["Portrait (खड़ा पेज - कम कॉलम्स के लिए उत्तम)", "Landscape (आड़ा पेज - अधिक कॉलम्स के लिए उत्तम)"],
                        index=1, # डिफ़ॉल्ट रूप से Landscape सेट रहेगा
                        key="p2_print_orientation_selector"
                    )
                else:
                    st.caption("🙈 यह सेक्शन फ़िलहाल छुपा हुआ है। (Unhide करने पर पिछली सेटिंग बनी रहेगी)")

                chosen_render_cols = st.session_state.get("p2_columns_multiselect_dropdown_v20", all_possible_p2_cols)
                print_orientation = st.session_state.get(
                    "p2_print_orientation_selector",
                    "Landscape (आड़ा पेज - अधिक कॉलम्स के लिए उत्तम)"
                )

                # सीएसएस के लिए वैल्यू सेट करना
                orientation_css = "portrait" if "Portrait" in print_orientation else "landscape"

                # सुरक्षा नियम: यदि सब डिलीट कर दें तो कम से कम नाम और नंबर जरूर दिखे
                if not chosen_render_cols:
                    chosen_render_cols = ["Application Number", "Student Name"]

                # 🔀 List Order Selector — P10 जैसा ही Sort Order सिस्टम अब P2 में भी
                p2_sort_order_choice = st.selectbox(
                    "🔀 लिस्ट किस क्रम में प्रिंट करें (Sort Order):",
                    options=[
                        "डिफ़ॉल्ट क्रम (जैसा डेटा है)",
                        "Student Name (अल्फाबेटिक A-Z क्रम में)",
                        "Subject → Student Name (पहले Subject, फिर नाम अनुसार A-Z)"
                    ],
                    key="p2_sort_order_choice"
                )
                if p2_sort_order_choice.startswith("Subject"):
                    # 🔤 पहले Subject के अल्फाबेटिक क्रम में, फिर उसी Subject के अंदर Student Name A-Z
                    admission_display_db["_sort_key_1"] = admission_display_db.get("Subject", "").astype(str).str.strip().str.upper()
                    admission_display_db["_sort_key_2"] = admission_display_db.get("Student Name", "").astype(str).str.strip().str.upper()
                    admission_display_db = admission_display_db.sort_values(
                        by=["_sort_key_1", "_sort_key_2"], ascending=[True, True]
                    ).drop(columns=["_sort_key_1", "_sort_key_2"]).reset_index(drop=True)
                elif p2_sort_order_choice.startswith("Student Name"):
                    # 🔤 Alphabetical (A-Z) क्रम — Student Name के आधार पर
                    admission_display_db["_sort_key"] = admission_display_db.get("Student Name", "").astype(str).str.strip().str.upper()
                    admission_display_db = admission_display_db.sort_values(
                        by=["_sort_key"], ascending=[True]
                    ).drop(columns=["_sort_key"]).reset_index(drop=True)
                # "डिफ़ॉल्ट क्रम" चुनने पर कोई sort नहीं होगा — डेटा जैसा है वैसा ही क्रम रहेगा

                st.markdown("---")
                
                # ==================================================================
                # 📊 Data Grid Overview (स्क्रीन पर दिखने वाली एकमात्र मुख्य तालिका)
                # ==================================================================
                # 🟢 फिक्स: पहले यहाँ "Application Number" को "Admission Application Number" के
                # डेटा से जबरन ओवरराइट कर दिया जाता था — अब हटा दिया गया है ताकि "Application Number"
                # अपना असली डेटा दिखाए (P2 की column list में सिर्फ यही field चाहिए, "Admission
                # Application Number" नहीं)।

                for col in chosen_render_cols:
                    if col not in admission_display_db.columns:
                        if col == "Admission & Enrollment Fees" and "Admssion & Enrollment Fees" in admission_display_db.columns:
                            admission_display_db["Admission & Enrollment Fees"] = admission_display_db["Admssion & Enrollment Fees"]
                        else:
                            admission_display_db[col] = ""
                        
                final_p2_render = admission_display_db[chosen_render_cols].copy()
                
                # 🟢 पुराना रीनेम कोड हटाकर इसे पूरी तरह साफ़ और सुरक्षित किया गया
                final_p2_render = final_p2_render.loc[:, ~final_p2_render.columns.duplicated()].copy()
                
                if not final_p2_render.empty:
                    final_p2_render.insert(0, "S. No.", range(1, len(final_p2_render) + 1))
                
                st.write(f"ग्रिड में प्रदर्शित कुल छात्र रिकॉर्ड संख्या: **{len(final_p2_render)}**")
                
                # 🌟 स्क्रीन की एकमात्र मुख्य ग्रिड तालिका
                st.dataframe(final_p2_render, use_container_width=True, hide_index=True)

                # ==================================================================
                # 🖨️ Clean Variable-Based Iframe Print Engine (Dynamic Layout Fix)
                # ==================================================================
                if not final_p2_render.empty:
                    columns_list = list(final_p2_render.columns)
                    records_list = final_p2_render.to_dict(orient="records")
                    
                    headers_html = "".join([f"<th style='border:1px solid #111; padding:6px; background:#f2f2f2; font-weight:bold; text-align:center;'>{col}</th>" for col in columns_list])
                    
                    rows_html = ""
                    for row in records_list:
                        rows_html += "<tr>"
                        for col in columns_list:
                            val = str(row.get(col, "")).replace("`", "'").replace("\n", " ")
                            rows_html += f"<td style='border:1px solid #111; padding:5px; text-align:left;'>{val}</td>"
                        rows_html += "</tr>"
                    
                    clean_table_html = f"""
                    <html>
                    <head>
                        <style>
                            @page {{ size: A4 {orientation_css}; margin: 8mm; }}
                            body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; color: #000; }}
                            .custom-print-header {{
                                width: 100%; border: 2px solid #1465de; background-color: #f4f8ff;
                                padding: 15px; margin-bottom: 20px; border-radius: 6px;
                                box-sizing: border-box; text-align: center;
                            }}
                            .h-line-1 {{ font-size: 16px; font-weight: bold; color: #1465de; margin-bottom: 5px; }}
                            .h-line-2 {{ font-size: 14px; font-weight: bold; color: #333; margin-bottom: 5px; }}
                            .h-line-3 {{ font-size: 12px; font-style: italic; color: #555; }}
                            .h-line-4 {{ font-size: 12px; font-style: italic; color: #1465de; margin-top: 3px; }}
                            table {{ width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 10px; }}
                        </style>
                    </head>
                    <body>
                        <div class="custom-print-header">
                            <div class="h-line-1">{custom_header_1}</div>
                            <div class="h-line-2">{custom_header_2}</div>
                            <div class="h-line-3">{custom_header_3}</div>
                            {f'<div class="h-line-4">{custom_header_4}</div>' if custom_header_4 and custom_header_4.strip() else ''}
                        </div>
                        <table>
                            <thead><tr>{headers_html}</tr></thead>
                            <tbody>{rows_html}</tbody>
                        </table>
                    </body>
                    </html>
                    """
                    
                    safe_html_string = clean_table_html.replace("\\", "\\\\").replace("`", "'").replace("\n", " ").replace("\r", "")
                    
                    # 🟢 यहाँ इंडेंटेशन फिक्स किया गया है (16 Spaces / 4 Tabs)
                    st.markdown('<div class="print-hide" style="margin-top: 20px;"></div>', unsafe_allow_html=True)
                    
                    # प्रिंट बटन जो सीधे बैकएंड से कनेक्टेड है
                    components.html(
                        f"""
                        <html>
                        <body>
                            <script>
                            function printAdmissionList() {{
                                var iframe = window.parent.document.createElement('iframe');
                                iframe.style.position = 'fixed'; iframe.style.right = '0'; iframe.style.bottom = '0';
                                iframe.style.width = '0'; iframe.style.height = '0'; iframe.style.border = '0';
                                window.parent.document.body.appendChild(iframe);
                                
                                var doc = iframe.contentWindow.document;
                                doc.open(); doc.write(`{safe_html_string}`); doc.close();
                                iframe.contentWindow.focus(); iframe.contentWindow.print();
                                
                                setTimeout(function() {{ window.parent.document.body.removeChild(iframe); }}, 1000);
                            }}
                            </script>
                            <button onclick="printAdmissionList()" style="
                                width: 100%; background-color: #1465de; color: white; padding: 14px; 
                                border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 16px;
                                font-family: sans-serif; box-shadow: 0 4px 6px rgba(20, 101, 222, 0.2);">
                                🖨️ Click Here to Print Admission & Payment Report Sheet
                            </button>
                        </body>
                        </html>
                        """,
                        height=70
                    )

        # ----------------------------------------------------------------------
        # P3: PANEL UNIQUE ID MODULE (Student Unique ID Mapping Engine)
        # ----------------------------------------------------------------------
        elif current_panel_id == "P3":
            st.header(f"💰 {get_panel_title('P3')} (Portal & Scholarship Tracker)")
            
            # Ensure the tracking fallback status column exists inside the master dataframe array
            if "Scholarship Status" not in live_db.columns: 
                live_db["Scholarship Status"] = "Not Applied"
                
            # 🔍 Isolated Firewall Query Filter Rule: Only fetch records explicitly approved for P3
            p3_authorized_db = live_db[live_db["Target Panel Visibility"] == "P3"].copy()
            
            if p3_authorized_db.empty:
                st.warning("⚠️ इस पैनल के लिए कोई अधिकृत स्वीकृत (Approved) डेटा उपलब्ध नहीं है। कृपया पहले P6 (Merge Panel) से डेटा को इस पैनल पर असाइन कर अप्रूव करें।")
            else:
                # 🟢 सही किया गया कोड
                st.markdown(
                    '<div style="background-color: #f4fbf7; border-left: 5px solid #2e7d32; padding: 10px; border-radius: 4px; margin-bottom: 15px;">'
                    '📌 <b>ऑपरेटर निर्देश:</b> इस ग्रिड में छात्रवृत्ति प्रोग्रेस (Scholarship Status) से संबंधित डेटा प्रदर्शित है। सुरक्षा नियमों के अनुसार केवल सुपर एडमिन ही इसमें बदलाव कर सकता है।'
                    '</div>', 
                    unsafe_allow_html=True
                )
                
                # Normalise alternate column structural headers to match baseline fields smoothly
                column_mapping_fixes = {
                    "Unique Id": "Unique ID", "Student Abc Id": "Unique ID", 
                    "Date Of Birth": "Date of Birth", "Duretion": "Duration", 
                    "Email Id": "Email ID", "Year": "Current Year",
                    "Application Number": "Admission Application Number"
                }
                p3_authorized_db = p3_authorized_db.rename(columns=column_mapping_fixes)

                # Isolate unique list categories to build search shorting options cleanly
                available_categories = ["All"] + sorted(list(set(p3_authorized_db["Category"].dropna().astype(str).str.strip())))
                selected_category = st.selectbox("Category (वर्ग) फ़िल्टर चुनें:", options=available_categories, key="p3_category_filter_secure_select_box")
                
                # Apply row shorting filters based on category criteria selection
                filtered_scholarship = p3_authorized_db.copy()
                if selected_category != "All": 
                    filtered_scholarship = filtered_scholarship[filtered_scholarship["Category"].str.strip() == selected_category]
                
                # Standardized 22 columns layout matrix + 1 interactive cell for operations comfort
                scholarship_fixed_cols = [
                    "Admission Application Number", "Scholarship Status", "Scholarship Name", "Unique ID", "Roll No.", "Enrollment No.",
                    "Student Name", "Father Name", "Admission Year", "Admission Session", "Eligibility Name", "Admission Date", 
                    "Application Enrollment No.", "Mother Name", "Date of Birth", "Category", "Subject", "Duration", 
                    "Mobile Number", "Email ID", "Address", "Status", "Current Year", "Payment Date"
                ]
                
                # Pre-populate missing structural columns with placeholders to bypass layout crashes
                for col in scholarship_fixed_cols:
                    if col not in filtered_scholarship.columns:
                        filtered_scholarship[col] = ""
                
                render_df = filtered_scholarship[scholarship_fixed_cols].copy()
                render_df.insert(0, "S. No.", range(1, len(render_df) + 1))
                
                st.write(f"ग्रिड में प्रदर्शित कुल सक्रिय रिकॉर्ड संख्या (Active Matrix Profiles): **{len(render_df)}**")
                
                # 🔐 Access Restriction Interface (Security Gateway)
                if role == "full_admin" or role == "p3_role":
                    # Admins and designated operators can interactively modify the Scholarship Status field
                    disabled_cols = [c for c in render_df.columns if c != "Scholarship Status"]
                    st.info("🔓 **एडमिन कंट्रोल मोड:** आपके पास छात्रवृत्ति ट्रैकिंग मैट्रिक्स (Scholarship Status) एडिट और सिंक करने का पूर्ण अधिकार है।")
                else:
                    # Regular viewers get a protected comprehensive spreadsheet canvas layout
                    disabled_cols = [c for c in render_df.columns]
                    st.warning("🔒 **रीड-ओनली मोड:** सुरक्षा कारणों से आपके पास इस लिस्ट में छात्रवृत्ति स्थिति बदलने का अधिकार नहीं है।")
                
                # Render interactive workspace spreadsheet data editor with custom selection menus
                edited_scholarship_df = st.data_editor(
                    render_df, 
                    use_container_width=True, 
                    disabled=disabled_cols, 
                    column_config={
                        "Scholarship Status": st.column_config.SelectboxColumn(
                            "Scholarship Status", 
                            options=["Not Applied", "Applied", "Sanctioned", "Disbursed", "Rejected"],
                            required=True,
                            help="छात्रवृत्ति आवेदन की वर्तमान स्थिति चुनें"
                        )
                    }, 
                    key="scholarship_live_editor_grid_p6_secure_engine", 
                    hide_index=True
                )
                
                # Commit updates engine to synchronize state modifications with core live datasets
                if role == "full_admin" or role == "p3_role":
                    if st.button("Save & Sync Scholarship Matrix", type="primary", use_container_width=True, key="p3_save_btn_secure_tracker_engine"):
                        try:
                            clean_edited = edited_scholarship_df.drop(columns=["S. No."], errors="ignore")
                            scholarship_sync_counter = 0
                            
                            for _, row_edit in clean_edited.iterrows():
                                app_num = str(row_edit["Admission Application Number"]).strip()
                                
                                # Locating matching data indexes using internal primary Application Key references
                                idx_matches = live_db[live_db["Application Number"].astype(str).str.strip() == app_num].index
                                
                                if not idx_matches.empty:
                                    for match_idx in idx_matches:
                                        live_db.at[match_idx, "Scholarship Status"] = str(row_edit["Scholarship Status"]).strip()
                                        scholarship_sync_counter += 1
                            
                            # Save modifications permanently to the CSV file repository
                            save_live_data(live_db)
                            st.success(f"🎉 सफलता! कुल {scholarship_sync_counter} छात्र रिकॉर्ड्स का छात्रवृत्ति स्टेटस डेटा मुख्य डेटाबेस (Live CSV) में सुरक्षित सिंक हो गया है!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"डेटा सिंक्रोनाइज़ेशन चक्र में तकनीकी समस्या आई: {e}")

        # ----------------------------------------------------------------------
        # P4: PANEL CCE DESK (Strict 22-Cols Selection, Map & Custom Foil System)
        # ----------------------------------------------------------------------
        elif current_panel_id == "P4":
            st.header(f"📋 {get_panel_title('P4')} (Complete CCE Management & Foil Desk)")
            
            # सुनिश्चित करें कि मार्क्स वाले कॉलम डेटाबेस स्कीमा में मौजूद हों
            for f in ["CCE Marks Obtained", "CCE Attendance Status"]:
                if f not in live_db.columns: 
                    live_db[f] = ""
            
            p4_authorized_db = live_db.copy()

            if p4_authorized_db.empty: 
                st.warning("⚠️ इस पैनल के लिए कोई अधिकृत स्वीकृत (Approved) डेटा उपलब्ध नहीं है।")
            else:
                # ------------------------------------------------------------------
                # भाग 1: 22-कॉलम छात्र सूची और लाइव असेसमेंट एंट्री ग्रिड
                # ------------------------------------------------------------------
                st.markdown('<div class="print-hide">', unsafe_allow_html=True)
                st.subheader("📝 1. CCE Data Entry Desk & 22-Columns Student List")
                
                st.markdown(
                    '<div style="background-color: #f1f8e9; border-left: 5px solid #558b2f; padding: 10px; border-radius: 4px; margin-bottom: 15px;">'
                    '📌 <b>डेटा एंट्री निर्देश:</b> नीचे दी गयी तालिका में छात्र के नाम के आगे सीधे <b>CCE Marks Obtained</b> और <b>CCE Attendance Status</b> भरें। बदलाव करने के बाद <b>Save Grid Changes</b> बटन को ज़रूर दबाएं।'
                    '</div>', 
                    unsafe_allow_html=True
                )
                st.markdown('</div>', unsafe_allow_html=True)
                
                # आपके द्वारा मांगे गए सटीक 22 कॉलम का फ़्रेमवर्क
                cce_requested_cols = [
                    "Admission Year", "Admission Session", "Eligibility Name", "Admission Application Number", 
                    "Admission Date", "Unique ID", "Roll No.", "Application Enrollment No.", "Enrollment No.", 
                    "Student Name", "Father Name", "Mother Name", "Date of Birth", "Category", "Subject", 
                    "Duration", "Mobile Number", "Email ID", "Address", "Current Year", "Status",
                    "CCE Marks Obtained", "CCE Attendance Status"
                ]

                # स्पेलिंग्स और विसंगतियों को ठीक करने के लिए ट्रांसलेशन मैप
                column_mapping_fixes = {
                    "Unique Id": "Unique ID", "Student Abc Id": "Unique ID", "Unique ID": "Unique ID",
                    "Date Of Birth": "Date of Birth", "Date of Birth": "Date of Birth",
                    "Duretion": "Duration", "Duration": "Duration",
                    "Email Id": "Email ID", "Email ID": "Email ID", 
                    "Year": "Current Year", "Current Year": "Current Year",
                    "Application Number": "Admission Application Number", "Admission Application Number": "Admission Application Number",
                    "Enrollment No": "Enrollment No.", "Enrollment No.": "Enrollment No."
                }
                
                filtered_cce = p4_authorized_db.copy()
                filtered_cce = filtered_cce.rename(columns=column_mapping_fixes)

                if "Application Number" in filtered_cce.columns and "Admission Application Number" not in filtered_cce.columns:
                    filtered_cce["Admission Application Number"] = filtered_cce["Application Number"]
                if "Year" in filtered_cce.columns and "Current Year" not in filtered_cce.columns:
                    filtered_cce["Current Year"] = filtered_cce["Year"]

                for col in cce_requested_cols:
                    if col not in filtered_cce.columns: 
                        filtered_cce[col] = ""
                
                # केवल वही 22 कॉलम छाँटें
                render_df = filtered_cce[cce_requested_cols].copy()
                render_df = render_df.loc[:, ~render_df.columns.duplicated()].copy()
                
                # डिस्प्ले रीनेम मैप
                display_rename_map = {
                    "Unique ID": "Unique Id",
                    "Email ID": "Email Id",
                    "Duration": "Duretion",
                    "Current Year": "Year"
                }
                render_df = render_df.rename(columns=display_rename_map)
                
                if "S. No." in render_df.columns: 
                    render_df = render_df.drop(columns=["S. No."])
                render_df.insert(0, "S. No.", range(1, len(render_df) + 1))
                
                # CCE लाइव डेटा एडिटर ग्रिड
                st.markdown('<div class="print-hide">', unsafe_allow_html=True)
                if role in ["full_admin", "p4_role"]:
                    disabled_cols = [c for c in render_df.columns if c not in ["CCE Marks Obtained", "CCE Attendance Status"]]
                    st.info("🔓 **डेटा एंट्री मोड एक्टिव:** आप CCE Marks और Attendance Status बदल सकते हैं।")
                else:
                    disabled_cols = [c for c in render_df.columns]
                    st.warning("🔒 **रीड-ओनली मोड:** आपके पास बदलाव का अधिकार नहीं है।")
                    
                edited_cce = st.data_editor(
                    render_df, 
                    use_container_width=True, 
                    disabled=disabled_cols, 
                    column_config={
                        "CCE Marks Obtained": st.column_config.TextColumn("CCE Marks (Max 20)"),
                        "CCE Attendance Status": st.column_config.SelectboxColumn("Attendance Status", options=["Present", "Absent", "Detained"], required=True)
                    }, 
                    key="cce_live_entry_grid_p7_desk_final", 
                    hide_index=True
                )
                
                if role in ["full_admin", "p4_role"]:
                    if st.button("💾 Save Grid Changes to Master Database", type="primary", use_container_width=True, key="p4_save_grid_btn"):
                        try:
                            clean_edited = edited_cce.drop(columns=["S. No."], errors="ignore")
                            cce_sync_counter = 0
                            for _, r_edit in clean_edited.iterrows():
                                app_num = str(r_edit["Admission Application Number"]).strip()
                                idx_matches = pd.Index([])
                                if "Application Number" in live_db.columns:
                                    idx_matches = live_db[live_db["Application Number"].astype(str).str.strip() == app_num].index
                                if idx_matches.empty and "Admission Application Number" in live_db.columns:
                                    idx_matches = live_db[live_db["Admission Application Number"].astype(str).str.strip() == app_num].index
                                
                                if not idx_matches.empty:
                                    for match_idx in idx_matches:
                                        live_db.at[match_idx, "CCE Marks Obtained"] = str(r_edit["CCE Marks Obtained"]).strip()
                                        live_db.at[match_idx, "CCE Attendance Status"] = str(r_edit["CCE Attendance Status"]).strip()
                                        cce_sync_counter += 1
                            save_live_data(live_db)
                            st.success(f"🎉 सफलता! कुल {cce_sync_counter} छात्रों के CCE मार्क्स सुरक्षित सेव हो गए हैं!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"डेटाबेस सिंक चक्र में तकनीकी समस्या: {e}")
                st.markdown('</div>', unsafe_allow_html=True)

                # ----------------------------------------------------------------------
                # भाग 2: फ़ाइल फ़ॉर्मेट अपलोड सिस्टम (Admission Format / Fee Format)
                # ----------------------------------------------------------------------
                st.markdown("---")
                st.markdown('<div class="print-hide">', unsafe_allow_html=True)
                st.subheader("📄 2. Upload Data by File Format Type")

                file_format_type = st.selectbox(
                    "📄 Select File Format Type:",
                    options=[
                        "1. Upload Admission Format",
                        "2. Upload Fee Format"
                    ],
                    key="p4_file_format_type_selector"
                )

                # ==================================================================
                # ✍️ Print Header Text Boxes Customizer (P2 जैसा ही सिस्टम, अब P4 के
                # दोनों File Format सेक्शन — Admission Format और Fee Format — के लिए भी)
                # ==================================================================
                st.markdown("---")
                if "p4_show_header_customizer_section" not in st.session_state:
                    st.session_state.p4_show_header_customizer_section = True
                hdr_p4_1, hdr_p4_2 = st.columns([6, 1])
                with hdr_p4_1:
                    st.subheader("✍️ प्रिंट हेडर कस्टमाइज़र (Print Header Text Customizer)")
                with hdr_p4_2:
                    st.write("")
                    if st.button("🙈 Hide" if st.session_state.p4_show_header_customizer_section else "👁️ Unhide",
                                 key="p4_toggle_header_customizer_section", use_container_width=True):
                        st.session_state.p4_show_header_customizer_section = not st.session_state.p4_show_header_customizer_section

                # 🔄 Header 3 ऑटो-सिंक — जब भी ऊपर "Select File Format Type" बदलेगा,
                # बॉक्स 3 अपने आप उसी फॉर्मेट के नाम से रीफ़्रेश हो जाएगा (P2 के Year/Subject
                # ऑटो-सिंक जैसा ही तरीका, बस यहाँ ट्रिगर File Format Type है)
                default_header_2 = "ADMISSION FORMAT REPORT SHEET" if file_format_type.startswith("1.") else "FEE FORMAT REPORT SHEET"
                default_header_3 = f"Format: {file_format_type}"

                _p4h2_track_key = "_p4_h2_last_format"
                if st.session_state.get(_p4h2_track_key) != file_format_type:
                    st.session_state["p4_custom_head_line_2_final_fixed"] = default_header_2
                    st.session_state["p4_custom_head_line_3_final_fixed"] = default_header_3
                    st.session_state[_p4h2_track_key] = file_format_type

                if st.session_state.p4_show_header_customizer_section:
                    st.caption("नीचे दिए गए बॉक्स में आप जो भी लिखेंगे, वह Admission/Fee Format की प्रिंट रिपोर्ट के पहले पेज पर सबसे ऊपर दिखाई देगा। "
                                "बॉक्स 2 और 3 File Format Type बदलने पर अपने आप अपडेट हो जाते हैं — चाहें तो इन्हें खुद भी बदल सकते हैं।")

                    col_p4tb1, col_p4tb2, col_p4tb3, col_p4tb4 = st.columns(4)
                    with col_p4tb1:
                        custom_header_1 = st.text_input("1. हेडर लाइन 1 (उदा. कॉलेज का नाम):", value="GOVT. K.R.G. POST-GRADUATE AUTONOMOUS COLLEGE, GWALIOR (M.P.)", key="p4_custom_head_line_1_final_fixed")
                    with col_p4tb2:
                        custom_header_2 = st.text_input("2. हेडर लाइन 2 (उदा. रिपोर्ट का प्रकार):", value=default_header_2, key="p4_custom_head_line_2_final_fixed")
                    with col_p4tb3:
                        custom_header_3 = st.text_input("3. हेडर लाइन 3 (उदा. आदेश संख्या या कोई विशेष नोट):", value=default_header_3, key="p4_custom_head_line_3_final_fixed")
                    with col_p4tb4:
                        custom_header_4 = st.text_input("4. हेडर लाइन 4 (वैकल्पिक — कोई अतिरिक्त नोट):", value="", key="p4_custom_head_line_4_final_fixed")
                else:
                    st.caption("🙈 यह सेक्शन फ़िलहाल छुपा हुआ है। (Unhide करने पर पिछली सेटिंग बनी रहेगी)")

                custom_header_1 = st.session_state.get("p4_custom_head_line_1_final_fixed", "GOVT. K.R.G. POST-GRADUATE AUTONOMOUS COLLEGE, GWALIOR (M.P.)")
                custom_header_2 = st.session_state.get("p4_custom_head_line_2_final_fixed", default_header_2)
                custom_header_3 = st.session_state.get("p4_custom_head_line_3_final_fixed", default_header_3)
                custom_header_4 = st.session_state.get("p4_custom_head_line_4_final_fixed", "")

                if file_format_type == "1. Upload Admission Format":
                    ADMISSION_FORMAT_COLUMNS = [
                        "Sr.No.", "Academic Batch", "Admission No.", "Enrollment No.",
                        "Student Name", "DOB", "Caste", "Course Code", "Course",
                        "Branch Code", "Branch", "10th Roll No", "10th Board Type",
                        "10th Passing Year", "12th Roll No", "12th Board Type", "12th Passing Year"
                    ]

                    # 🟢 बदलाव: अब यहाँ अलग से फ़ाइल अपलोड नहीं करनी — यह फॉर्मेट सीधे
                    # Admission Panel (P2) में जो डेटा पहले से Approved/मौजूद है, उसी से अपने आप
                    # बन जाएगा। नीचे दिया गया मैप बताता है कि हर आउटपुट कॉलम किस Admission Panel
                    # फ़ील्ड से लिया जा रहा है — अगर कोई मैपिंग बदलनी हो तो बताइए, ठीक कर देंगे।
                    ADMISSION_FORMAT_SOURCE_MAP = {
                        "Academic Batch": "Admission Session",
                        "Admission No.": "Admission Application Number",
                        "Enrollment No.": "Enrollment No.",
                        "Student Name": "Student Name",
                        "DOB": "Date of Birth",
                        "Caste": "Category",
                        "Course Code": "Subject Code",
                        "Course": "Degree",
                        "Branch Code": "",   # अभी DB में इसका कोई सीधा फ़ील्ड नहीं है
                        "Branch": "Branch",
                        "10th Roll No": "",  # अभी DB में इसका कोई सीधा फ़ील्ड नहीं है
                        "10th Board Type": "",
                        "10th Passing Year": "",
                        "12th Roll No": "",
                        "12th Board Type": "",
                        "12th Passing Year": ""
                    }

                    st.info(
                        "📌 यह फॉर्मेट अब खुद-ब-खुद Admission Panel (P2) के मौजूदा डेटा से बनता है — "
                        "अलग से फ़ाइल अपलोड करने की ज़रूरत नहीं है। जिन कॉलम्स के लिए अभी डेटाबेस में कोई "
                        "सीधा फ़ील्ड नहीं है (जैसे Branch Code, 10th/12th की जानकारी), वे फ़िलहाल खाली दिखेंगे।"
                    )

                    admission_source_df = live_db[live_db["Target Panel Visibility"] == "P2"].copy()

                    if admission_source_df.empty:
                        st.warning("⚠️ Admission Panel (P2) में अभी कोई अधिकृत (Approved) डेटा उपलब्ध नहीं है, इसलिए यह फॉर्मेट खाली है।")
                    else:
                        adm_fix_map = {
                            "Unique Id": "Unique ID", "Date Of Birth": "Date of Birth",
                            "Duretion": "Duration", "Email Id": "Email ID", "Year": "Current Year"
                        }
                        admission_source_df = admission_source_df.rename(columns=adm_fix_map)
                        admission_source_df = admission_source_df.loc[:, ~admission_source_df.columns.duplicated()].copy()

                        adm_fmt_df = pd.DataFrame()
                        for out_col in ADMISSION_FORMAT_COLUMNS:
                            if out_col == "Sr.No.":
                                continue
                            src_col = ADMISSION_FORMAT_SOURCE_MAP.get(out_col, "")
                            if src_col and src_col in admission_source_df.columns:
                                adm_fmt_df[out_col] = admission_source_df[src_col].astype(str).str.strip()
                            else:
                                adm_fmt_df[out_col] = ""

                        adm_fmt_df.insert(0, "Sr.No.", range(1, len(adm_fmt_df) + 1))

                        st.success(f"✅ Admission Panel से कुल {len(adm_fmt_df)} रिकॉर्ड्स इस फॉर्मेट में मिले।")
                        st.dataframe(adm_fmt_df[ADMISSION_FORMAT_COLUMNS], use_container_width=True, hide_index=True)

                        st.download_button(
                            label="📥 Admission Format Download करें (CSV)",
                            data=adm_fmt_df[ADMISSION_FORMAT_COLUMNS].to_csv(index=False).encode('utf-8'),
                            file_name="admission_format_export.csv",
                            mime="text/csv",
                            use_container_width=True,
                            key="p4_admission_format_download_btn"
                        )

                        # ==================================================================
                        # 🖨️ Admission Format Print Engine (P2 जैसा ही Iframe Print System,
                        # ऊपर के Print Header Customizer वाले custom_header_1..4 यहीं इस्तेमाल होते हैं)
                        # ==================================================================
                        adm_print_df = adm_fmt_df[ADMISSION_FORMAT_COLUMNS].copy()
                        adm_columns_list = list(adm_print_df.columns)
                        adm_records_list = adm_print_df.to_dict(orient="records")

                        adm_headers_html = "".join([f"<th style='border:1px solid #111; padding:6px; background:#f2f2f2; font-weight:bold; text-align:center;'>{col}</th>" for col in adm_columns_list])

                        adm_rows_html = ""
                        for row in adm_records_list:
                            adm_rows_html += "<tr>"
                            for col in adm_columns_list:
                                val = str(row.get(col, "")).replace("`", "'").replace("\n", " ")
                                adm_rows_html += f"<td style='border:1px solid #111; padding:5px; text-align:left;'>{val}</td>"
                            adm_rows_html += "</tr>"

                        adm_clean_table_html = f"""
                        <html>
                        <head>
                            <style>
                                @page {{ size: A4 landscape; margin: 8mm; }}
                                body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; color: #000; }}
                                .custom-print-header {{
                                    width: 100%; border: 2px solid #1465de; background-color: #f4f8ff;
                                    padding: 15px; margin-bottom: 20px; border-radius: 6px;
                                    box-sizing: border-box; text-align: center;
                                }}
                                .h-line-1 {{ font-size: 16px; font-weight: bold; color: #1465de; margin-bottom: 5px; }}
                                .h-line-2 {{ font-size: 14px; font-weight: bold; color: #333; margin-bottom: 5px; }}
                                .h-line-3 {{ font-size: 12px; font-style: italic; color: #555; }}
                                .h-line-4 {{ font-size: 12px; font-style: italic; color: #1465de; margin-top: 3px; }}
                                table {{ width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 10px; }}
                            </style>
                        </head>
                        <body>
                            <div class="custom-print-header">
                                <div class="h-line-1">{custom_header_1}</div>
                                <div class="h-line-2">{custom_header_2}</div>
                                <div class="h-line-3">{custom_header_3}</div>
                                {f'<div class="h-line-4">{custom_header_4}</div>' if custom_header_4 and custom_header_4.strip() else ''}
                            </div>
                            <table>
                                <thead><tr>{adm_headers_html}</tr></thead>
                                <tbody>{adm_rows_html}</tbody>
                            </table>
                        </body>
                        </html>
                        """

                        adm_safe_html_string = adm_clean_table_html.replace("\\", "\\\\").replace("`", "'").replace("\n", " ").replace("\r", "")

                        components.html(
                            f"""
                            <html>
                            <body>
                                <script>
                                function printP4AdmissionFormat() {{
                                    var iframe = window.parent.document.createElement('iframe');
                                    iframe.style.position = 'fixed'; iframe.style.right = '0'; iframe.style.bottom = '0';
                                    iframe.style.width = '0'; iframe.style.height = '0'; iframe.style.border = '0';
                                    window.parent.document.body.appendChild(iframe);

                                    var doc = iframe.contentWindow.document;
                                    doc.open(); doc.write(`{adm_safe_html_string}`); doc.close();
                                    iframe.contentWindow.focus(); iframe.contentWindow.print();

                                    setTimeout(function() {{ window.parent.document.body.removeChild(iframe); }}, 1000);
                                }}
                                </script>
                                <button onclick="printP4AdmissionFormat()" style="
                                    width: 100%; background-color: #1465de; color: white; padding: 14px;
                                    border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 16px;
                                    font-family: sans-serif; box-shadow: 0 4px 6px rgba(20, 101, 222, 0.2);">
                                    🖨️ Click Here to Print Admission Format Report
                                </button>
                            </body>
                            </html>
                            """,
                            height=70
                        )

                elif file_format_type == "2. Upload Fee Format":
                    st.info(
                        "⚙️ Fee Format के लिए कॉलम लिस्ट अभी तय नहीं है — कृपया बताएं कि इसमें कौन-कौन से "
                        "कॉलम चाहिए ताकि यह फीचर भी Admission Format जैसा (validate + save to live database, "
                        "और ऊपर वाले Print Header Customizer के साथ प्रिंट) बनाया जा सके।"
                    )

                st.markdown('</div>', unsafe_allow_html=True)

        # ----------------------------------------------------------------------
        # P5: ADVANCED PANEL-WISE COLUMN TWIN MAPPING SYSTEM (Fixed Core Sync)
        # ----------------------------------------------------------------------
        elif current_panel_id == "P5":
            st.header(f"📢 {get_panel_title('P5')} (Advanced Panel Column Linker)")
            
            # 🟢 Corrected Safe Single-Quote Concatenation Format
            st.markdown(
                '<div style="background-color: #f4fbf7; border-left: 5px solid #2e7d32; padding: 12px; border-radius: 4px; margin-bottom: 20px;">'
                '🎯 <b>कंट्रोल निर्देश:</b> यहाँ से आप किसी भी एक वर्किंग पैनल (P1 से P8) के कॉलम को किसी दूसरे पैनल के कॉलम के साथ आपस में जोड़ सकते हैं।'
                '<br>1. बाईं तरफ (Source) वह पैनल और कॉलम चुनें जहां से डेटा सिंक करना शुरू करना है।'
                '<br>2. दाईं तरफ (Target) वह पैनल और कॉलम चुनें जिसके साथ डेटा लिंक और एक्सचेंज करना है।'
                '<br><br>⚠️ <b>नो न्यू कॉलम पॉलिसी:</b> सिस्टम डेटाबेस में कोई भी नया कॉलम नहीं बनाएगा। दोनों पैनल्स के चुने गए कॉलम्स के बीच बैकएंड डेटा लाइव एक्सचेंज और सिंक हो जाएगा।'
                '</div>', 
                unsafe_allow_html=True
            )
            
            # मुख्य डेटाबेस के सभी 22+ प्रमाणित कॉलम्स
            all_22_columns = [
                "Admission Application Number", "Roll No.", "Enrollment No.", "Student Name", "Father Name", 
                "Admission Year", "Admission Session", "Eligibility Name", "Admission Date", "Unique ID", 
                "Application Enrollment No.", "Mother Name", "Date of Birth", "Category", "Subject", 
                "Duration", "Mobile Number", "Email ID", "Address", "Status", "Current Year", "Payment Date"
            ]
            
            # 🟢 सिर्फ मौजूद पैनल्स (P1, P2, P3, P4, P8) और उनके कॉलम की लिस्ट
            panel_columns_repository = {
                "Panel 1: Data entry Onboarding": all_22_columns,
                "Panel 2: Admission panel": ["Application Number", "Payment Date", "Admission Year", "Admission Session", "Student Name", "Father Name", "Mobile Number", "Status"],
                "Panel 6: Scholarship panel": ["Admission Application Number", "Unique ID", "Student Name", "Category", "Scholarship Name", "Scholarship Status"],
                "Panel 7: CCE panel": all_22_columns,
                "Panel 15: Super-Admin Master Control": all_22_columns
            }
            
            current_twins = load_twin_mappings()
            
            st.subheader("🔗 लिंक करें पैनल्स के जुड़वाँ कॉलम्स (Link Panel Columns)")
            
            # लेआउट को 4 कॉलम ग्रिड में विभाजित किया गया है
            col_p11_left_p, col_p11_left_c, col_p11_right_p, col_p11_right_c = st.columns(4)
            
            with col_p11_left_p:
                # 1. LEFT SIDE - PANEL SELECT
                left_panel = st.selectbox(
                    "🏢 1. सोर्स पैनल चुनें (From Panel):",
                    options=list(panel_columns_repository.keys()),
                    key="p5_left_panel_select"
                )
                
            with col_p11_left_c:
                # 2. LEFT SIDE - COLUMN SELECT
                left_available_cols = panel_columns_repository[left_panel]
                src_selection = st.selectbox(
                    "⬅️ 2. सोर्स कॉलम (Source Column):",
                    options=left_available_cols,
                    key="p5_left_col_select"
                )
                
            with col_p11_right_p:
                # 3. RIGHT SIDE - PANEL SELECT
                right_panel = st.selectbox(
                    "🏢 3. टारगेट पैनल चुनें (To Panel):",
                    options=list(panel_columns_repository.keys()),
                    key="p5_right_panel_select"
                )
                
            with col_p11_right_c:
                # 4. RIGHT SIDE - COLUMN SELECT
                right_available_cols = panel_columns_repository[right_panel]
                tgt_selection = st.selectbox(
                    "➡️ 4. टारगेट कॉलम (Target Column):",
                    options=right_available_cols,
                    key="p5_right_col_select"
                )
            
            # फाइनल सबमिशन बटन
            btn_label = f"🔗 सिंक सक्रिय करें: {left_panel.split(':')[0]} ({src_selection}) ↔ {right_panel.split(':')[0]} ({tgt_selection})"
            if st.button(btn_label, type="primary", use_container_width=True):
                if left_panel == right_panel and src_selection == tgt_selection:
                    st.error("❌ आप एक ही पैनल के एक ही कॉलम को खुद से लिंक नहीं कर सकते! कृपया अलग कॉलम नाम या पैनल चुनें।")
                else:
                    # बैकएंड मैपिंग स्कीमा में मैप को सेव करें
                    current_twins[src_selection] = tgt_selection
                    save_twin_mappings(current_twins)
                    st.success(f"🎉 सफलता! `{left_panel.split(':')[0]}` के `{src_selection}` और `{right_panel.split(':')[0]}` के `{tgt_selection}` के बीच लाइव डेटा सिंक कनेक्शन स्थापित हो गया है।")
                    st.balloons()
                    st.rerun()
            
            # भाग 2: वर्तमान में सक्रिय मैपिंग की लिस्ट और डिलीट करने का विकल्प
            st.markdown("---")
            st.subheader("📋 वर्तमान सक्रिय जुड़वाँ कॉलम्स की सूची (Active Mappings)")
            
            if not current_twins:
                st.info("💡 वर्तमान में कोई डायनेमिक मैपिंग सेट नहीं है। डेटाबेस अपने डिफ़ॉल्ट रूप में काम कर रहा है।")
            else:
                active_maps_list = [{"S.No.": i+1, "Source Column Connection": k, "Target Column Linked": v} for i, (k, v) in enumerate(current_twins.items())]
                st.dataframe(pd.DataFrame(active_maps_list), use_container_width=True, hide_index=True)
                
                st.markdown("##### 🗑️ मैपिंग हटाएं (Remove Link)")
                mapping_to_delete = st.selectbox("हटाने के लिए मैपिंग चुनें:", options=list(current_twins.keys()), format_func=lambda x: f"{x} ↔ {current_twins[x]}")
                
                if st.button("🗑️ सिंक कनेक्शन तोड़ें (Delete Mapping)", type="secondary", use_container_width=True):
                    if mapping_to_delete in current_twins:
                        del current_twins[mapping_to_delete]
                        save_twin_mappings(current_twins)
                        st.error("💥 मैपिंग सफलतापूर्वक हटा दी गई है!")
                        st.rerun()

        # ======================================================================
        # P6: 🔀 MERGE & APPROVE PANEL (Complete Integrated Routing System)
        # ======================================================================
        elif current_panel_id == "P6":
            st.header(f"🔀 {get_panel_title('P6')} (Live Multi-Column Merge Verification & Routing Room)")
            
            # Load the staging verification queue and main central repository
            stage_db = load_stage_data()
            master_db_lookup = load_live_data()
            
            if stage_db.empty:
                st.success("🟢 शानदार! स्टेजिंग कतार पूर्णतः खाली है। पैनल 1 से भेजी गयी सभी फाइलें प्रोसेस की जा चुकी हैं।")
            else:
                # 🟢 Corrected Safe Inline String Setup
                st.markdown(
                    '<div style="background-color: #f0f7ff; border-left: 5px solid #1465de; padding: 12px; border-radius: 4px; margin-bottom: 20px;">'
                    '🎯 <b>कन्फर्मेशन मर्ज गाइड:</b> पहले वह पैनल (Main File) चुनें जिसका डेटा बदलना है, फिर स्टेजिंग से नई फ़ाइल (Anya File) चुनकर लाइव मैचिंग चेक करें। यदि मर्ज नहीं करना है तो सीधे अप्रूव करें।'
                    '</div>', 
                    unsafe_allow_html=True
                )
                
                # ----------------------------------------------------------------------
                # 👑 स्टेप 1: MAIN FILE (पैनल से डेटा का चयन और लाइव प्रीव्यू)
                # ----------------------------------------------------------------------
                st.subheader("👑 Step 1: Select Main File Panel")
                panel_options_map = {
                    "Panel 2: Admission View": "P2",
                    "Panel 6: Scholarship View": "P3", "Panel 7: CCE panel View": "P4"
                }
                
                selected_main_panel_lbl = st.selectbox(
                    "निरीक्षण और अपडेट करने के लिए मुख्य पैनल (Main File Source) चुनें:",
                    options=list(panel_options_map.keys()),
                    key="p6_main_panel_dropdown_v15"
                )
                target_main_panel_id = panel_options_map[selected_main_panel_lbl]
                
                # Fetch approved records tied to the selected workspace platform visibility token
                main_file_db = master_db_lookup[master_db_lookup["Target Panel Visibility"] == target_main_panel_id].copy()
                
                st.write(f"📊 **Main File (Approved DB):** `{selected_main_panel_lbl}` | वर्तमान रिकॉर्ड्स संख्या: `{len(main_file_db)}`")
                if not main_file_db.empty:
                    with st.expander("👁️ मुख्य फ़ाइल (Main File) का पूरा लाइव डेटा देखें", expanded=False):
                        st.dataframe(main_file_db[[c for c in ["Admission Year", "Application Number", "Student Name", "Father Name", "Subject"] if c in main_file_db.columns]], use_container_width=True)
                else:
                    st.warning("⚠️ इस चयनित पैनल में वर्तमान में कोई स्वीकृत डेटा उपलब्ध नहीं है।")

                # ----------------------------------------------------------------------
                # 📄 स्टेप 2: ANYA FILE (स्टेजिंग कतार से नई फ़ाइल का चयन)
                # ----------------------------------------------------------------------
                st.markdown("---")
                st.subheader("📄 Step 2: Select Anya File (New Uploaded Staging File)")
                distinct_files = list(stage_db["Uploaded File Name"].unique())
                
                selected_anya_file = st.selectbox(
                    "स्टेजिंग कतार से वह नई फ़ाइल चुनें जिससे डेटा खींचना है (या सीधे अप्रूव करने के लिए छोड़ें):", 
                    options=["-- कोई अन्य फ़ाइल नहीं चुनें --"] + distinct_files,
                    key="p6_anya_file_select_v15"
                )

                # ----------------------------------------------------------------------
                # 🚀 केस ए: बिना मर्ज किए सीधे अप्रूव करने का मैकेनिज्म (Direct Approve Window)
                # ----------------------------------------------------------------------
                if selected_anya_file == "-- कोई अन्य फ़ाइल नहीं चुनें --":
                    st.markdown("---")
                    st.subheader("🚀 बिना मर्ज किए सीधे अप्रूव करें (Direct Approval Window)")
                    
                    direct_target_file_name = distinct_files[0] if distinct_files else ""
                    
                    if not direct_target_file_name:
                        st.warning("कतार में कोई फ़ाइल उपलब्ध नहीं है।")
                    else:
                        file_subset_direct = stage_db[stage_db["Uploaded File Name"] == direct_target_file_name].copy()
                        st.info(f"💡 वर्तमान में स्टेजिंग कतार की फ़ाइल '**{direct_target_file_name}**' को इसके मूल रूप में सीधे किसी भी वर्किंग पैनल पर भेजने के लिए नीचे सेटिंग्स चुनें।")
                        
                        col_dir1, col_dir2 = st.columns(2)
                        with col_dir1:
                            direct_routing_panel = st.selectbox(
                                "📌 इस फ़ाइल को किस विशिष्ट वर्किंग पैनल पर विज़िबल करना है?",
                                options=[
                                    "P2 : Admission panel",
                                    "P3 : Unique ID panel",
                                    "P4 : Roll No. panel",
                                    "P5 : Enrollment panel",
                                    "P3 : Scholarship panel",
                                    "P4 : CCE panel",
                                    "P8 : Promotion panel",
                                    "P9 : Result panel",
                                    "P10 : Register panel"
                                ],
                                key="p6_direct_panel_routing_dropdown_v15"
                            )
                            parsed_direct_panel_id = direct_routing_panel.split(" : ")[0].strip()
                            
                        with col_dir2:
                            st.write("")
                            st.write("")
                            direct_approve_btn = st.button("🚀 सीधे अप्रूव करें (Direct Approve & Sync)", type="primary", use_container_width=True, key="p6_direct_approve_btn_v15")
                        
                        with st.expander("⚠️ डेंजर ज़ोन: इस फ़ाइल को स्टेजिंग से हटाएं (बिना अप्रूव किए)", expanded=False):
                            confirm_delete_dir = st.checkbox("हाँ, मैं इस फ़ाइल को पूरी तरह कतार से हटाना चाहता हूँ।", key="confirm_delete_dir_key_v15")
                            if st.button("🗑️ इस फ़ाइल को डिलीट करें", type="primary", use_container_width=True, disabled=not confirm_delete_dir):
                                updated_stage_db = stage_db[stage_db["Uploaded File Name"] != direct_target_file_name]
                                save_stage_data(updated_stage_db)
                                st.error(f"💥 फ़ाइल '{direct_target_file_name}' हटा दी गई!")
                                st.rerun()

                        if direct_approve_btn:
                            try:
                                file_subset_direct["Target Panel Visibility"] = parsed_direct_panel_id
                                
                                # 1. नाम बदलने से पहले ही डुप्लिकेट कॉलम हटाएँ
                                file_subset_direct = file_subset_direct.loc[:, ~file_subset_direct.columns.duplicated()].copy()
                                
                                # Remap layout variables to protect 22 column structural norms
                                column_mapping_fixes = {
                                    "Unique Id": "Unique ID", 
                                    "Date Of Birth": "Date of Birth", "Duretion": "Duration", 
                                    "Email Id": "Email ID", "Year": "Current Year"
                                }
                                file_subset_direct = file_subset_direct.rename(columns=column_mapping_fixes)
                                
                                # 2. नाम बदलने के बाद भी यदि कोई डुप्लिकेट बनता है तो साफ़ करें
                                file_subset_direct = file_subset_direct.loc[:, ~file_subset_direct.columns.duplicated()].copy()
                                
                                # सुरक्षित असाइनमेंट
                                if "Application Number" not in file_subset_direct.columns:
                                    if "Admission Application Number" in file_subset_direct.columns:
                                        file_subset_direct["Application Number"] = file_subset_direct["Admission Application Number"].astype(str)
                                    else:
                                        file_subset_direct["Application Number"] = ""
                                
                                # 3. सुनिश्चित करें कि टारगेट कॉलम्स का ढांचा साफ़ हो
                                for col in DEFAULT_COLUMNS:
                                    if col not in file_subset_direct.columns:
                                        file_subset_direct[col] = ""
                                        
                                # 4. मास्टर डेटाबेस के डुप्लिकेट कॉलम्स भी हटाएँ ताकि जोड़ने में एरर न आए
                                master_db_clean = master_db_lookup.loc[:, ~master_db_lookup.columns.duplicated()].copy()
                                remaining_master_db_dir = master_db_clean[master_db_clean["Target Panel Visibility"] != parsed_direct_panel_id].copy()
                                
                                # 5. अंतिम सुरक्षित कॉनकेट (Concat)
                                final_direct_master = pd.concat([remaining_master_db_dir, file_subset_direct[DEFAULT_COLUMNS]], ignore_index=True)
                                save_live_data(final_direct_master)
                                
                                remaining_stage_db_dir = stage_db[stage_db["Uploaded File Name"] != direct_target_file_name]
                                save_stage_data(remaining_stage_db_dir)
                                
                                st.success(f"🎉 शत-प्रतिशत सफलता! आपकी फ़ाइल बिना किसी बदलाव के सीधे स्वीकृत होकर {parsed_direct_panel_id} पैनल पर लाइव हो चुकी है!")
                                st.balloons()
                                st.rerun()
                            except Exception as dir_err:
                                st.error(f"सीधे अप्रूवल चक्र के दौरान तकनीकी समस्या आई: {dir_err}")

                # ----------------------------------------------------------------------
                # 🔍 केस बी: जब यूजर मर्ज करने के लिए स्टेजिंग से कोई ANYA FILE सेलेक्ट करता है
                # ----------------------------------------------------------------------
                else:
                    anya_file_subset = stage_db[stage_db["Uploaded File Name"] == selected_anya_file].copy()
                    st.write(f"📦 **Anya File (Staging Column Source):** `{selected_anya_file}` | छात्र रिकॉर्ड्स: `{len(anya_file_subset)}`")

                    with st.expander("⚠️ डेंजर ज़ोन: गलत फ़ाइल को स्टेजिंग से हटाएं", expanded=False):
                        st.warning(f"क्या आप निश्चित रूप से फ़ाइल '**{selected_anya_file}**' को स्टेजिंग कतार से हटाना चाहते हैं?")
                        confirm_delete = st.checkbox("हाँ, मैं इस फ़ाइल को डिलीट करना चाहता हूँ।", key="confirm_delete_v15")
                        if st.button("🗑️ परमानेंटली डिलीट करें", type="primary", use_container_width=True, disabled=not confirm_delete):
                            updated_stage_db = stage_db[stage_db["Uploaded File Name"] != selected_anya_file]
                            save_stage_data(updated_stage_db)
                            st.error(f"💥 फ़ाइल '{selected_anya_file}' हटा दी गई!")
                            st.rerun()

                    st.markdown("---")
                    st.subheader("🔍 Step 3: Configure Matching & Columns Data Retrieval")
                    
                    if main_file_db.empty:
                        st.info("💡 अन्य फ़ाइल से मर्ज करने के लिए मुख्य पैनल में कम से कम एक डेटा रिकॉर्ड होना आवश्यक है।")
                    else:
                        col_m1, col_m2 = st.columns(2)
                        with col_m1:
                            main_match_key = st.selectbox(
                                "Main File का मैचिंग कॉलम चुनें (जैसे Application Number):",
                                options=list(main_file_db.columns),
                                key="xl_main_match_key_v15"
                            )
                        with col_m2:
                            anya_match_key = st.selectbox(
                                "Anya File का मैचिंग कॉलम चुनें (जैसे Application Number):",
                                options=list(anya_file_subset.columns),
                                key="xl_anya_match_key_v15"
                            )
                            
                        anya_return_cols = st.multiselect(
                            "Anya File के वे कॉलम्स चुनें जिनका डेटा Main File में भरना है (जैसे B, C, D कॉलम्स):",
                            options=[c for c in anya_file_subset.columns if c not in ["Uploaded File Name", "Target Panel Visibility"]],
                            default=[c for c in ["Student Name", "Father Name", "Mother Name", "Roll No.", "Enrollment No."] if c in anya_file_subset.columns],
                            key="xl_anya_return_cols_v15"
                        )

                        # ----------------------------------------------------------------------
                        # 👁️ Live Merge Preview Engine
                        # ----------------------------------------------------------------------
                        if anya_return_cols:
                            try:
                                main_file_db[main_match_key] = main_file_db[main_match_key].astype(str).str.strip()
                                anya_file_subset[anya_match_key] = anya_file_subset[anya_match_key].astype(str).str.strip()
                                
                                anya_clean = anya_file_subset[[anya_match_key] + [c for c in anya_return_cols if c != anya_match_key]].copy().drop_duplicates(subset=[anya_match_key])
                                
                                preview_merged = pd.merge(
                                    main_file_db,
                                    anya_clean,
                                    left_on=main_match_key,
                                    right_on=anya_match_key,
                                    how='left',
                                    suffixes=('', '_new_data')
                                )
                                
                                for col in anya_return_cols:
                                    new_col_name = f"{col}_new_data" if f"{col}_new_data" in preview_merged.columns else col
                                    if new_col_name in preview_merged.columns:
                                        preview_merged[col] = preview_merged[new_col_name].fillna(preview_merged[col]).astype(str)
                                
                                if main_match_key in preview_merged.columns:
                                    if f"{main_match_key}_new_data" in preview_merged.columns:
                                        preview_merged[main_match_key] = preview_merged[main_match_key].fillna(preview_merged[f"{main_match_key}_new_data"])
                                
                                keep_preview_cols = [c for c in preview_merged.columns if not c.endswith('_new_data') and c != f"{anya_match_key}_y"]
                                final_preview_df = preview_merged[keep_preview_cols].copy()
                                
                                if main_match_key not in final_preview_df.columns and f"{main_match_key}_x" in final_preview_df.columns:
                                    final_preview_df = final_preview_df.rename(columns={f"{main_match_key}_x": main_match_key})
                                
                                st.markdown("#### 📈 Live Merge Preview (जांचें कि सही मर्ज है या नहीं)")
                                st.caption("नीचे दी गई तालिका दिखा रही है कि अप्रूव करने पर मेन फ़ाइल में डेटा किस प्रकार अपडेट होकर सेव होगा:")
                                
                                preview_display_cols = list(set(["Admission Year", main_match_key, "Student Name", "Father Name", "Target Panel Visibility"] + anya_return_cols))
                                st.dataframe(final_preview_df[[c for c in preview_display_cols if c in final_preview_df.columns]], use_container_width=True)
                                
                                # ----------------------------------------------------------------------
                                # 🚀 Step 4: Finalize & Precision Approve
                                # ----------------------------------------------------------------------
                                st.markdown("---")
                                st.subheader("🚀 Step 4: Finalize & Precision Approve")
                                
                                col_app1, col_app2 = st.columns(2)
                                with col_app1:
                                    target_routing_panel = st.selectbox(
                                        "📌 इस स्वीकृत डेटा को किस वर्किंग पैनल पर विज़िबल रखना है?",
                                        options=[
                                            "P2 : Admission panel",
                                            "P3 : Unique ID panel",
                                            "P4 : Roll No. panel",
                                            "P5 : Enrollment panel",
                                            "P3 : Scholarship panel",
                                            "P4 : CCE panel",
                                            "P8 : Promotion panel",
                                            "P9 : Result panel",
                                            "P10 : Register panel"
                                        ],
                                        key="p6_target_panel_routing_dropdown_v15"
                                    )
                                    parsed_panel_id = target_routing_panel.split(" : ")[0].strip()
                                    
                                with col_app2:
                                    st.write("")
                                    st.write("")
                                    approve_action_btn = st.button("🚀 Approve & Update Selected Data Rows", type="primary", use_container_width=True, key="p6_final_approve_btn_v15")
                                
                                if approve_action_btn:
                                    try:
                                        # 1. किसी भी तरह के डुप्लिकेट कॉलम को पहले ही साफ़ करें
                                        final_preview_df = final_preview_df.loc[:, ~final_preview_df.columns.duplicated()].copy()
                                        
                                        final_preview_df["Target Panel Visibility"] = parsed_panel_id
                                        
                                        # 2. पुराने कॉलम नामों को प्रमाणित स्कीमों में बदलें
                                        column_mapping_fixes = {
                                            "Unique Id": "Unique ID", 
                                            "Date Of Birth": "Date of Birth", "Duretion": "Duration", 
                                            "Email Id": "Email ID", "Year": "Current Year"
                                        }
                                        final_preview_df = final_preview_df.rename(columns=column_mapping_fixes)
                                        
                                        # 3. नाम बदलने के बाद यदि फिर से कोई डुप्लिकेट बनता है, तो उसे दोबारा साफ़ करें
                                        final_preview_df = final_preview_df.loc[:, ~final_preview_df.columns.duplicated()].copy()
                                        
                                        # 4. 🔴 एरर फिक्स सुरक्षित असाइनमेंट इंजन:
                                        # चेक करें कि 'Application Number' कॉलम मौजूद है या नहीं
                                        if "Application Number" in final_preview_df.columns:
                                            # सुनिश्चित करें कि हम डेटाफ्रेम नहीं, बल्कि उसकी वैल्यू या सीरीज़ ही ले रहे हैं
                                            app_num_data = final_preview_df["Application Number"]
                                            if isinstance(app_num_data, pd.DataFrame):
                                                final_preview_df["Application Number"] = app_num_data.iloc[:, 0].astype(str)
                                            else:
                                                final_preview_df["Application Number"] = app_num_data.astype(str)
                                        elif "Admission Application Number" in final_preview_df.columns:
                                            adm_app_data = final_preview_df["Admission Application Number"]
                                            if isinstance(adm_app_data, pd.DataFrame):
                                                final_preview_df["Application Number"] = adm_app_data.iloc[:, 0].astype(str)
                                            else:
                                                final_preview_df["Application Number"] = adm_app_data.astype(str)
                                        else:
                                            final_preview_df["Application Number"] = ""

                                        # 5. मास्टर डेटाबेस से पुराना विज़िबिलिटी डेटा साफ़ करें
                                        remaining_master_db = master_db_lookup[master_db_lookup["Target Panel Visibility"] != parsed_panel_id].copy()
                                        remaining_master_db = remaining_master_db.loc[:, ~remaining_master_db.columns.duplicated()].copy()
                                        
                                        # 6. सभी आवश्यक DEFAULT_COLUMNS को सुरक्षित सेट करें
                                        for col in DEFAULT_COLUMNS:
                                            if col not in final_preview_df.columns:
                                                final_preview_df[col] = ""
                                                
                                        # 7. केवल एकल और ओरिजिनल कॉलम्स का सुरक्षित संकलन (Concat)
                                        final_updated_master_db = pd.concat([remaining_master_db, final_preview_df[DEFAULT_COLUMNS]], ignore_index=True)
                                        save_live_data(final_updated_master_db)
                                        
                                        # 8. स्टेजिंग कतार से प्रविष्टि हटाएं
                                        remaining_stage_db = stage_db[stage_db["Uploaded File Name"] != selected_anya_file]
                                        save_stage_data(remaining_stage_db)
                                        
                                        st.success(f"🎉 शत-प्रतिशत सफलता! Anya फ़ाइल का डेटा मुख्य फ़ाइल में सही जगह अपडेट होकर और मैचिंग कॉलम के साथ {parsed_panel_id} पर लाइव हो चुका है!")
                                        st.balloons()
                                        st.rerun()
                                        
                                    except Exception as inner_merge_err:
                                        st.error(f"मर्ज डेटाबेस सेव चक्र के दौरान तकनीकी समस्या आई: {inner_merge_err}")
                                    
                                    # Normalize alternate key names to standardized core database headers before final commit
                                    column_mapping_fixes = {
                                        "Unique Id": "Unique ID", 
                                        "Date Of Birth": "Date of Birth", "Duretion": "Duration", 
                                        "Email Id": "Email ID", "Year": "Current Year",
                                        "Application Number": "Admission Application Number"
                                    }
                                    final_preview_df = final_preview_df.rename(columns=column_mapping_fixes)
                                    if "Application Number" not in final_preview_df.columns and "Admission Application Number" in final_preview_df.columns:
                                        final_preview_df["Application Number"] = final_preview_df["Admission Application Number"]

                                    remaining_master_db = master_db_lookup[master_db_lookup["Target Panel Visibility"] != parsed_panel_id].copy()
                                    
                                    for col in DEFAULT_COLUMNS:
                                        if col not in final_preview_df.columns:
                                            final_preview_df[col] = ""
                                            
                                    final_updated_master_db = pd.concat([remaining_master_db, final_preview_df[DEFAULT_COLUMNS]], ignore_index=True)
                                    save_live_data(final_updated_master_db)
                                    
                                    remaining_stage_db = stage_db[stage_db["Uploaded File Name"] != selected_anya_file]
                                    save_stage_data(remaining_stage_db)
                                    
                                    st.success(f"🎉 शत-प्रतिशत सफलता! Anya फ़ाइल का डेटा मुख्य फ़ाइल में सही जगह अपडेट होकर और मैचिंग कॉलम के साथ {parsed_panel_id} पर लाइव हो चुका है!")
                                    st.balloons()
                                    st.rerun()
                                    
                            except Exception as merge_err:
                                st.error(f"लाइव मर्ज वेरिफिकेशन के दौरान तकनीकी समस्या आई: {merge_err}")
                        else:
                            st.info("💡 कृपया प्रीव्यू और अपडेट इंजन को सक्रिय करने के लिए Step 3 से कम से कम एक रिटर्न कॉलम ज़रूर चुनें।")

        # ----------------------------------------------------------------------
        # P7: MULTI-PANEL INSPECTION WINDOW
        # ----------------------------------------------------------------------
        elif current_panel_id == "P7":
            st.header(f"👁️ {get_panel_title('P7')} (Multi-Panel Inspection Window)")

            # Standardized 22 core fields mapping per target layout configuration
            all_22_columns = [
                "Admission Application Number", "Roll No.", "Enrollment No.", "Student Name", "Father Name", 
                "Admission Year", "Admission Session", "Eligibility Name", "Admission Date", "Unique ID", 
                "Application Enrollment No.", "Mother Name", "Date of Birth", "Category", "Subject", 
                "Duration", "Mobile Number", "Email ID", "Address", "Status", "Current Year", "Payment Date"
            ]

            # Structural column profiles customized per workspace panel selection (only available panels)
            panel_options_list = {
                "Panel 2: Admission View": all_22_columns,
                "Panel 6: Scholarship View": ["Admission Application Number", "Unique ID", "Student Name", "Category", "Scholarship Name", "Scholarship Status"],
                "Panel 7: CCE panel View": all_22_columns
            }

            st.subheader("📂 Select Panel Dashboard View")
            selected_panel_view = st.selectbox(
                "निरीक्षण करने के लिए पैनल सूची चुनें (Select Dashboard to Inspect):",
                options=list(panel_options_list.keys()),
                key="p7_panel_selector_dropdown_secure_v15"
            )

            # Map selection labels to their exact database target visibility tracking tags
            panel_id_map = {
                "Panel 2: Admission View": "P2",
                "Panel 6: Scholarship View": "P3", "Panel 7: CCE panel View": "P4"
            }
            target_panel_id = panel_id_map[selected_panel_view]
            target_columns = panel_options_list[selected_panel_view]

            # 🔍 Isolated Firewall Query Rule: Filter centralized records matching visibility tokens
            view_filtered_db = live_db[live_db["Target Panel Visibility"] == target_panel_id].copy()

            # Normalization translator dictionary to prevent cell mismatches or blank structures
            column_mapping_fixes = {
                "Unique Id": "Unique ID", "Student Abc Id": "Unique ID", 
                "Date Of Birth": "Date of Birth", "Duretion": "Duration", 
                "Email Id": "Email ID", "Year": "Current Year",
                "Application Number": "Admission Application Number",
                "Enrollment No": "Enrollment No."
            }
            view_filtered_db = view_filtered_db.rename(columns=column_mapping_fixes)
            if "Application Number" in view_filtered_db.columns and "Admission Application Number" not in view_filtered_db.columns:
                view_filtered_db["Admission Application Number"] = view_filtered_db["Application Number"]

            # Populate any structural column keys missing from memory
            for c_col in target_columns:
                if c_col not in view_filtered_db.columns:
                    view_filtered_db[c_col] = ""

            st.markdown(f"### 📋 {selected_panel_view} - Isolated Inspection Records")
            
            col_search1, col_search2 = st.columns(2)
            with col_search1:
                search_target_col = st.selectbox("खोजने के लिए फ़ील्ड चुनें:", options=target_columns, key="p7_search_col_target_secure_v15")
            with col_search2:
                search_query_text = st.text_input(f"'{search_target_col}' में प्रविष्टि खोजें:", key="p7_query_val_text_secure_v15").strip()

            if search_query_text != "":
                # 🟢 डुप्लिकेट कॉलम एरर फिक्स इंजन
                col_data = view_filtered_db[search_target_col]
                search_series = col_data.iloc[:, 0] if isinstance(col_data, pd.DataFrame) else col_data
                
                view_filtered_db = view_filtered_db[
                    search_series.astype(str).str.contains(search_query_text, case=False, na=False)
                ]

            st.write(f"वर्तमान ग्रिड में कुल उपलब्ध स्वीकृत छात्र रिकॉर्ड संख्या: **{len(view_filtered_db)}**")

            final_render_cols = [col for col in target_columns if col in view_filtered_db.columns]
            
            if not view_filtered_db.empty:
                display_ready_df = view_filtered_db[final_render_cols].copy()
                display_ready_df.insert(0, "S. No.", range(1, len(display_ready_df) + 1))
            
                # 🟢 एरर फिक्स: डुप्लिकेट कॉलम को डिलीट करने के लिए यह लाइन यहाँ जोड़ें
                display_ready_df = display_ready_df.loc[:, ~display_ready_df.columns.duplicated()].copy()
            
                st.dataframe(display_ready_df, use_container_width=True, hide_index=True)
                
                st.download_button(
                    label=f"📥 Download Selected Dashboard Report Snapshot (CSV)",
                    data=view_filtered_db[final_render_cols].to_csv(index=False).encode('utf-8'),
                    file_name=f"{selected_panel_view.replace(':', '').replace(' ', '_').lower()}_snapshot.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="p7_download_compiled_report_btn_secure_v15"
                )
            else:
                st.warning("🔍 निर्दिष्ट खोज प्रविष्टि या स्वीकृत पैनल विज़िबिलिटी के आधार पर कोई रिकॉर्ड नहीं मिला।")

        # ----------------------------------------------------------------------
        # P8: PANEL ADMIN (SUPREME ENGINE & NOTICE BOARD MANAGER)
        # ----------------------------------------------------------------------
        elif current_panel_id == "P8":
            st.header(f"🛠️ {get_panel_title('P8')} (Full Super-Admin Control Command)")
            
            # 📢 Live Notice Board Manager Panel Area
            hdr_c1_p15_show_notice_board, hdr_c2_p15_show_notice_board = st.columns([6, 1])
            with hdr_c1_p15_show_notice_board:
                st.subheader("📢 Live Notice Board Manager")
            with hdr_c2_p15_show_notice_board:
                if st.button("🙈 Hide" if st.session_state.get("p8_show_notice_board", True) else "👁️ Unhide", key="p8_show_notice_board_toggle_btn", use_container_width=True):
                    st.session_state["p8_show_notice_board"] = not st.session_state.get("p8_show_notice_board", True)
                    st.rerun()

            if st.session_state.get("p8_show_notice_board", True):
                with st.expander("कॉलेज सूचना पटल (Official Notice Board) की गाइडलाइंस एडिट करें", expanded=True):
                    with st.form(key="p8_global_notice_form_final_secure"):
                        updated_notice_input = st.text_area(
                            "सूचना पटल की पंक्तियाँ लिखें (प्रत्येक नई लाइन मुख्य पेज पर एक नया पॉइंट बनेगी):",
                            value=st.session_state.notice_text,
                            height=150,
                            key="p8_notice_text_area_input_final_secure"
                        )
                        if st.form_submit_button("Publish & Save Notice Board Permanently", type="primary", use_container_width=True):
                            st.session_state.notice_text = updated_notice_input
                            save_notice_board(updated_notice_input)
                            st.success("🎉 कॉलेज सूचना पटल सफलतापूर्वक अपडेट हो गया है! यह बिना लॉगिन वाले होम पेज पर लाइव दिखाई देगा।")
                            st.rerun()

            st.markdown("---")

            # --- (P12 se yahan shift kiya gaya) Header Elements & Branding Themes ---
            hdr_c1_p15_show_header_branding, hdr_c2_p15_show_header_branding = st.columns([6, 1])
            with hdr_c1_p15_show_header_branding:
                st.subheader("🖼️ Header Elements & Branding Themes")
            with hdr_c2_p15_show_header_branding:
                if st.button("🙈 Hide" if st.session_state.get("p8_show_header_branding", True) else "👁️ Unhide", key="p8_show_header_branding_toggle_btn", use_container_width=True):
                    st.session_state["p8_show_header_branding"] = not st.session_state.get("p8_show_header_branding", True)
                    st.rerun()

            if st.session_state.get("p8_show_header_branding", True):
                with st.form(key="p8_landing_view_editor_form_secure"):
                    col_view1, col_view2 = st.columns(2)
                    with col_view1:
                        header_toggle = st.checkbox(
                            "Display Institutional Header Text Block", 
                            value=bool(st.session_state.pre_login_config.get("show_header_text", True))
                        )
                        mantra_text = st.text_input(
                            "Spiritual Invocation / Mantra Text:", 
                            value=str(st.session_state.pre_login_config.get("header_mantra", "ॐ श्री गुरवे नमः"))
                        )
                    with col_view2:
                        system_title_text = st.text_input(
                            "Main Gateway Application Title:", 
                            value=str(st.session_state.pre_login_config.get("system_title", "Permanent Shared Live Database System"))
                        )

                    st.markdown("##### 🔤 Header Text Font Size")
                    col_font1, col_font2 = st.columns(2)
                    with col_font1:
                        mantra_font_size = st.slider(
                            "Spiritual Invocation / Mantra — Font Size (px):",
                            min_value=10, max_value=60,
                            value=int(st.session_state.pre_login_config.get("header_mantra_font_size", 24)),
                            key="p8_mantra_font_size_slider"
                        )
                    with col_font2:
                        title_font_size = st.slider(
                            "Main Gateway Application Title — Font Size (px):",
                            min_value=10, max_value=80,
                            value=int(st.session_state.pre_login_config.get("header_title_font_size", 32)),
                            key="p8_title_font_size_slider"
                        )

                    st.markdown("##### Notice Board Branding Colors")
                    col_theme1, col_theme2 = st.columns(2)
                    with col_theme1:
                        border_color = st.color_picker(
                            "Left Accent Border Color:",
                            value=str(st.session_state.pre_login_config.get("notice_board_border_color", "#FF5733"))
                        )
                    with col_theme2:
                        bg_color = st.color_picker(
                            "Container Background Surface Color:", 
                            value=str(st.session_state.pre_login_config.get("notice_board_bg_color", "#f9f9f9"))
                        )
                    
                    submit_settings = st.form_submit_button("💾 Apply & Save Landing View Settings Permanently", type="primary", use_container_width=True)
                    
                    if submit_settings:
                        updated_config = {
                            "show_header_text": header_toggle,
                            "header_mantra": mantra_text,
                            "system_title": system_title_text,
                            "header_mantra_font_size": mantra_font_size,
                            "header_title_font_size": title_font_size,
                            "notice_board_border_color": border_color,
                            "notice_board_bg_color": bg_color
                        }
                        st.session_state.pre_login_config = updated_config
                        save_pre_login_config(updated_config)
                        st.success("🎉 डैशबोर्ड विजुअल सेटिंग्स सफलतापूर्वक सेव हो गई हैं!")
                        st.rerun()

            st.markdown("---")

            # --- (P12 se yahan shift kiya gaya) Logo Upload, Size & Fit Mode Customizer ---
            hdr_c1_p15_show_logo_upload, hdr_c2_p15_show_logo_upload = st.columns([6, 1])
            with hdr_c1_p15_show_logo_upload:
                st.subheader("🖼️ लोगो अपलोड, साइज़ और फिट मोड कंट्रोल")
            with hdr_c2_p15_show_logo_upload:
                if st.button("🙈 Hide" if st.session_state.get("p8_show_logo_upload", True) else "👁️ Unhide", key="p8_show_logo_upload_toggle_btn", use_container_width=True):
                    st.session_state["p8_show_logo_upload"] = not st.session_state.get("p8_show_logo_upload", True)
                    st.rerun()

            if st.session_state.get("p8_show_logo_upload", True):
                st.caption("यहाँ से नया लोगो अपलोड करें, उसकी Width/Height अलग-अलग सेट करें और Fit Mode चुनें — Live Preview में सेव करने से पहले ही देख सकते हैं कि लोगो कैसा दिखेगा।")

                current_logo_path = st.session_state.pre_login_config.get("logo_path", "logo pratap.png")
                current_logo_w = int(st.session_state.pre_login_config.get("logo_width", 110))
                current_logo_h = int(st.session_state.pre_login_config.get("logo_height", 110))
                current_logo_fit = st.session_state.pre_login_config.get("logo_fit_mode", "contain")

                new_logo_file = st.file_uploader(
                    "नया लोगो अपलोड करें (PNG/JPG) — खाली छोड़ने पर मौजूदा लोगो बना रहेगा:",
                    type=["png", "jpg", "jpeg"],
                    key="p8_logo_uploader_v1"
                )

                col_logo1, col_logo2, col_logo3 = st.columns(3)
                with col_logo1:
                    logo_width_input = st.slider("↔️ Logo Width (px)", min_value=30, max_value=400, value=current_logo_w, key="p8_logo_width_slider_v1")
                with col_logo2:
                    logo_height_input = st.slider("↕️ Logo Height (px)", min_value=30, max_value=400, value=current_logo_h, key="p8_logo_height_slider_v1")
                with col_logo3:
                    fit_options = ["contain", "cover"]
                    fit_index = fit_options.index(current_logo_fit) if current_logo_fit in fit_options else 0
                    logo_fit_input = st.selectbox(
                        "🖼️ Fit Mode",
                        options=fit_options,
                        index=fit_index,
                        format_func=lambda x: "contain (पूरी image दिखेगी, कटेगी नहीं)" if x == "contain" else "cover (box भरेगा, extra हिस्सा crop हो सकता है)",
                        key="p8_logo_fit_selector_v1"
                    )

                preview_img_base64 = ""
                if new_logo_file is not None:
                    preview_bytes = new_logo_file.getvalue()
                    preview_img_base64 = f"data:image/png;base64,{base64.b64encode(preview_bytes).decode()}"
                else:
                    preview_img_base64 = get_image_base64(current_logo_path)

                st.markdown("##### 👁️ Live Preview")
                if preview_img_base64:
                    st.markdown(
                        f"""
                        <div style="width:{logo_width_input}px; height:{logo_height_input}px; display:flex; align-items:center; justify-content:center;
                                    overflow:hidden; border-radius:8px; box-shadow:0 4px 10px rgba(0,0,0,0.15); border:1px solid #e2e8f0; background:#fff;">
                            <img src="{preview_img_base64}" style="width:100%; height:100%; object-fit:{logo_fit_input}; display:block;">
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.info("ℹ️ अभी कोई लोगो उपलब्ध नहीं है — प्रीव्यू देखने के लिए एक लोगो अपलोड करें।")

                if st.button("📏 साइज़ & फिट सेव करें", type="primary", use_container_width=True, key="p8_logo_save_btn_v1"):
                    saved_path = current_logo_path
                    if new_logo_file is not None:
                        ext = os.path.splitext(new_logo_file.name)[1] or ".png"
                        saved_path = f"custom_logo{ext}"
                        with open(saved_path, "wb") as f_logo:
                            f_logo.write(new_logo_file.getvalue())

                    updated_logo_config = dict(st.session_state.pre_login_config)
                    updated_logo_config["logo_path"] = saved_path
                    updated_logo_config["logo_width"] = logo_width_input
                    updated_logo_config["logo_height"] = logo_height_input
                    updated_logo_config["logo_fit_mode"] = logo_fit_input

                    st.session_state.pre_login_config = updated_logo_config
                    save_pre_login_config(updated_logo_config)
                    st.success("🎉 लोगो साइज़, फिट मोड और (यदि अपलोड की गई हो तो) नई इमेज सफलतापूर्वक सेव हो गई!")
                    st.rerun()

            st.markdown("---")
            hdr_c1_p15_show_panel_names, hdr_c2_p15_show_panel_names = st.columns([6, 1])
            with hdr_c1_p15_show_panel_names:
                st.subheader("✏️ Dynamic 8 Panels Name & Label Customizer")
            with hdr_c2_p15_show_panel_names:
                if st.button("🙈 Hide" if st.session_state.get("p8_show_panel_names", True) else "👁️ Unhide", key="p8_show_panel_names_toggle_btn", use_container_width=True):
                    st.session_state["p8_show_panel_names"] = not st.session_state.get("p8_show_panel_names", True)
                    st.rerun()

            if st.session_state.get("p8_show_panel_names", True):
                with st.expander("8 पैनल्स के नाम (App Titles) एडिट करने के लिए यहाँ क्लिक करें", expanded=False):
                    with st.form(key="p8_panel_rename_matrix_form_final_secure"):
                        p_setup1, p_setup2 = st.columns(2)
                        temp_panel_mappings = {}
                        for idx, p_key in enumerate(DEFAULT_PANELS.keys()):
                            current_panel_name = st.session_state.panel_names.get(p_key, DEFAULT_PANELS[p_key])
                            if idx % 2 == 0:
                                with p_setup1: 
                                    temp_panel_mappings[p_key] = st.text_input(f"Name for {p_key}:", value=current_panel_name, key=f"p8_ren_final_{p_key}")
                            else:
                                with p_setup2: 
                                    temp_panel_mappings[p_key] = st.text_input(f"Name for {p_key}:", value=current_panel_name, key=f"p8_ren_final_{p_key}")
                        
                        if st.form_submit_button("Save All 8 Panel Titles Permanently", type="primary", use_container_width=True):
                            st.session_state.panel_names = temp_panel_mappings
                            save_panel_names(temp_panel_mappings)
                            st.success("✅ सभी 8 पैनल्स के नाम अपडेट हो गए हैं!")
                            st.rerun()

            st.markdown("---")
            hdr_c1_p15_show_panel_visibility, hdr_c2_p15_show_panel_visibility = st.columns([6, 1])
            with hdr_c1_p15_show_panel_visibility:
                st.subheader("🛡️ Global 8 Panels Visibility Toggle Switch Board")
            with hdr_c2_p15_show_panel_visibility:
                if st.button("🙈 Hide" if st.session_state.get("p8_show_panel_visibility", True) else "👁️ Unhide", key="p8_show_panel_visibility_toggle_btn", use_container_width=True):
                    st.session_state["p8_show_panel_visibility"] = not st.session_state.get("p8_show_panel_visibility", True)
                    st.rerun()

            if st.session_state.get("p8_show_panel_visibility", True):
                # Visibility Panel Controllers Layer for the 8 active panels only
                active_panel_keys = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]
                vis_cols = st.columns(len(active_panel_keys))
                for i, p_key in enumerate(active_panel_keys):
                    with vis_cols[i]:
                        status_lbl = "🙈 Hidden" if st.session_state.get(f"hide_panel_{p_key}", False) else "👀 Active"
                        if st.button(f"{p_key}\n({status_lbl})", use_container_width=True, key=f"p8_btn_v_final_{p_key}"):
                            st.session_state[f"hide_panel_{p_key}"] = not st.session_state.get(f"hide_panel_{p_key}", False)
                            st.rerun()

            # ⚙️ सुपर-एडमिन मास्टर ड्रॉपडाउन लिस्ट कस्टमाइज़र
            st.markdown("---")
            hdr_c1_p15_show_dropdown_customizer, hdr_c2_p15_show_dropdown_customizer = st.columns([6, 1])
            with hdr_c1_p15_show_dropdown_customizer:
                st.subheader("⚙️ Super-Admin Master Dropdown List Customizer")
            with hdr_c2_p15_show_dropdown_customizer:
                if st.button("🙈 Hide" if st.session_state.get("p8_show_dropdown_customizer", True) else "👁️ Unhide", key="p8_show_dropdown_customizer_toggle_btn", use_container_width=True):
                    st.session_state["p8_show_dropdown_customizer"] = not st.session_state.get("p8_show_dropdown_customizer", True)
                    st.rerun()

            if st.session_state.get("p8_show_dropdown_customizer", True):
                st.markdown("पैनल 1 (Data Onboarding) में दिखने वाली तीनों स्क्रॉल सूचियों के विकल्पों को यहाँ से लाइव कस्टमाइज़ करें:")
                
                col_drop1, col_drop2, col_drop3 = st.columns(3)
                with col_drop1:
                    st.markdown("##### 📁 1. File Segments / Types")
                    edited_file_types = st.text_area("File Types (एक प्रति लाइन):", value="\n".join(st.session_state.p1_dropdown_schemas["file_types"]), height=140, key="p8_custom_file_types_text")
                with col_drop2:
                    st.markdown("##### 📆 2. Academic Years")
                    edited_years = st.text_area("Admission Years (एक प्रति लाइन):", value="\n".join(st.session_state.p1_dropdown_schemas["academic_years"]), height=140, key="p8_custom_years_text")
                with col_drop3:
                    st.markdown("##### ⏳ 3. Academic Sessions")
                    edited_sessions = st.text_area("Admission Sessions (एक प्रति line):", value="\n".join(st.session_state.p1_dropdown_schemas["academic_sessions"]), height=140, key="p8_custom_sessions_text")
                
                if st.button("💾 Apply & Update Master Dropdown Framework", type="primary", use_container_width=True, key="p8_save_dropdowns_btn"):
                    st.session_state.p1_dropdown_schemas["file_types"] = [line.strip() for line in edited_file_types.split("\n") if line.strip()]
                    st.session_state.p1_dropdown_schemas["academic_years"] = [line.strip() for line in edited_years.split("\n") if line.strip()]
                    st.session_state.p1_dropdown_schemas["academic_sessions"] = [line.strip() for line in edited_sessions.split("\n") if line.strip()]
                    st.success("🎉 ड्रॉपडाउन सूचियाँ सफलतापूर्वक अपडेट हो गईं!")
                    st.rerun()

            # ======================================================================
            # 🔐 न्यू मॉड्यूल: सुरक्षित मास्टर CSV/XLSX फ़ाइल ओवरराइट अपलोडर (Fixed Auto Lock)
            # ======================================================================
            st.markdown("---")
            hdr_c1_p15_show_master_overwrite, hdr_c2_p15_show_master_overwrite = st.columns([6, 1])
            with hdr_c1_p15_show_master_overwrite:
                st.subheader("⚠️ Advanced Action: Dangerous Master File Overwrite Uploader (CSV / XLSX)")
            with hdr_c2_p15_show_master_overwrite:
                if st.button("🙈 Hide" if st.session_state.get("p8_show_master_overwrite", True) else "👁️ Unhide", key="p8_show_master_overwrite_toggle_btn", use_container_width=True):
                    st.session_state["p8_show_master_overwrite"] = not st.session_state.get("p8_show_master_overwrite", True)
                    st.rerun()

            if st.session_state.get("p8_show_master_overwrite", True):
                st.warning("यह एक अत्यंत संवेदनशील विकल्प है। यहाँ नई फ़ाइल अपलोड करने पर वर्तमान का पूरा लाइव डेटाबेस (`shared_student_database.csv`) स्थायी रूप से मिट जाएगा और नई फ़ाइल का डेटा नया मास्टर बन जाएगा।")
                
                # ऑटो-रीसेट ट्रिगर काउंटर स्टेट जो विजेट को रीबूट करेगा
                if "p8_uploader_reset_counter" not in st.session_state:
                    st.session_state.p8_uploader_reset_counter = 0

                with st.expander("🔑 सुरक्षित मास्टर फ़ाइल अपलोड गेटवे खोलें", expanded=False):
                    col_up_pass, col_up_file = st.columns(2)
                    
                    with col_up_pass:
                        # काउंटर को की (Key) के साथ जोड़कर डायनेमिक बनाया गया है ताकि एरर न आए
                        uploader_secure_password = st.text_input(
                            "🛡️ फ़ाइल अपलोडर स्पेशल पासवर्ड दर्ज करें:", 
                            type="password", 
                            key=f"p8_master_pass_widget_run_{st.session_state.p8_uploader_reset_counter}"
                        )
                    
                    with col_up_file:
                        is_password_correct = (uploader_secure_password == "admin@upload15")
                        
                        uploaded_master_file = st.file_uploader(
                            "सिस्टम में ओवरराइट करने के लिए मास्टर फ़ाइल चुनें (CSV / XLSX / XLS):", 
                            type=["csv", "xlsx", "xls"],
                            key=f"p8_master_file_widget_run_{st.session_state.p8_uploader_reset_counter}",
                            disabled=not is_password_correct
                        )
                    
                    if uploader_secure_password and not is_password_correct:
                        st.error("❌ गलत फ़ाइल अपलोडर पासवर्ड! अपलोड ब्लॉक लॉक है।")
                    elif is_password_correct:
                        st.success("🔓 पासवर्ड सत्यापित! आप फ़ाइल अपलोड कर सकते हैं।")
                        
                        if uploaded_master_file is not None:
                            st.info(f"📁ं चयनित फ़ाइल: `{uploaded_master_file.name}` प्रोसेस होने के लिए तैयार है।")
                            
                            confirm_overwrite_checkbox = st.checkbox(
                                "मैं प्रमाणित करता हूँ कि मैं पुराना मास्टर डेटा डिलीट करके इस नई फ़ाइल को लाइव डेटाबेस बनाना चाहता हूँ।",
                                key=f"p8_master_chk_run_{st.session_state.p8_uploader_reset_counter}"
                            )
                            
                            if st.button("💥 FORCE OVERWRITE COMPLETE MASTER DATABASE NOW", type="primary", use_container_width=True, disabled=not confirm_overwrite_checkbox):
                                try:
                                    if uploaded_master_file.name.endswith('.csv'):
                                        raw_uploaded_df = pd.read_csv(uploaded_master_file, dtype=str).fillna("")
                                    elif uploaded_master_file.name.endswith('.xlsx'):
                                        raw_uploaded_df = pd.read_excel(uploaded_master_file, engine='openpyxl', dtype=str).fillna("")
                                    elif uploaded_master_file.name.endswith('.xls'):
                                        try:
                                            raw_uploaded_df = pd.read_excel(uploaded_master_file, engine='xlsrd', dtype=str).fillna("")
                                        except:
                                            uploaded_master_file.seek(0)
                                            html_tables = pd.read_html(uploaded_master_file)
                                            raw_uploaded_df = html_tables[0].astype(str).fillna("") if html_tables else pd.DataFrame()
                                    
                                    if raw_uploaded_df.empty:
                                        st.error("❌ अपलोडेड फ़ाइल के अंदर कोई मान्य डेटा नहीं मिला।")
                                    else:
                                        raw_uploaded_df = raw_uploaded_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
                                        
                                        for col in DEFAULT_COLUMNS:
                                            if col not in raw_uploaded_df.columns:
                                                raw_uploaded_df[col] = ""
                                        
                                        if "Target Panel Visibility" not in raw_uploaded_df.columns or raw_uploaded_df["Target Panel Visibility"].eq("").all():
                                            raw_uploaded_df["Target Panel Visibility"] = "P2"
                                        
                                        finalized_uploaded_master = raw_uploaded_df[DEFAULT_COLUMNS].copy()
                                        save_live_data(finalized_uploaded_master)
                                        
                                        # 🔒 सुरक्षित रीसेट मैकेनिज्म: काउंटर बदलते ही विजेट फ्रेश रीबूट हो जाएगा और पुराना डेटा मिट जाएगा
                                        st.session_state.p8_uploader_reset_counter += 1
                                        
                                        st.success(f"🎉 शत-प्रतिशत सफलता! `{uploaded_master_file.name}` को नया लाइव मास्टर डेटाबेस बना दिया गया है। गेटवे को सुरक्षित लॉक कर दिया गया है।")
                                        st.balloons()
                                        st.rerun()
                                        
                                except Exception as upload_err:
                                    st.error(f"मास्टर फ़ाइल डेटा प्रोसेसिंग चक्र में तकनीकी खराबी आई: {upload_err}")

            # ----------------------------------------------------------------------
            # यहाँ से आपका पुराना कोड वापस शुरू हो जाएगा:
            # ----------------------------------------------------------------------
            st.markdown("---")
            hdr_c1_p15_show_master_db_view, hdr_c2_p15_show_master_db_view = st.columns([6, 1])
            with hdr_c1_p15_show_master_db_view:
                st.subheader("📊 Master Database List View & Advanced Operational Controls")
            with hdr_c2_p15_show_master_db_view:
                if st.button("🙈 Hide" if st.session_state.get("p8_show_master_db_view", True) else "👁️ Unhide", key="p8_show_master_db_view_toggle_btn", use_container_width=True):
                    st.session_state["p8_show_master_db_view"] = not st.session_state.get("p8_show_master_db_view", True)
                    st.rerun()

            if st.session_state.get("p8_show_master_db_view", True):
                
                # Action Toggles Column Layout
                col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
                with col_ctrl3:
                    lock_label = "🔒 लिस्ट लॉक करें (Locked)" if st.session_state.admin_lock_state else "🔓 लिस्ट अनलॉक करें (Editable)"
                    if st.button(lock_label, use_container_width=True, type="primary" if not st.session_state.admin_lock_state else "secondary", key="p8_lock_toggle_master_btn_final"):
                        st.session_state.admin_lock_state = not st.session_state.admin_lock_state
                        st.rerun()

                with col_ctrl1:
                    lbl_edit = "👀 एडमिट टेक्स्ट FUNCTION: active" if st.session_state.admin_unhide_edit else "🙈 एडमिट टेक्स्ट FUNCTION: hidden"
                    if st.button(lbl_edit, use_container_width=True, disabled=st.session_state.admin_lock_state, key="p8_edit_toggle_master_btn_final"):
                        st.session_state.admin_unhide_edit = not st.session_state.admin_unhide_edit
                        st.rerun()

                with col_ctrl2:
                    lbl_move = "👀 कॉलम मूव बटन्स: active" if st.session_state.admin_unhide_move else "🙈 कॉलम मूव बटन्स: hidden"
                    if st.button(lbl_move, use_container_width=True, key="p8_move_toggle_master_btn_final"):
                        st.session_state.admin_unhide_move = not st.session_state.admin_unhide_move
                        st.rerun()

                # ======================================================================
                # 🔀 कॉलम शिफ्टर ब्लॉक (लिस्ट लॉक होने पर यह आटोमेटिक फ्रीज हो जाएगा)
                # ======================================================================
                if st.session_state.admin_unhide_move:
                    st.info("🔀 कॉलम का क्रम बदलने के लिए सेलेक्ट करें (Select Column to Shift):")
                    
                    # 🚨 यदि लिस्ट लॉक है, तो ड्रॉपडाउन को भी डिसेबल (फ्रीज) कर दें
                    target_col = st.selectbox(
                        "मूव करने के लिए कॉलम चुनें:", 
                        options=st.session_state.admin_columns_order, 
                        disabled=st.session_state.admin_lock_state,
                        key="p8_column_shifter_select_box_final"
                    )
                    c_left, c_right = st.columns(2)
                    
                    # 🔒 सुरक्षा गेटवे: यदि लिस्ट लॉक है (admin_lock_state = True), तो बटन लॉक रहेंगे
                    if c_left.button("⬅️ Shift Left", use_container_width=True, disabled=st.session_state.admin_lock_state, key="p8_shift_left_master_btn_final"):
                        idx = st.session_state.admin_columns_order.index(target_col)
                        if idx > 0:
                            st.session_state.admin_columns_order[idx], st.session_state.admin_columns_order[idx-1] = st.session_state.admin_columns_order[idx-1], st.session_state.admin_columns_order[idx]
                            st.rerun()
                            
                    if c_right.button("➡️ Shift Right", use_container_width=True, disabled=st.session_state.admin_lock_state, key="p8_shift_right_master_btn_final"):
                        idx = st.session_state.admin_columns_order.index(target_col)
                        if idx < len(st.session_state.admin_columns_order) - 1:
                            st.session_state.admin_columns_order[idx], st.session_state.admin_columns_order[idx+1] = st.session_state.admin_columns_order[idx+1], st.session_state.admin_columns_order[idx]
                            st.rerun()

                # फ़ील्ड्स और ऑर्डर्स मैपिंग
                render_columns = [col for col in st.session_state.admin_columns_order if col in live_db.columns]
                ordered_db = live_db[render_columns].copy()
                ordered_db_display = ordered_db.rename(columns={c: get_display_name(c) for c in ordered_db.columns})
                ordered_db_display.insert(0, "S.No.", range(1, len(ordered_db_display) + 1))

                st.markdown(f"**📈 मुख्य लाइव डेटाबेस रिकॉर्ड्स की कुल संख्या:** `{len(ordered_db_display)}`")
                
                if ordered_db_display.empty:
                    st.warning("💡 वर्तमान में मास्टर डेटाबेस पूरी तरह खाली है। कृपया पहले Panel 1 से नया डेटा लोड करें।")
                else:
                    if st.session_state.admin_lock_state:
                        # लॉक मोड: केवल डेटा व्यू करने के लिए (Read-Only)
                        st.dataframe(ordered_db_display, use_container_width=True, hide_index=True)
                    else:
                        # अनलॉक मोड: ग्रिड एडिटिंग और रो डिलीट करने के लिए एक्टिवेट
                        st.info("🔓 **एडिट और डिलीट मोड सक्रिय:** आप सेल पर डबल-क्लिक करके डेटा बदल सकते हैं। किसी रो को सिलेक्ट कर कीबोर्ड से Delete बटन दबाकर रो हटा सकते हैं।")
                        
                        disabled_fields = ["S.No."]
                        # यदि 'एडमिट टेक्स्ट FUNCTION' चालू नहीं (hidden) है, तो संवेदनशील कॉलम्स लॉक रहेंगे
                        if not st.session_state.admin_unhide_edit:
                            disabled_fields.extend([get_display_name("Application Number"), get_display_name("Student Name"), get_display_name("Father Name")])

                        disabled_fields = ["S.No."]
                        # यदि 'एडमिट टेक्स्ट FUNCTION' चालू नहीं (hidden) है, तो संवेदनशील कॉलम्स लॉक रहेंगे
                        if not st.session_state.admin_unhide_edit:
                            disabled_fields.extend([get_display_name("Application Number"), get_display_name("Student Name"), get_display_name("Father Name")])
                        
                        # 🛡️ 🆕 यहाँ यह नया स्कीमा एडिटर (कॉलम और रो जोड़ने/हटाने का फ़ंक्शन) पेस्ट हो रहा है:
                        if role == "full_admin" and not st.session_state.admin_lock_state:
                            st.markdown("---")
                            st.markdown("#### 🛠️ Super-Admin Schema Editor (Add/Delete Columns & Rows)")
                            tab_col_ctrl, tab_row_ctrl = st.tabs(["📊 Dynamic Column Panel Engine", "➕ Manual Row Injector"])
                            
                            with tab_col_ctrl:
                                col_add_side, col_del_side = st.columns(2)
                                with col_add_side:
                                    st.markdown("##### ➕ नया कॉलम जोड़ें (Add Column)")
                                    new_col_input = st.text_input("नया कॉलम का सटीक नाम दर्ज करें:", key="p8_new_col_input_name").strip()
                                    if st.button("🚀 Create Column Globally", type="primary", use_container_width=True):
                                        if new_col_input and new_col_input not in live_db.columns:
                                            live_db[new_col_input] = ""
                                            if new_col_input not in DEFAULT_COLUMNS: DEFAULT_COLUMNS.append(new_col_input)
                                            if new_col_input not in st.session_state.admin_columns_order: st.session_state.admin_columns_order.append(new_col_input)
                                            save_live_data(live_db)
                                            st.success(f"🎉 कॉलम `{new_col_input}` संरचना में जुड़ गया है।")
                                            st.rerun()
                                            
                                with col_del_side:
                                    st.markdown("##### 🗑️ कॉलम हटाएं (Delete Column)")
                                    col_to_delete = st.selectbox("हटाने के लिए कॉलम चुनें:", options=[c for c in live_db.columns if c != "Target Panel Visibility"], key="p8_col_to_delete_select")
                                    confirm_col_del = st.checkbox("हाँ, मैं इस कॉलम का पूरा डेटा नष्ट करना चाहता हूँ।", key="p8_confirm_col_del_chk")
                                    if st.button("🗑️ ERASE COLUMN PERMANENT PERMANENTLY", type="primary", use_container_width=True, disabled=not confirm_col_del):
                                        if col_to_delete in live_db.columns: live_db = live_db.drop(columns=[col_to_delete])
                                        if col_to_delete in DEFAULT_COLUMNS: DEFAULT_COLUMNS.remove(col_to_delete)
                                        if col_to_delete in st.session_state.admin_columns_order: st.session_state.admin_columns_order.remove(col_to_delete)
                                        save_live_data(live_db)
                                        st.error(f"💥 कॉलम `{col_to_delete}` हटा दिया गया है!")
                                        st.rerun()

                            with tab_row_ctrl:
                                st.markdown("##### ➕ डेटाबेस में सिंगल रो इंजेक्ट करें (Add Row)")
                                if st.button("➕ Inject Blank Data Row at the End", use_container_width=True):
                                    blank_row = {c: "" for c in live_db.columns}
                                    blank_row["Target Panel Visibility"] = "P2"
                                    live_db = pd.concat([live_db, pd.DataFrame([blank_row])], ignore_index=True)
                                    save_live_data(live_db)
                                    st.success("🎉 एक खाली रो डेटाबेस के अंत में जोड़ दी गई है!")
                                    st.rerun()
                        
                        st.markdown("---")
                        
                        # 🎯 आपकी शर्त: लॉक होने पर माउस कर्सर से कॉलम हिलना बंद होगा, अनलॉक पर चालू रहेगा
                        if st.session_state.admin_lock_state:
                            # 🔒 लॉक मोड: यह माउस कर्सर से कॉलम को खींचना (Move करना) पूरी तरह बंद कर देगा
                            st.dataframe(
                                ordered_db_display, 
                                use_container_width=True, 
                                hide_index=True
                            )
                            edited_master_db = ordered_db_display
                        else:
                            # 🔓 अनलॉक मोड: यहाँ आप माउस कर्सर से कॉलम को अपनी मर्जी से आगे-पीछे हिला सकते हैं
                            edited_master_db = st.data_editor(
                                ordered_db_display,
                                use_container_width=True,
                                disabled=disabled_fields,
                                hide_index=True,
                                num_rows="dynamic",
                                key="p8_supreme_master_live_editor_grid"
                            )
                        
                        if st.button("💾 Save Grid Changes to Master CSV File", type="primary", use_container_width=True, key="p8_save_master_csv_btn"):
                            try:
                                clean_edited_master = edited_master_db.drop(columns=["S.No."], errors="ignore")
                                display_to_orig_map = {get_display_name(c): c for c in live_db.columns}
                                clean_edited_master = clean_edited_master.rename(columns=display_to_orig_map)
                                save_live_data(clean_edited_master)
                                st.success("🎉 संपूर्ण मास्टर चेंजेस लाइव डेटाबेस फ़ाइल में सुरक्षित अपडेट हो गए हैं!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"डेटाबेस अपडेट चक्र में तकनीकी समस्या आई: {e}")

                        # ======================================================================
                        # 🎓 न्यू सब-सिस्टम: Degree + Branch → Subject ऑटो-जेनरेटर
                        #    (Degree के ब्रैकेट में लिखा नंबर अपने-आप Duration कॉलम में चला जाएगा,
                        #     ब्रैकेट/उसका डेटा Degree से हट जाएगा, फिर Degree + Branch जोड़कर
                        #     "Degree (Branch)" फॉर्मेट में Subject कॉलम में लिख दिया जाएगा)
                        # ======================================================================
                        if role == "full_admin" and not st.session_state.admin_lock_state and "Degree" in live_db.columns:
                            st.markdown("---")
                            st.subheader("🎓 Degree + Branch → Subject Auto-Generator (Bracket → Duration)")
                            st.info(
                                "🔓 इस बटन को दबाने पर: Degree कॉलम में मौजूद `(...)` ब्रैकेट में अगर कोई नंबर लिखा है "
                                "तो वह नंबर उसी रो के Duration कॉलम में सेट हो जाएगा, और Degree से ब्रैकेट + उसके अंदर "
                                "का डेटा हटा दिया जाएगा। फिर Degree और Branch को जोड़कर Subject कॉलम में "
                                "`Degree (Branch)` फॉर्मेट में लिख दिया जाएगा। उदाहरण: Degree = `M.Sc.`, "
                                "Branch = `Home Science` → Subject = `M.Sc. (Home Science)`"
                            )

                            bracket_pattern = re.compile(r"\(([^)]*)\)")

                            if st.button(
                                "🚀 Process Degree/Branch → Subject & Duration (All Rows)",
                                type="primary",
                                use_container_width=True,
                                key="p8_degree_branch_subject_auto_btn"
                            ):
                                try:
                                    processed_counter = 0
                                    duration_updated_counter = 0

                                    for idx in live_db.index:
                                        degree_raw = str(live_db.at[idx, "Degree"]) if pd.notna(live_db.at[idx, "Degree"]) else ""
                                        if degree_raw.strip().lower() == "nan":
                                            degree_raw = ""

                                        branch_raw = ""
                                        if "Branch" in live_db.columns and pd.notna(live_db.at[idx, "Branch"]):
                                            branch_raw = str(live_db.at[idx, "Branch"])
                                            if branch_raw.strip().lower() == "nan":
                                                branch_raw = ""

                                        if degree_raw.strip() == "" and branch_raw.strip() == "":
                                            continue

                                        # 1️⃣ Degree में मौजूद हर ब्रैकेट ढूंढें
                                        bracket_matches = bracket_pattern.findall(degree_raw)

                                        # 2️⃣ अगर किसी ब्रैकेट के अंदर सिर्फ नंबर है तो वह Duration कॉलम में डालें
                                        for bracket_content in bracket_matches:
                                            num_match = re.search(r"\d+(\.\d+)?", bracket_content)
                                            if num_match:
                                                if "Duration" in live_db.columns:
                                                    live_db.at[idx, "Duration"] = num_match.group(0)
                                                    duration_updated_counter += 1
                                                break  # पहला नंबर वाला ब्रैकेट मिलते ही रुक जाएँ

                                        # 3️⃣ Degree से हर ब्रैकेट + उसके अंदर का डेटा हटा दें (चाहे नंबर हो या टेक्स्ट)
                                        clean_degree = bracket_pattern.sub("", degree_raw)
                                        clean_degree = re.sub(r"\s{2,}", " ", clean_degree).strip()

                                        # 4️⃣ Degree + Branch जोड़कर Subject कॉलम बनाएँ
                                        branch_clean = branch_raw.strip()
                                        if clean_degree and branch_clean:
                                            new_subject = f"{clean_degree} ({branch_clean})"
                                        elif clean_degree:
                                            new_subject = clean_degree
                                        else:
                                            new_subject = branch_clean

                                        live_db.at[idx, "Degree"] = clean_degree
                                        if "Subject" in live_db.columns:
                                            live_db.at[idx, "Subject"] = new_subject
                                        processed_counter += 1

                                    save_live_data(live_db)
                                    st.success(
                                        f"🎉 सफलता! कुल {processed_counter} रिकॉर्ड्स प्रोसेस किए गए, जिनमें से "
                                        f"{duration_updated_counter} रिकॉर्ड्स में ब्रैकेट वाला नंबर Duration कॉलम में अपडेट हुआ।"
                                    )
                                    st.balloons()
                                    st.rerun()
                                except Exception as deg_err:
                                    st.error(f"Degree/Branch → Subject प्रोसेस करने में तकनीकी समस्या आई: {deg_err}")

                        # ======================================================================
                        # 📚 न्यू सब-सिस्टम: बल्क सब्जेक्ट-वाइज ड्यूरेशन कस्टमाइज़र (सिर्फ एडमिन लॉक-सिक्योर)
                        # ======================================================================
                        if not live_db.empty and "Subject" in live_db.columns:
                            st.markdown("---")
                            st.subheader("📚 Bulk Subject-Wise Duration Settings (Admin Control)")
                            
                            # लॉक स्टेट के आधार पर एडमिन को निर्देश दिखाएं
                            if st.session_state.admin_lock_state:
                                st.warning("🔒 **यह ग्रिड अभी लॉक है:** ड्यूरेशन बदलने के लिए ऊपर जाकर पहले '🔓 लिस्ट अनलॉक करें (Editable)' बटन दबाएं।")
                            else:
                                st.info("🔓 **अनलॉक मोड सक्रिय:** अब आप किसी भी विषय के सामने उसकी कोर्स अवधि (Duration) बदल सकते हैं।")
                            
                            # 1. डेटाबेस से सभी उपलब्ध यूनीक विषयों की लिस्ट निकालें
                            unique_db_subjects = sorted([s for s in live_db["Subject"].dropna().unique() if str(s).strip() != ""])
                            
                            if not unique_db_subjects:
                                st.warning("⚠️ डेटाबेस में कोई भी विषय (Subject) नहीं मिला।")
                            else:
                                # 2. कस्टमाइज़ेशन के लिए एक डेटाफ्रेम मैट्रिक्स तैयार करें
                                subject_duration_mapping = []
                                for sub in unique_db_subjects:
                                    existing_sub_rows = live_db[live_db["Subject"] == sub]
                                    existing_duration = "3" # डिफ़ॉल्ट मान
                                    if not existing_sub_rows.empty:
                                        valid_durations = existing_sub_rows["Duration"].dropna().unique()
                                        valid_durations = [str(d).strip() for d in valid_durations if str(d).strip() != ""]
                                        if valid_durations:
                                            first_val = valid_durations[0].split('.')[0]
                                            if first_val in ["1", "2", "3", "4", "5", "6"]:
                                                existing_duration = first_val
                                    
                                    subject_duration_mapping.append({
                                        "Subject Name": sub,
                                        "Course Duration (Years)": existing_duration
                                    })
                                
                                sub_mapping_df = pd.DataFrame(subject_duration_mapping)
                                
                                # 🚨 सुरक्षा गेटवे: यदि मास्टर लिस्ट लॉक है, तो पूरा ग्रिड डिसेबल रहेगा
                                is_grid_disabled = st.session_state.admin_lock_state
                                
                                # 3. एडमिन के लिए एक इंटरैक्टिव कस्टमाइज़ेशन ग्रिड रेंडर करें
                                edited_sub_mapping_df = st.data_editor(
                                    sub_mapping_df,
                                    use_container_width=True,
                                    disabled=True if is_grid_disabled else ["Subject Name"], # लॉक होने पर पूरी टेबल फ्रीज हो जाएगी
                                    column_config={
                                        "Course Duration (Years)": st.column_config.SelectboxColumn(
                                            "Select Duration",
                                            options=["1", "2", "3", "4", "5", "6"],
                                            required=True,
                                            help="इस विषय के लिए कोर्स की कुल अवधि वर्षों में चुनें"
                                        )
                                    },
                                    key="p8_bulk_subject_duration_editor_grid_final_clean",
                                    hide_index=True
                                )
                                
                                # 🚨 सुरक्षा गेटवे 2: सेव बटन केवल तभी दिखाई देगा जब लिस्ट अनलॉक होगी
                                if not st.session_state.admin_lock_state:
                                    if st.button("💾 Apply & Update Bulk Subject Durations", type="primary", use_container_width=True, key="p8_save_bulk_sub_duration_btn"):
                                        try:
                                            bulk_update_counter = 0
                                            bulk_skip_counter = 0
                                            
                                            # ग्रिड की प्रत्येक रो को लूप करें और मास्टर डेटाबेस में बदलें
                                            for _, edit_row in edited_sub_mapping_df.iterrows():
                                                target_sub = edit_row["Subject Name"]
                                                new_duration_to_apply = edit_row["Course Duration (Years)"]
                                                
                                                # मास्टर डेटाबेस में इस सब्जेक्ट के सभी इंडेक्स ढूंढें
                                                sub_match_indices = live_db[live_db["Subject"] == target_sub].index
                                                
                                                if not sub_match_indices.empty:
                                                    for idx in sub_match_indices:
                                                        # 🚨 अगर इस रो में Duration पहले से भरा हुआ है, तो उसे छोड़ दें (ignore) और अगली रो पर जाएँ
                                                        existing_val = live_db.at[idx, "Duration"]
                                                        existing_val_str = "" if pd.isna(existing_val) else str(existing_val).strip()
                                                        if existing_val_str != "" and existing_val_str.lower() != "nan":
                                                            bulk_skip_counter += 1
                                                            continue

                                                        # Duration खाली है, तभी नया मान भरेंगे
                                                        live_db.at[idx, "Duration"] = str(new_duration_to_apply)
                                                        bulk_update_counter += 1
                                                        
                                            # परिवर्तनों को स्थायी रूप से सेव करें
                                            save_live_data(live_db)
                                            st.success(
                                                f"🎉 शत-प्रतिशत सफलता! कुल {bulk_update_counter} छात्रों का ड्यूरेशन डेटा विषय के अनुसार अपडेट कर दिया गया है। "
                                                f"({bulk_skip_counter} रिकॉर्ड्स को छोड़ दिया गया क्योंकि उनमें Duration पहले से भरा हुआ था)"
                                            )
                                            st.balloons()
                                            st.rerun()
                                        except Exception as bulk_err:
                                            st.error(f"सब्जेक्ट-वाइज ड्यूरेशन सिंक करने में तकनीकी समस्या आई: {bulk_err}")
