from enum import Enum
from typing import Optional
from pydantic import BaseModel
from alcf_tokens.auth import get_access_token, ServiceName

HEADERS = {
    "Authorization": f"Bearer {get_access_token(ServiceName.iri)}",
    "Content-Type": "application/json"
}


class JobState(str, Enum):
    queued = "queued"
    active = "active"
    completed = "completed"
    failed = "failed"
    canceled = "canceled"
    

class TaskStatus(str, Enum):
    pending = "pending"
    active = "active"
    completed = "completed"
    failed = "failed"


class JobStatus(BaseModel):
    state: JobState
    exit_code: int


class JobResponse(BaseModel):
    id: str
    status: JobStatus


class FilesystemResponse(BaseModel):
    task_id: str
    task_uri: str


class TaskOutputContent(BaseModel):
    content: str
    content_type: str
    start_position: int
    end_position: int


class TaskOutput(BaseModel):
    output: TaskOutputContent


class TaskResponse(BaseModel):
    id: str
    status: TaskStatus
    result: Optional[TaskOutput] = None
