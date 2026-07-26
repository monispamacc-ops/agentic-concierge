from pydantic import BaseModel, Field
from typing import Optional, Union, Dict, Any

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default_session"

class TravelIntent(BaseModel):
    action_type: str = Field(
        description="The intent type: 'book_travel' for flights, 'book_hotel' for hotels, or 'general_inquiry' for anything else."
    )
    destination: Optional[str] = Field(
        None, description="The target destination city or country."
    )
    start_date: Optional[str] = Field(
        None, description="Start date of the trip if provided."
    )
    end_date: Optional[str] = Field(
        None, description="End date of the trip if provided."
    )
    max_budget: Optional[Union[float, str]] = Field(
        None, description="The maximum budget amount or price indicator provided by the user."
    )

class AgentResponse(BaseModel):
    intent: TravelIntent
    tool_executed: str
    tool_output: Dict[str, Any]