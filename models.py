from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    action = Column(String)
    payload = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)