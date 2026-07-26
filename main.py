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

# Mock Tool 1: Dynamic Flight Search with Dynamic Currency Support
def search_flights_tool(destination: str, max_budget: float, currency_symbol: str = "₹"):
    return {
        "status": "success",
        "service": "flights",
        "results": [
            {"name": f"Global Airways ({destination} Express)", "price": f"{currency_symbol}{min(95000 if currency_symbol == '₹' else 1200, int(max_budget * 0.8)):,}", "location": destination},
            {"name": f"SkyWings International", "price": f"{currency_symbol}{min(75000 if currency_symbol == '₹' else 950, int(max_budget * 0.6)):,}", "location": destination}
        ],
        "message": f"Successfully retrieved flights to {destination} within budget {currency_symbol}{max_budget:,.2f}."
    }

# Mock Tool 2: Distinct Real-World Hotel Search with Dynamic Currency Support
def search_hotels_tool(destination: str, max_budget: float, currency_symbol: str = "₹"):
    dest_lower = destination.lower()
    if "tokyo" in dest_lower:
        hotels = [
            {"name": "The Ritz-Carlton, Tokyo", "price": f"{currency_symbol}{min(35000 if currency_symbol == '₹' else 450, int(max_budget * 0.8)):,}", "location": destination, "rating": "4.9/5"},
            {"name": "Park Hyatt Tokyo", "price": f"{currency_symbol}{min(28000 if currency_symbol == '₹' else 380, int(max_budget * 0.6)):,}", "location": destination, "rating": "4.8/5"}
        ]
    elif "dubai" in dest_lower:
        hotels = [
            {"name": "The Burj Al Arab", "price": f"{currency_symbol}{min(45000 if currency_symbol == '₹' else 600, int(max_budget * 0.9)):,}", "location": destination, "rating": "4.9/5"},
            {"name": "Atlantis, The Palm", "price": f"{currency_symbol}{min(32000 if currency_symbol == '₹' else 420, int(max_budget * 0.7)):,}", "location": destination, "rating": "4.7/5"}
        ]
    elif "london" in dest_lower:
        hotels = [
            {"name": "The Savoy", "price": f"{currency_symbol}{min(30000 if currency_symbol == '₹' else 390, int(max_budget * 0.7)):,}", "location": destination, "rating": "4.8/5"},
            {"name": "The Ritz London", "price": f"{currency_symbol}{min(35000 if currency_symbol == '₹' else 450, int(max_budget * 0.8)):,}", "location": destination, "rating": "4.9/5"}
        ]
    else:
        hotels = [
            {"name": f"Metropolitan Luxury Suites {destination}", "price": f"{currency_symbol}{min(22000 if currency_symbol == '₹' else 280, int(max_budget * 0.5)):,}", "location": destination, "rating": "4.7/5"},
            {"name": f"Central Oasis Inn {destination}", "price": f"{currency_symbol}{min(14000 if currency_symbol == '₹' else 170, int(max_budget * 0.3)):,}", "location": destination, "rating": "4.4/5"}
        ]
    return {
        "status": "success",
        "service": "hotels",
        "results": hotels,
        "message": f"Successfully retrieved hotels in {destination} within budget {currency_symbol}{max_budget:,.2f}."
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Concierge backend is running."}

@app.post("/parse-intent", response_model=TravelIntent)
def parse_user_intent(request: ChatRequest):
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured.")
    
    try:
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        structured_llm = llm.with_structured_output(TravelIntent)
        prompt = f"Extract the travel intent and parameters from the following user request: '{request.message}'"
        return structured_llm.invoke(prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run-agent", response_model=AgentResponse)
def run_agent_workflow(request: ChatRequest):
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured.")
    
    try:
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        structured_llm = llm.with_structured_output(TravelIntent)

        session_id = request.session_id or "default_session"
        if session_id not in session_store:
            session_store[session_id] = []
        
        session_store[session_id].append({"role": "user", "message": request.message})
        
        prompt = f"Extract the travel intent and parameters from the following user request: '{request.message}'. If it is unrelated to travel, booking, flights, or hotels, set action_type to 'general_inquiry'."
        intent = structured_llm.invoke(prompt)
        
        raw_message = request.message.lower()
        currency_symbol = "$" if ("$" in raw_message or "dollar" in raw_message or "usd" in raw_message) else "₹"
        
        raw_budget = str(intent.max_budget).lower() if intent.max_budget else ("1000" if currency_symbol == "$" else "100000")
        try:
            if "lakh" in raw_budget:
                num_part = "".join(filter(lambda c: c.isdigit() or c == ".", raw_budget))
                budget = float(num_part) * 100000.0 if num_part else 100000.0
            elif raw_budget.replace(".", "", 1).isdigit():
                budget = float(raw_budget)
            else:
                budget = 1000.0 if currency_symbol == "$" else 100000.0
        except Exception:
            budget = 1000.0 if currency_symbol == "$" else 100000.0

        destination = intent.destination if intent.destination else "Unknown"
        
        tool_name = "none"
        tool_output = {}
        
        if intent.action_type == "book_travel":
            tool_name = "search_flights_tool"
            tool_output = search_flights_tool(destination, budget, currency_symbol)
        elif intent.action_type == "book_hotel":
            tool_name = "search_hotels_tool"
            tool_output = search_hotels_tool(destination, budget, currency_symbol)
        else:
            tool_name = "fallback_response"
            tool_output = {
                "status": "info",
                "service": "general",
                "message": f"I am your corporate travel concierge assistant. Please specify your destination and budget in {('USD ($)' if currency_symbol == '$' else 'INR (₹)')}!"
            }
            
        session_store[session_id].append({
            "role": "assistant", 
            "intent": intent.dict(), 
            "tool_executed": tool_name, 
            "tool_output": tool_output
        })
        
        intent_dict = intent.dict()
        intent_dict["max_budget"] = f"{currency_symbol}{budget:,.2f}"
        
        return AgentResponse(
            intent=intent_dict,
            tool_executed=tool_name,
            tool_output=tool_output
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent workflow execution error: {str(e)}")

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
        
        raw_message = str(message).lower()
        currency_symbol = "$" if ("$" in raw_message or "dollar" in raw_message or "usd" in raw_message) else "₹"
        
        raw_budget = str(intent.max_budget).lower() if intent.max_budget else ("1000" if currency_symbol == "$" else "100000")
        try:
            if "lakh" in raw_budget:
                num_part = "".join(filter(lambda c: c.isdigit() or c == ".", raw_budget))
                budget = float(num_part) * 100000.0 if num_part else 100000.0
            elif raw_budget.replace(".", "", 1).isdigit():
                budget = float(raw_budget)
            else:
                budget = 1000.0 if currency_symbol == "$" else 100000.0
        except Exception:
            budget = 1000.0 if currency_symbol == "$" else 100000.0

        destination = intent.destination if intent.destination else "Unknown"
        
        tool_name = "none"
        tool_output = {}
        
        if intent.action_type == "book_travel":
            tool_name = "search_flights_tool"
            tool_output = search_flights_tool(destination, budget, currency_symbol)
        elif intent.action_type == "book_hotel":
            tool_name = "search_hotels_tool"
            tool_output = search_hotels_tool(destination, budget, currency_symbol)
        else:
            tool_name = "fallback_response"
            tool_output = {
                "status": "info",
                "service": "general",
                "message": f"I am your corporate travel concierge assistant. Please specify your destination and budget in {('USD ($)' if currency_symbol == '$' else 'INR (₹)')}!"
            }
            
        session_store[session_id].append({
            "role": "assistant", 
            "intent": intent.dict(), 
            "tool_executed": tool_name, 
            "tool_output": tool_output
        })
        
        intent_dict = intent.dict()
        intent_dict["max_budget"] = f"{currency_symbol}{budget:,.2f}"
        
        return {
            "intent": intent_dict,
            "tool_executed": tool_name,
            "tool_output": tool_output
        }
    except Exception as e:
        raise RuntimeError(f"Agent workflow execution error: {str(e)}")