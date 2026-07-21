from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MissionCreateSchema(BaseModel):
    title: str
    province: str
    city: str
    address: Optional[str] = None
    essential_skills: List[str]
    bonus_skills: List[str] = []
    start_time: datetime
    end_time: datetime

class SendInviteSchema(BaseModel):
    mission_id: int
    volunteer_id: int

class CompleteMissionSchema(BaseModel):
    mission_id: int
    ratings: dict # {volunteer_id: rating_number}