import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from main import app  # Importing your compiled graph

# Page Config
st.set_page_config(page_title="AutoStream AI Agent")
st.title("AutoStream AI Agent")
st.markdown("I can help you with pricing and signing up. I'll need your Name, Email, and Platform.")

# 1. Initialize Session State
# We need to mirror your 'AgentState' structure in Streamlit
if "messages" not in st.session_state:
    st.session_state.messages = []

if "lead_data" not in st.session_state:
    st.session_state.lead_data = {
        "name": None,
        "email": None,
        "platform": None
    }

# 2. Display Conversation History
for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)
    elif isinstance(msg, AIMessage):
        with st.chat_message("assistant"):
            st.markdown(msg.content)

# 3. Chat Input Handler
if prompt := st.chat_input("Type your message here..."):
    
    # A. Display User Message Immediately
    st.chat_message("user").markdown(prompt)
    
    # B. Prepare State for LangGraph
    # We must pass the EXISTING lead_data so the agent remembers what it already knows
    current_state = {
        "messages": st.session_state.messages + [HumanMessage(content=prompt)],
        "lead_data": st.session_state.lead_data
    }

    # C. Run the Graph
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Invoke the graph with the current state
                result = app.invoke(current_state)
                
                # Extract the latest response
                # The graph returns the FULL updated state
                last_message = result["messages"][-1]
                updated_lead_data = result["lead_data"]
                
                # Display the AI response
                st.markdown(last_message.content)

                # D. Update Session State (Critical Step!)
                # We overwrite our session state with the new state from LangGraph
                st.session_state.messages = result["messages"]
                st.session_state.lead_data = updated_lead_data

                # E. Check for Success (Optional UI Polish)
                if "secured your spot" in last_message.content:
                    st.success("✅ Lead Captured Successfully!")
                    with st.expander("View Captured Data"):
                        st.json(updated_lead_data)

            except Exception as e:
                st.error(f"An error occurred: {e}")

# Sidebar Debugger (Optional - helps you see the state updating in real-time)
with st.sidebar:
    st.header("Debug State")
    st.write("Current Known Details:")
    st.table(st.session_state.lead_data)
