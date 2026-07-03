from typing import List

from pydantic import BaseModel

from app.models.TaskUpdate import TaskUpdate


class TaskBulkUpdate(BaseModel):
    tasks: List[TaskUpdate]