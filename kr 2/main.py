import uuid
import time
import re
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response, Header, Cookie
from pydantic import BaseModel, Field, EmailStr, field_validator
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from itsdangerous import Signer, BadSignature

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Override default 422 Unprocessable Entity for validation, returning 400 Bad Request
    to perfectly match assignment requirements, especially for Tasks 5.4/5.5.
    """
    return JSONResponse(
        status_code=400,
        content={"detail": exc.errors()},
    )


# ==========================
# 🌟 Задание 3.1
# ==========================
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    age: Optional[int] = Field(default=None, gt=0)
    is_subscribed: Optional[bool] = False

@app.post("/create_user")
def create_user(user: UserCreate):
    return user


# ==========================
# 🌟 Задание 3.2
# ==========================
sample_products = [
    {"product_id": 123, "name": "Smartphone", "category": "Electronics", "price": 599.99},
    {"product_id": 456, "name": "Phone Case", "category": "Accessories", "price": 19.99},
    {"product_id": 789, "name": "Iphone", "category": "Electronics", "price": 1299.99},
    {"product_id": 101, "name": "Headphones", "category": "Accessories", "price": 99.99},
    {"product_id": 202, "name": "Smartwatch", "category": "Electronics", "price": 299.99}
]

@app.get("/products/search")
def search_products(keyword: str, category: Optional[str] = None, limit: int = 10):
    results = []
    for p in sample_products:
        if keyword.lower() in p["name"].lower():
            if category:
                if p["category"].lower() == category.lower():
                    results.append(p)
            else:
                results.append(p)
    return results[:limit]

@app.get("/product/{product_id}")
def get_product(product_id: int):
    for p in sample_products:
        if p["product_id"] == product_id:
            return p
    raise HTTPException(status_code=404, detail="Product not found")


# ==========================
# 🌟 Задания 5.1, 5.2, 5.3
# ==========================
SECRET_KEY = "super_secret_key_for_itsdangerous"
signer = Signer(SECRET_KEY, sep=".")

class LoginData(BaseModel):
    username: str
    password: str

@app.post("/login")
async def login(request: Request, response: Response):
    # Пытаемся получить данные из формы или JSON
    content_type = request.headers.get("content-type", "")
    username = None
    password = None

    if "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
    else:
        try:
            json_data = await request.json()
            username = json_data.get("username")
            password = json_data.get("password")
        except:
            pass
            
    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing username or password")
    
    # Мок-проверка логина и пароля
    if username == "user123" and password == "password123":
        user_id = str(uuid.uuid4())
        current_time = int(time.time())
        # Строка для подписи: user_id.timestamp -> итоговая кука: user_id.timestamp.signature
        data_to_sign = f"{user_id}.{current_time}"
        session_token = signer.sign(data_to_sign.encode()).decode()
        
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=False, 
            max_age=300
        )
        return {"message": "Login successful", "session_token": session_token}
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/user")
def get_user_5_1(request: Request, response: Response):
    """
    Простой маршрут для задания 5.1
    """
    session_token = request.cookies.get("session_token")
    if not session_token:
        response.status_code = 401
        return {"message": "Unauthorized"}
        
    return {"user": "user123", "profile": "some profile info"}

@app.get("/profile")
def get_profile(request: Request, response: Response):
    """
    Защищенный маршрут для заданий 5.2 и 5.3
    Динамическое управление сессией
    """
    session_token = request.cookies.get("session_token")
    if not session_token:
        response.status_code = 401
        return {"message": "Unauthorized"}
        
    try:
        unsigned_data = signer.unsign(session_token).decode()
        parts = unsigned_data.split('.')
        if len(parts) != 2:
            response.status_code = 401
            return {"message": "Invalid session"}
            
        user_id, timestamp_str = parts
        last_active = int(timestamp_str)
        current_time = int(time.time())
        
        diff = current_time - last_active
        
        # Если с прошлой активности прошло 5 минут и более (300 сек) - сессия истекла
        if diff >= 300: 
            response.status_code = 401
            return {"message": "Session expired"}
            
        # Если от 3 до 5 минут (>= 180 и < 300) - продлеваем сессию
        if 180 <= diff < 300:
            new_data = f"{user_id}.{current_time}"
            new_token = signer.sign(new_data.encode()).decode()
            response.set_cookie(
                key="session_token",
                value=new_token,
                httponly=True,
                secure=False,
                max_age=300
            )
            
        return {"user_id": user_id, "profile_data": "Profile accessed"}
        
    except BadSignature:
        response.status_code = 401
        return {"message": "Invalid session"}
    except Exception:
        response.status_code = 401
        return {"message": "Invalid session"}


# ==========================
# 🌟 Задания 5.4, 5.5
# ==========================
class CommonHeaders(BaseModel):
    user_agent: str
    accept_language: str

    @field_validator('accept_language')
    @classmethod
    def validate_al(cls, v: str):
        if not re.match(r'^[a-zA-Z0-9,\-;\.\s\=\*q]+$', v):
            raise ValueError("Invalid Accept-Language format")
        return v

@app.get("/headers")
def read_headers(headers: CommonHeaders = Header(...)):
    """
    Автоматическое извлечение заголовков через Pydantic модель (FastAPI 0.115+)
    Если заголовки отсутствуют, возвращается ошибка валидации, которая 
    перехватывается в 400 Bad Request благодаря validation_exception_handler.
    """
    return {
        "User-Agent": headers.user_agent,
        "Accept-Language": headers.accept_language
    }

@app.get("/info")
def get_info(response: Response, headers: CommonHeaders = Header(...)):
    """
    Использование CommonHeaders, возвращение расширенного JSON 
    и кастомного заголовка ответа X-Server-Time.
    """
    response.headers["X-Server-Time"] = datetime.now().isoformat()
    return {
        "message": "Добро пожаловать! Ваши заголовки успешно обработаны.",
        "headers": {
            "User-Agent": headers.user_agent,
            "Accept-Language": headers.accept_language
        }
    }
