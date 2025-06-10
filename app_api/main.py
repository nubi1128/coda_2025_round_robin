from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.post("/payload")
async def echo(request: Request):
    data = await request.json()
    return JSONResponse(content=data)