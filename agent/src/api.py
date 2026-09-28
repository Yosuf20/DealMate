# agent/src/api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from agent.src.supervisor import run_dealsetu
from agent.src.tools.whatsapp import (
    approve_pending_message,
    cancel_pending_message,
    list_pending_messages,
    whatsapp_request,
)

app = FastAPI()

class SearchRequest(BaseModel):
    query: str


class WhatsAppSendRequest(BaseModel):
    seller: str = ""
    phone: str
    message: str = Field(min_length=1, max_length=4096)
    request_id: str = "adhoc"


@app.post("/search")
def search(req: SearchRequest):
    return run_dealsetu(req.query)


@app.get("/whatsapp/status")
def whatsapp_status():
    try:
        return whatsapp_request("GET", "/whatsapp/status")
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/whatsapp/qr")
def whatsapp_qr():
    try:
        return whatsapp_request("GET", "/whatsapp/qr")
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.post("/whatsapp/connect")
def whatsapp_connect():
    try:
        return whatsapp_request("POST", "/whatsapp/connect")
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.post("/whatsapp/disconnect")
def whatsapp_disconnect():
    try:
        return whatsapp_request("POST", "/whatsapp/disconnect")
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.post("/whatsapp/send")
def whatsapp_send(req: WhatsAppSendRequest):
    try:
        return {
            "success": True,
            **whatsapp_request(
                "POST",
                "/whatsapp/send",
                {
                    "seller": req.seller,
                    "phone": req.phone,
                    "message": req.message,
                    "requestId": req.request_id,
                },
            ),
        }
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/whatsapp/pending")
def whatsapp_pending():
    return {"messages": list_pending_messages()}


@app.post("/whatsapp/pending/{message_id}/send")
def whatsapp_send_pending(message_id: str):
    try:
        return approve_pending_message(message_id)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/whatsapp/pending/{message_id}/cancel")
def whatsapp_cancel_pending(message_id: str):
    try:
        return cancel_pending_message(message_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/whatsapp/messages")
def whatsapp_messages():
    try:
        return {"messages": whatsapp_request("GET", "/whatsapp/messages")}
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error