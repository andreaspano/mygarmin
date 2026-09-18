"""Profile page: shows the personal info stored in user/profile.yaml."""

from pathlib import Path

import streamlit as st
import yaml

PROFILE_PATH = Path("user/profile.yaml")
AVATAR_PATH = Path("user/avatar.jpg")

LABELS = {
    "garmin_id": "Garmin ID",
    "first_name": "First name",
    "surname": "Surname",
    "display_name": "Display name",
    "email": "Email",
    "gender": "Gender",
    "date_of_birth": "Date of birth",
    "height_cm": "Height",
    "weight_kg": "Weight",
    "handedness": "Handedness",
    "measurement_system": "Measurement system",
}
UNITS = {"height_cm": " cm", "weight_kg": " kg"}
CAPITALIZE_KEYS = {"gender", "handedness", "measurement_system"}

st.title("Profile")

if not PROFILE_PATH.exists():
    st.info(f"No profile file found at {PROFILE_PATH.resolve()}.")
    st.stop()

with open(PROFILE_PATH, encoding="utf-8") as f:
    profile = yaml.safe_load(f) or {}

rows = {}
for key, label in LABELS.items():
    if key not in profile:
        continue
    value = profile[key]
    if value is None:
        rows[label] = "-"
        continue
    if key in CAPITALIZE_KEYS and isinstance(value, str):
        value = value.capitalize()
    rows[label] = f"{value}{UNITS.get(key, '')}"

avatar_col, info_col = st.columns([1, 3])
with avatar_col:
    if AVATAR_PATH.exists():
        st.image(str(AVATAR_PATH), width=180)

with info_col:
    st.table(rows, border="horizontal", width="content")
