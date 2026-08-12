from pydantic import BaseModel, Field

class UserProfile(BaseModel):
    name: str = Field(default="", max_length=200)
    profession: str = Field(default="", max_length=200)
    preferences: list[str] = Field(default_factory=list)
