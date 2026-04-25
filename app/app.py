import streamlit as st
import time
from llm_client import stream_response, invoke_model, calculate_cost, MODELS
from logger import log_call, get_log_df

st.set_page_config(page_title="Bedrock Chatbot", page_icon="🤖", layout="wide")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")

    model_name = st.selectbox("Model", list(MODELS.keys()))
    model_id   = MODELS[model_name]
    temperature  = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
    max_tokens   = st.slider("Max Tokens", 100, 1024, 512, 50)
    system_prompt = st.text_area(
        "System Instruction",
        "You are a helpful, concise assistant.",
        height=100,
    )
    use_streaming = st.toggle("Streaming", value=True)

    st.divider()
    st.caption("📊 Session Stats")
    log_df = get_log_df()
    if not log_df.empty:
        st.metric("Total calls",  len(log_df))
        st.metric("Total cost",   f"${log_df['cost_usd'].sum():.5f}")
        st.metric("Avg latency",  f"{log_df['latency_ms'].mean():.0f} ms")
    else:
        st.info("No calls yet — start chatting!")

# ── Main ───────────────────────────────────────────────────────────────────────
st.title("🤖 Bedrock Chatbot")
st.caption(
    f"Model: `{model_id}` · Temp: `{temperature}` · "
    f"Max tokens: `{max_tokens}` · Streaming: `{'On' if use_streaming else 'Off'}`"
)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask something…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if use_streaming:
            start = time.time()
            response_text = st.write_stream(
                stream_response(
                    model_id=model_id,
                    prompt=prompt,
                    system=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            )
            latency_ms = round((time.time() - start) * 1000)
            est_in  = int(len(prompt.split()) * 1.3)
            est_out = int(len(response_text.split()) * 1.3)
            cost    = calculate_cost(model_id, est_in, est_out)
            log_call(model_id, prompt, response_text, latency_ms, est_in, est_out, cost)
        else:
            with st.spinner("Thinking…"):
                result = invoke_model(
                    model_id=model_id,
                    prompt=prompt,
                    system=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            response_text = result["text"]
            st.markdown(response_text)
            log_call(
                model_id, prompt, response_text,
                result["latency_ms"], result["input_tokens"],
                result["output_tokens"], result["cost_usd"],
            )

    st.session_state.messages.append({"role": "assistant", "content": response_text})

# ── Session logs ───────────────────────────────────────────────────────────────
st.divider()
with st.expander("📋 Session Logs", expanded=False):
    log_df = get_log_df()
    if log_df.empty:
        st.info("No calls logged yet.")
    else:
        st.dataframe(log_df, use_container_width=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Calls",  len(log_df))
        c2.metric("Total Cost",   f"${log_df['cost_usd'].sum():.5f}")
        c3.metric("Avg Latency",  f"{log_df['latency_ms'].mean():.0f} ms")
