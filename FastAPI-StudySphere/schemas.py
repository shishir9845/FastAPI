from typing import List
from pydantic import ConfigDict, Field, BaseModel

class CenterCreate(BaseModel):
    name : str = Field(..., min_length = 1)
    city : str = Field(..., min_length=1)

class CenterOut(BaseModel):
    id : int
    name : str
    city : str
    model_config = ConfigDict(from_attributes = True)

class SessionCreate(BaseModel):
    student_name : str = Field(..., min_length = 1)
    status : str = Field(..., min_length = 1)
    duration : int = Field(..., ge = 15)

class SessionOut(BaseModel):
    id : int
    student_name : str
    status : str
    duration : int
    model_config = ConfigDict(from_attributes = True)

class CenterWithSessions(BaseModel):
    id : int
    name : str
    city : str
    sessions : List[SessionOut]
    model_config = ConfigDict(from_attributes = True)