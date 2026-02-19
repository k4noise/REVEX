import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Привет!"}

@app.get("/ping")
async def ping():
    return {"status": "ok", "answer": "pong"}

def run_dev():
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

def run_prod():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)