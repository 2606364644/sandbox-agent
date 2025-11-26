from pydantic import BaseModel, Field


class PlanningResult(BaseModel):
    todolist: str = Field(description="你规划的todolist")
