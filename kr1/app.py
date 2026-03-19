from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .models import User, UserAge, Feedback

app = FastAPI()


@app.get("/")
def read_root():
    return FileResponse("kr1/index.html")

# Задание 1.3*
class CalculateRequest(BaseModel):
    num1: float
    num2: float

@app.post("/calculate")
def calculate(req: CalculateRequest):
    return {"result": req.num1 + req.num2}

# Задание 1.4
user_instance = User(name="Ваше Имя и Фамилия", id=1)

@app.get("/users")
def get_users():
    return user_instance

# Задание 1.5*
@app.post("/user")
def create_user_with_age(user: UserAge):
    is_adult = user.age >= 18
    return {
        "name": user.name,
        "age": user.age,
        "is_adult": is_adult
    }

# Задание 2.1 и 2.2*
feedbacks = []

@app.post("/feedback")
def submit_feedback(feedback: Feedback):
    feedbacks.append(feedback)
    return {"message": f"Спасибо, {feedback.name}! Ваш отзыв сохранён."}
