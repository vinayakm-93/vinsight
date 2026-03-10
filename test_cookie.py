from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/set")
def set_cookie(response: Response):
    response.set_cookie("access_token", "Bearer mysecrettoken123", httponly=True)
    return {"msg": "cookie set"}

@app.get("/get")
def get_cookie(request: Request):
    token = request.cookies.get("access_token")
    return {"token": token}

client = TestClient(app)
res_set = client.get("/set")
print("Set-Cookie:", res_set.headers.get("set-cookie"))

res_get = client.get("/get", headers={"cookie": "access_token=Bearer mysecrettoken123"})
print("Got back directly:", res_get.json())

res_get_strict = client.get("/get", headers={"cookie": "access_token=\"Bearer mysecrettoken123\""})
print("Got back strict:", res_get_strict.json())
