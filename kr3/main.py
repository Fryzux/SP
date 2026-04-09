import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials, OAuth2PasswordBearer
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from passlib.context import CryptContext
import jwt
from dotenv import load_dotenv

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import get_db_connection, init_db
from models import User, TodoCreate, TodoUpdate, TodoResponse

load_dotenv()

MODE = os.getenv("MODE", "DEV")
DOCS_USER = os.getenv("DOCS_USER", "admin")
DOCS_PASSWORD = os.getenv("DOCS_PASSWORD", "admin")
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

security_basic = HTTPBasic()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 6.2 In-memory DB
fake_users_db = {
    "user1": {
        "username": "user1",
        "hashed_password": pwd_context.hash("correctpass")
    }
}

@app.on_event("startup")
def on_startup():
    init_db()

# 6.3 Docs Auth
def verify_docs_auth(credentials: HTTPBasicCredentials = Depends(security_basic)):
    correct_username = secrets.compare_digest(credentials.username, DOCS_USER)
    correct_password = secrets.compare_digest(credentials.password, DOCS_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.get("/docs", include_in_schema=False)
async def get_documentation(username: str = Depends(verify_docs_auth)):
    if MODE == "PROD":
        raise HTTPException(status_code=404, detail="Not Found")
    return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")

@app.get("/openapi.json", include_in_schema=False)
async def openapi(username: str = Depends(verify_docs_auth)):
    if MODE == "PROD":
        raise HTTPException(status_code=404, detail="Not Found")
    return get_openapi(title="FastAPI App", version="1.0.0", routes=app.routes)

# 6.1 & 6.2 Basic Auth Endpoint
def auth_user_basic(credentials: HTTPBasicCredentials = Depends(security_basic)):
    user_dict = None
    for username, user_info in fake_users_db.items():
        if secrets.compare_digest(username, credentials.username):
            user_dict = user_info
            break
            
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
        
    if not pwd_context.verify(credentials.password, user_dict["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user_dict["username"]

@app.get("/login")
def basic_login(username: str = Depends(auth_user_basic)):
    return {"message": f"Welcome, {username}! You got my secret, welcome"}

# 6.5 & 8.1 Register
@app.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("1/minute")
def register(request: Request, user: User):
    conn = get_db_connection()
    existing_user = conn.execute("SELECT * FROM users WHERE username = ?", (user.username,)).fetchone()
    if existing_user:
        conn.close()
        raise HTTPException(status_code=409, detail="User already exists")
    
    hashed_password = pwd_context.hash(user.password)
    role = "admin" if user.username == "admin" else "user"
    
    conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                 (user.username, hashed_password, role))
    conn.commit()
    conn.close()
    return {"message": "New user created", "detail": "User registered successfully!"}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 6.4 & 6.5 JWT Login
@app.post("/login")
@limiter.limit("5/minute")
def login(request: Request, user: User):
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    
    db_user = None
    for u in users:
        if secrets.compare_digest(u["username"], user.username):
            db_user = u
            break
            
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not pwd_context.verify(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Authorization failed")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user["username"], "role": db_user["role"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# 6.4 & 7.1 JWT Protected & RBAC
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"username": username, "role": role}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")

def require_role(allowed_roles: List[str]):
    def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return current_user
    return role_checker

@app.get("/protected_resource")
def protected_resource(current_user: dict = Depends(get_current_user)):
    return {"message": "Access granted", "user": current_user["username"]}

@app.get("/admin_resource")
def admin_resource(current_user: dict = Depends(require_role(["admin"]))):
    return {"message": "Hello, Admin!"}

@app.get("/user_resource")
def user_resource(current_user: dict = Depends(require_role(["admin", "user"]))):
    return {"message": "Hello, User!"}

@app.get("/guest_resource")
def guest_resource(current_user: dict = Depends(require_role(["admin", "user", "guest"]))):
    return {"message": "Hello, Guest!"}

# 8.2 Todos CRUD
@app.post("/todos", response_model=TodoResponse, status_code=201)
def create_todo(todo: TodoCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO todos (title, description, completed) VALUES (?, ?, ?)",
                   (todo.title, todo.description, False))
    conn.commit()
    todo_id = cursor.lastrowid
    new_todo = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    conn.close()
    
    result = dict(new_todo)
    result["completed"] = bool(result["completed"])
    return result

@app.get("/todos/{todo_id}", response_model=TodoResponse)
def get_todo(todo_id: int):
    conn = get_db_connection()
    todo = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    conn.close()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    result = dict(todo)
    result["completed"] = bool(result["completed"])
    return result

@app.put("/todos/{todo_id}", response_model=TodoResponse)
def update_todo(todo_id: int, todo: TodoUpdate):
    conn = get_db_connection()
    existing_todo = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    if not existing_todo:
        conn.close()
        raise HTTPException(status_code=404, detail="Todo not found")
    
    conn.execute("UPDATE todos SET title = ?, description = ?, completed = ? WHERE id = ?",
                 (todo.title, todo.description, todo.completed, todo_id))
    conn.commit()
    updated_todo = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    conn.close()
    
    result = dict(updated_todo)
    result["completed"] = bool(result["completed"])
    return result

@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int):
    conn = get_db_connection()
    existing_todo = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    if not existing_todo:
        conn.close()
        raise HTTPException(status_code=404, detail="Todo not found")
    
    conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()
    conn.close()
    return {"message": "Todo deleted successfully"}
