import streamlit as st
from src.services.watcher import FileWatcher

@st.cache_resource
def get_watcher_instance():
    """
    Creates and caches a single FileWatcher instance.
    Streamlit will keep this object alive across reruns.
    """
    return FileWatcher()

def start_watcher():
    watcher = get_watcher_instance()
    if not watcher.is_running:
        watcher.start(blocking=False)
        st.toast("File Watcher Started!")

def stop_watcher():
    watcher = get_watcher_instance()
    if watcher.is_running:
        watcher.stop()
        st.toast("File Watcher Stopped.")

def is_watcher_running():
    return get_watcher_instance().is_running
