import json
import os
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/call-requests", tags=["call-requests"])

# Simple JSON storage for call requests
STORAGE_FILE = "call_requests.json"

class CallRequestCreate(BaseModel):
    name: str
    phone_number: str
    preferred_time: Optional[str] = None
    message: Optional[str] = None

class CallRequestUpdate(BaseModel):
    status: str

def get_requests():
    if not os.path.exists(STORAGE_FILE):
        return []
    try:
        with open(STORAGE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_requests(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)

@router.post("")
async def create_request(req: CallRequestCreate):
    data = get_requests()
    new_request = {
        "id": str(uuid.uuid4()),
        "name": req.name,
        "phone_number": req.phone_number,
        "preferred_time": req.preferred_time,
        "message": req.message,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    data.insert(0, new_request) # Add to top
    save_requests(data)
    return new_request

@router.get("")
async def list_requests():
    return {"items": get_requests()}

@router.put("/{req_id}")
async def update_request(req_id: str, update_data: CallRequestUpdate):
    data = get_requests()
    for req in data:
        if req["id"] == req_id:
            req["status"] = update_data.status
            save_requests(data)
            return req
    raise HTTPException(status_code=404, detail="Request not found")

@router.delete("/{req_id}")
async def delete_request(req_id: str):
    data = get_requests()
    filtered = [req for req in data if req["id"] != req_id]
    if len(filtered) == len(data):
        raise HTTPException(status_code=404, detail="Request not found")
    save_requests(filtered)
    return {"status": "deleted"}
