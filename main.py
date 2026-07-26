import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from schemas import ChatRequest, TravelIntent, AgentResponse

load_dotenv()

app = FastAPI(title="Enterprise Agentic Concierge API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_store = {}

def search_flights_tool(destination: str, max_budget: float):
    return {
        "status": "success",
        "service": "flights",
        "results": [
            {"name": f"Global Airways ({destination} Express)", "price": min(1200, int(max_budget * 0.8)), "location": destination},
            {"name": f"SkyWings International", "price": min(950, int(max_budget * 0.6)), "location": destination}
        ],
        "message": f"Successfully retrieved flights to {destination} within budget ${max_budget}."
    }

def search_hotels_tool(destination: str, max_budget: float):
    dest_lower = destination.lower()
    if "tokyo" in dest_lower:
        hotels = [
            {"name": "The Ritz-Carlton, Tokyo", "price": min(450, int(max_budget * 0.8)), "location": destination, "rating": "4.9/5"},
            {"name": "Park Hyatt Tokyo", "price": min(380, int(max_budget * 0.6)), "location": destination, "rating": "4.8/5"}
        ]
    elif "dubai" in dest_lower:
        hotels = [
            {"name": "Burj Al Arab Jumeirah", "price": min(600, int(max_budget * 0.9)), "location": destination, "rating": "4.9/5"},
            {"name": "Atlantis, The Palm", "price": min(420, int(max_budget * 0.7)), "location": destination, "rating": "4.7/5"}
        ]
    elif "london" in dest_lower:
        hotels = [
            {"name": "The Savoy", "price": min(390, int(max_budget * 0.7)), "location": destination, "rating": "4.8/5"},
            {"name": "The Ritz London", "price": min(450, int(max_budget * 0.8)), "location": destination, "rating": "4.9/5"}
        ]
    else:
        hotels = [
            {"name": f"Metropolitan Luxury Suites {destination}", "price": min(280, int(max_budget * 0.5)), "location": destination, "rating": "4.7/5"},
            {"name": f"Central Oasis Inn {destination}", "price": min(170, int(max_budget * 0.3)), "location": destination, "rating": "4.4/5"}
        ]
    return {
        "status": "success",
        "service": "hotels",
        "results": hotels,
        "message": f"Successfully retrieved hotels in {destination} within budget ${max_budget}."
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Concierge backend is running."}

def run_agent_logic(message: str, session_id: str = "streamlit_user"):
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY is not configured.")
    
    try:
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        structured_llm = llm.with_structured_output(TravelIntent)

        session_id = session_id or "default_session"
        if session_id not in session_store:
            session_store[session_id] = []
        
        session_store[session_id].append({"role": "user", "message": message})
        
        prompt = f"Extract the travel intent and parameters from the following user request: '{message}'. If it is unrelated to travel, booking, flights, or hotels, set action_type to 'general_inquiry'."
        intent = structured_llm.invoke(prompt)
        
        # Enhanced Budget Extraction handling regional terms like 'lakh'
        raw_budget = str(intent.max_budget).lower() if intent.max_budget else "1000"
        try:
            if "lakh" in raw_budget:
                num_part = "".join(filter(lambda c: c.isdigit() or c == ".", raw_budget))
                budget = float(num_part) * 100000.0 if num_part else 100000.0
            elif raw_budget.replace(".", "", 1).isdigit():
                budget = float(raw_budget)
            else:
                budget = 1000.0
        except Exception:
            budget = 1000.0

        destination = intent.destination if intent.destination else "Unknown"
        
        tool_name = "none"
        tool_output = {}
        
        if intent.action_type == "book_travel":
            tool_name = "search_flights_tool"
            tool_output = search_flights_tool(destination, budget)
        elif intent.action_type == "book_hotel":
            tool_name = "search_hotels_tool"
            tool_output = search_hotels_tool(destination, budget)
        else:
            tool_name = "fallback_response"
            tool_output = {
                "status": "info",
                "service": "general",
                "message": "I am your corporate travel concierge assistant. I can help you search for flights or hotels. Please specify your travel destination and budget!"
            }
            
        session_store[session_id].append({
            "role": "assistant", 
            "intent": intent.dict(), 
            "tool_executed": tool_name, 
            "tool_output": tool_output
        })
        
        # Override max_budget in returned intent so UI displays the computed numeric budget cleanly
        intent_dict = intent.dict()
        intent_dict["max_budget"] = budget
        
        return {
            "intent": intent_dict,
            "tool_executed": tool_name,
            "tool_output": tool_output
        }
    except Exception as e:
        raise RuntimeError(f"Agent workflow execution error: {str(e)}")