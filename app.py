import os
import streamlit as st
from main import run_agent_logic

# Page Configuration
st.set_page_config(
    page_title="Enterprise Agentic Concierge",
    page_icon="✈️",
    layout="centered"
)

# Custom Styling for High-End Dark Interface
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stTextInput textarea {
        color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("# ✈️ Enterprise Agentic Concierge")
st.markdown("Your AI-powered corporate travel assistant (Robust Error-Handling Enabled).")

# Initialize Session State History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "data" in message and message["data"]:
            data = message["data"]
            intent = data.get("intent", {})
            tool_name = data.get("tool_executed", "")
            tool_output = data.get("tool_output", {})
            
            with st.expander("🔍 View Agent Execution Details"):
                st.markdown(f"**Intent Detected:** `{intent.get('action_type', 'unknown')}`")
                st.markdown(f"- **Destination:** {intent.get('destination', 'N/A')}")
                st.markdown(f"- **Max Budget:** {intent.get('max_budget', 'N/A')}")
                
                if tool_name and tool_name != "none":
                    st.markdown(f"**Tool Executed:** `{tool_name}`")
                    if "results" in tool_output:
                        st.markdown("**Retrieved Options:**")
                        for item in tool_output["results"]:
                            st.markdown(f"- ✈️ {item.get('name', 'Option')} - {item.get('price', '')} to {item.get('location', '')}")
                    if "message" in tool_output:
                        st.info(tool_output["message"])

# User Chat Input
if user_input := st.chat_input("I want to book a flight for London under 50,000 rupees..."):
    # Append User Message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Run Agent Logic & Handle Errors Gracefully
    with st.chat_message("assistant"):
        with st.spinner("Processing request through agent workflow..."):
            try:
                # Check for API key in Streamlit secrets or environment
                if "GROQ_API_KEY" in st.secrets:
                    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
                
                response_data = run_agent_logic(user_input)
                
                intent = response_data.get("intent", {})
                tool_name = response_data.get("tool_executed", "")
                tool_output = response_data.get("tool_output", {})
                
                response_content = tool_output.get("message", "Request processed successfully.")
                st.markdown(response_content)
                
                with st.expander("🔍 View Agent Execution Details"):
                    st.markdown(f"**Intent Detected:** `{intent.get('action_type', 'unknown')}`")
                    st.markdown(f"- **Destination:** {intent.get('destination', 'N/A')}")
                    st.markdown(f"- **Max Budget:** {intent.get('max_budget', 'N/A')}")
                    
                    if tool_name and tool_name != "none":
                        st.markdown(f"**Tool Executed:** `{tool_name}`")
                        if "results" in tool_output:
                            st.markdown("**Retrieved Options:**")
                            for item in tool_output["results"]:
                                st.markdown(f"- ✈️ {item.get('name', 'Option')} - {item.get('price', '')} to {item.get('location', '')}")
                        if "message" in tool_output:
                            st.info(tool_output["message"])
                
                # Save Assistant Response in History
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_content,
                    "data": response_data
                })
                
            except Exception as e:
                error_msg = f"Error processing request: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })