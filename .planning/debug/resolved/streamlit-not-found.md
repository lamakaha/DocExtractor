---
status: resolved
trigger: "The streamlit command is not recognized in the terminal."
created: 2025-01-24T12:00:00Z
updated: 2025-01-24T12:15:00Z
---

## Current Focus

hypothesis: streamlit is installed but its installation directory (Scripts) is not in the system PATH.
test: verify streamlit location and check PATH
expecting: streamlit to be in a directory not present in $env:PATH
next_action: complete task with diagnosis and fix

## Symptoms

expected: Streamlit app should launch.
actual: streamlit : The term 'streamlit' is not recognized as the name of a cmdlet, function, script file, or operable program.
errors: CommandNotFoundException in PowerShell.
reproduction: streamlit run src/ui/app.py
started: The first time I launched it.

## Eliminated

- hypothesis: streamlit is not installed in the current python environment
  evidence: pip list shows streamlit 1.55.0
  timestamp: 2025-01-24T12:05:00Z

## Evidence

- timestamp: 2025-01-24T12:05:00Z
  checked: pip list and pip show streamlit
  found: streamlit 1.55.0 is installed at C:\Users\sarka\AppData\Roaming\Python\Python313\site-packages
  implication: The executable should be in C:\Users\sarka\AppData\Roaming\Python\Python313\Scripts

- timestamp: 2025-01-24T12:05:00Z
  checked: ls C:\Users\sarka\AppData\Roaming\Python\Python313\Scripts\streamlit.exe
  found: file exists
  implication: Streamlit is installed correctly but not in PATH

- timestamp: 2025-01-24T12:05:00Z
  checked: $env:PATH
  found: C:\Users\sarka\AppData\Roaming\Python\Python313\Scripts is missing from PATH
  implication: This is why 'streamlit' command is not recognized

- timestamp: 2025-01-24T12:10:00Z
  checked: python -m streamlit --version
  found: Streamlit, version 1.55.0
  implication: Streamlit can be invoked as a python module even if its executable is not in PATH

## Resolution

root_cause: Streamlit is installed as a user-level package in `C:\Users\sarka\AppData\Roaming\Python\Python313\site-packages`, and its associated Scripts directory (`C:\Users\sarka\AppData\Roaming\Python\Python313\Scripts`) is not included in the system's PATH environment variable.
fix: Use `python -m streamlit run src/ui/app.py` to launch the application. This bypasses the need for the `streamlit` executable to be in the PATH. Alternatively, the user can add `C:\Users\sarka\AppData\Roaming\Python\Python313\Scripts` to their PATH.
verification: Confirmed that `python -m streamlit --version` successfully returns the installed version (1.55.0).
files_changed: []
