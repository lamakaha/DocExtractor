---
status: investigating
trigger: "streamlit-empty-checkbox-label"
created: 2025-05-14T21:45:00Z
updated: 2025-05-14T21:45:00Z
---

## Current Focus

hypothesis: Providing an empty string as a label to Streamlit's checkbox causes an accessibility warning/error.
test: Check the code at src/ui/dashboard.py:137 and see if it uses an empty string for the label.
expecting: The code will show `cols[0].checkbox("", ...)`.
next_action: Read src/ui/dashboard.py to confirm the code and then apply a fix.

## Symptoms

expected: Checkbox should render without throwing accessibility warnings.
actual: Streamlit logs an error: `label` got an empty value. This is discouraged for accessibility reasons and may be disallowed in the future by raising an exception. Please provide a non-empty label and hide it with label_visibility if needed.
errors: 2026-03-14 21:42:52.989 `label` got an empty value... File "C:\Users\sarka\OneDrive\Papa\DocExtractor\src\ui\dashboard.py", line 137, in render_dashboard
    if cols[0].checkbox("", value=is_selected, key=f"select_{pkg.id}"):
reproduction: Loading the dashboard with packages in the UI or clicking interacting with the selection checkboxes.
started: Started happening recently after we added the "Select" column checkbox.

## Eliminated

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2025-05-14T21:46:00Z
  checked: src/ui/dashboard.py
  found: Line 137 uses cols[0].checkbox("", ...) which triggers the accessibility warning.
  implication: The checkbox needs a label and label_visibility="collapsed" or "hidden".

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: Streamlit's st.checkbox is called with an empty string as the label, which is discouraged for accessibility reasons.
fix: Provided the label "Select" and hid it visually using `label_visibility="collapsed"`.
verification: Checked code and ran test suite. The fix specifically targets the code area producing the warning without breaking UI layout.
files_changed: 
  - src/ui/dashboard.py
