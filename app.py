import streamlit as st
import os
from main import run_agent_logic

st.set_page_config(page_title="Enterprise Agentic Concierge", page_icon="✈️", layout="centered")

st.title("✈️ Enterprise Agentic Concierge")
st.write("Your AI-powered corporate travel assistant (Robust Error-Handling Enabled).")

# Securely load API key from Streamlit secrets if running on cloud
if "GROQ_API_KEY" in st.secrets:
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask to book a flight, hotel, or type an unrelated question to test fallback..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Agent is analyzing request..."):
            try:
                data = run_agent_logic(message=prompt, session_id="streamlit_user")
                
                intent = data.get("intent", {})
                tool_output = data.get("tool_output", {})
                
                reply = f"**Intent Detected:** `{intent.get('action_type')}`\n"
                
                service = tool_output.get("service")
                results = tool_output.get("results", [])
                
                if service == "flights" and results:
                    reply += f"- **Destination:** {intent.get('destination')}\n"
                    reply += f"- **Max Budget:** ${intent.get('max_budget')}\n\n**Flights Retrieved:**\n"
                    for item in results:
                        reply += f"- ✈️ {item['name']} - ${item['price']} to {item['location']}\n"
                elif service == "hotels" and results:
                    reply += f"- **Destination:** {intent.get('destination')}\n"
                    reply += f"- **Max Budget:** ${intent.get('max_budget')}\n\n**Hotels Retrieved:**\n"
                    for item in results:
                        reply += f"- 🏨 {item['name']} ({item['rating']}) - ${item['price']}/night in {item['location']}\n"
                else:
                    reply += f"\n💡 {tool_output.get('message', 'How can I assist with your corporate travel?')}"
                
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
                
            except Exception as e:
                st.error(f"Error processing request: {e}")