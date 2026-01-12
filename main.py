import json
import operator
from typing import TypedDict, Annotated, List
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

#State function (For retaining memory across 5-6 conversation turns)

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    lead_data: dict     #to store name email and platform

#knowledge base (Retrieve pricing from json)
def retrieve_knowledge():
    try:
        with open("knowledge_base.json", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "Error: Knowledge base file not found."
    
#Lead capture tool (mock api function)
def mock_lead_capture(name: str , email: str, platform: str):
    #Simulates sending lead data to a backend
    print(f"\n[Tool Executed] Lead captured: Name: {name}, Email: {email}, Platform: {platform}")
    return "Lead processed"

#Core Agent (Node)
def agent_node(state: AgentState):
    messages = state["messages"]
    # Load the EXISTING data we have already captured
    current_data = state["lead_data"]

    #History of conversation
    history_text=""
    for msg in messages:
        role='User' if isinstance(msg, HumanMessage) else 'Agent'
        history_text+=f"{role}: {msg.content}\n"

    #Injecting knowledge base
    kb_content=retrieve_knowledge()

    # The Dynamic Prompt
    # We ask the LLM to output a JSON containing the RESPONSE text AND the EXTRACTED data.
    system_prompt = f"""
    You are a sales assistant for AutoStream.
    
    KNOWLEDGE BASE:
    {kb_content}
    
    CURRENT CAPTURED DATA:
    Name: {current_data.get('name') or 'Missing'}
    Email: {current_data.get('email') or 'Missing'}
    Platform: {current_data.get('platform') or 'Missing'}

    TASK:
    1. Read the TRANSCRIPT below.
    2. Look for new details (Name, Email, or Platform) in the user's latest messages.
       - BE SMART: If the Agent asked "What is your name?" and user said "Ujjwal", EXTRACT "Ujjwal" as Name.
       - Platforms can be ANY social media (LinkedIn, X, Twitch, etc.).
    3. Generate a JSON response strictly in this format:
    
    {{
      "response_text": "Your reply to the user here...",
      "extracted_name": "Name found in transcript or null",
      "extracted_email": "Email found in transcript or null",
      "extracted_platform": "Platform found in transcript or null"
    }}

    RULES:
    - If you have ALL 3 details (Current Data + Extracted), your "response_text" should just be "Great, processing..." because the tool will run.
    - If details are missing, your "response_text" should politely ask for the missing ones.
    """

    # Send the Transcript + Prompt to the LLM
    final_prompt = f"TRANSCRIPT:\n{history_text}\n\n{system_prompt}"
    
    response = llm.invoke([HumanMessage(content=final_prompt)])
    
    # 3. Parse LLM Output (Dynamic Extraction)
    content = response.content
    # Clean up markdown if Gemini adds it
    content = content.replace("```json", "").replace("```", "").strip()
    
    ai_reply = "I'm having trouble connecting." # Fallback
    
    try:
        data = json.loads(content)
        ai_reply = data.get("response_text", "")
        
        # If LLM found a new name, we update our state. If not, we keep the old one.
        if data.get("extracted_name"):
            current_data["name"] = data["extracted_name"]
        if data.get("extracted_email"):
            current_data["email"] = data["extracted_email"]
        if data.get("extracted_platform"):
            current_data["platform"] = data["extracted_platform"]
            
    except json.JSONDecodeError:
        # Fallback if LLM messes up JSON (Rare with 2.5 Flash)
        ai_reply = response.content

    # We return the AI's text reply AND the updated lead_data
    return {
        "messages": [AIMessage(content=ai_reply)],
        "lead_data": current_data,
    }

#Tool Execution (Node)
def tool_check_node(state: AgentState):
    lead_data = state["lead_data"]
    
    # Checks if we have all 3 pieces of data
    # We check if they are "Truthy" (not None and not empty string)
    if lead_data.get("name") and lead_data.get("email") and lead_data.get("platform"):
        
        # Execute the Tool
        mock_lead_capture(
            lead_data["name"],
            lead_data["email"],
            lead_data["platform"],
        )
        
        # Reset data (optional, but good for flow) or just end
        return {
            "messages": [
                AIMessage(
                    content=f"Thanks {lead_data['name']}! I've secured your spot for {lead_data['platform']}."
                )
            ]
        }

    return {}
#Graph setup
workflow=StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tool_checker", tool_check_node)

workflow.set_entry_point("agent")
workflow.add_edge("agent", "tool_checker")
workflow.add_edge("tool_checker", END)

app = workflow.compile()

#Runner (for local testing)
if __name__ == "__main__":
    print("AutoStream Agent Started. Type 'quit' to exit.")
    print("Try asking: 'Tell me about the Pro plan'")

    state = {
    "messages": [],
    "lead_data": {
        "name": None,
        "email": None,
        "platform": None
    }
}
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["quit", "exit"]:
            break

        state["messages"].append(HumanMessage(content=user_input))

        # Run the graph
        result = app.invoke(state)
        

       # Update State
        state = result
        
        # Get the Agent's last reply
        agent_reply = state['messages'][-1].content
        print(f"Agent: {agent_reply}")

        # FIX: Check if the success message was sent
        if "secured your spot" in agent_reply:
            print("\n-------------------------------------------------")
            print("Lead Captured Successfully!")
            print("-------------------------------------------------")
            break