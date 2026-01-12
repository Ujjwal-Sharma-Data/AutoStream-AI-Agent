# AutoStream AI Agent

This is a Conversational AI Agent built for **AutoStream**, a fictional SaaS company. The agent is designed to qualify sales leads, answer pricing questions using RAG, and capture user details (Name, Email, Platform) into a structured format.

## 🛠️ Tech Stack
- **Framework:** LangGraph (Stateful Multi-Turn Conversations)
- **LLM:** Google Gemini 2.5 Flash
- **Knowledge Base:** JSON-based RAG
- **Logic:** Hybrid Approach (LLM Context Extraction + Persistent State)

## 🚀 Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone <YOUR_REPO_URL>
   cd autostream-agent

2. **Install Dependencies**
    pip install -r requirements.txt

3. **Configure API key**
    - Create a .env file in the root folder.
    - Add your Google Gemini API key:
        GOOGLE_API_KEY="your_actual_key_here"

4. **Run the Agent**
    python3 main.py

## Architecture Explanation
The system follows a cyclic **State Machine** architecture:
1.  **Input:** User message enters the graph and is appended to the persistent conversation history.
2.  **Analysis (The Brain):** The `agent_node` constructs a prompt containing the **full transcript** and the **current known state**. The LLM analyzes this to extract new entities (Name, Email, Platform) contextually.
3.  **State Merge:** Extracted entities are merged into the persistent `lead_data` dictionary.
4.  **Decision:**
    * **Missing Data:** The agent asks a follow-up question.
    * **Complete Data:** The `tool_check_node` validates the state and executes `mock_lead_capture`.
5.  **Output:** The final response is returned to the user.

### **Technical Decisions (Why LangGraph?)**
I selected **LangGraph** over AutoGen because this task requires a **deterministic control flow**. Unlike AutoGen (which is better for open-ended multi-agent debates), LangGraph allows us to define strict loops—ensuring the agent *cannot* proceed to the "Tool Trigger" step until specific data criteria (Name/Email/Platform) are met.

**State Management:**
We utilize a **Hybrid Persistence** model. Instead of relying solely on the LLM's short-term memory, we maintain a structured `AgentState` dictionary. Every turn, the LLM acts as an extractor, parsing the transcript to find new information which is permanently saved to the `lead_data` state. This ensures "perfect memory" even if the user provides details out of order or changes topics.

### **WhatsApp Deployment Plan**
To deploy this agent on WhatsApp, I would integrate the **WhatsApp Business API** with a Python webhook:
* **Webhook:** A **FastAPI** endpoint receives incoming HTTP POST requests from Meta containing the user's message and `wa_id` (phone number).
* **Session Handling:** The `wa_id` serves as the unique session key. We retrieve the user's persisted LangGraph state from a Redis database using this key.
* **Execution:** The message passes through the graph, updates the state, and the agent's text response is sent back via the `messages` API endpoint.