from pydantic import BaseModel, Field, field_validator
import re

# Задание 1.4
class User(BaseModel):
    name: str
    id: int

# Задание 1.5* 
# (Используется отдельная модель, чтобы не конфликтовать с User из 1.4, 
# хотя в задании обе названы "Пользователь/User")
class UserAge(BaseModel):
    name: str
    age: int

# Задание 2.1 и 2.2*
class Feedback(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    message: str = Field(..., min_length=10, max_length=500)

    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        # Проверка на наличие недопустимых слов (в любых падежах)
        forbidden_pattern = re.compile(r'(кринж|рофл|вайб)', re.IGNORECASE)
        if forbidden_pattern.search(v):
            raise ValueError("Использование недопустимых слов")
        return v
