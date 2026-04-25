import pandas as pd
import streamlit as st

def _init():
    if "call_log" not in st.session_state:
        st.session_state.call_log = []

def log_call(model_id, prompt, response_text, latency_ms,
             input_tokens=0, output_tokens=0, cost_usd=0.0):
    _init()
    st.session_state.call_log.append({
        "time":             pd.Timestamp.now().strftime("%H:%M:%S"),
        "model":            model_id,
        "prompt":           prompt[:60] + ("…" if len(prompt) > 60 else ""),
        "response_preview": response_text[:80] + ("…" if len(response_text) > 80 else ""),
        "input_tokens":     input_tokens,
        "output_tokens":    output_tokens,
        "latency_ms":       latency_ms,
        "cost_usd":         cost_usd,
    })

def get_log_df():
    _init()
    return pd.DataFrame(st.session_state.call_log)
