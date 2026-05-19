from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Union
from datetime import datetime
import uuid

app = FastAPI(
    title="Smart Campus — Analytics Service API",
    version="1.0.0",
    description="Mock Server sử dụng FastAPI map chuẩn hóa 100% theo template Lab 02"
)

# --- 1. ĐỊNH NGHĨA SCHEMAS THEO TEMPLATE MỚI ---

class HealthStatus(BaseModel):
    status: str = "ok"
    service: str = "analytics-service"
    time: datetime

class Alert(BaseModel):
    id: uuid.UUID
    sourceService: str
    alertType: str # UNAUTHORIZED_ACCESS, SENSOR_THRESHOLD_EXCEEDED, SYSTEM_ERROR
    severity: str # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    relatedEventId: Optional[uuid.UUID] = None
    status: str # OPEN, ACKNOWLEDGED, RESOLVED
    createdAt: datetime
    resolvedAt: Optional[datetime] = None

class AlertPageResponse(BaseModel):
    items: List[Alert]

class SensorEvent(BaseModel):
    eventType: str = "SENSOR_READING"
    eventId: uuid.UUID
    deviceId: str
    metric: str
    value: float
    unit: str
    timestamp: datetime

class AccessEvent(BaseModel):
    eventType: str = "ACCESS_CHECK"
    eventId: uuid.UUID
    gateId: str
    cardId: str
    decision: str # ALLOW, DENY
    timestamp: datetime

class EventAccepted(BaseModel):
    eventId: uuid.UUID
    acceptedAt: datetime

# --- KHUNG TẠO LỖI STANDARD PROBLEM DETAILS (RFC 7807) ---
def make_problem_response(status_code: int, title: str, detail: str, instance: str, type_url: str = "https://campus.local/errors/validation"):
    return JSONResponse(
        status_code=status_code,
        content={
            "type": type_url,
            "title": title,
            "status": status_code,
            "detail": detail,
            "instance": instance,
            "errors": []
        },
        headers={"Content-Type": "application/problem+json"}
    )

# --- 2. TRIỂN KHAI CÁC ENDPOINT MOCK KHỚP PATHS ---

@app.get("/health", response_model=HealthStatus, tags=["health"])
def get_health():
    return {
        "status": "ok",
        "service": "analytics-service",
        "time": datetime.utcnow()
    }

@app.get("/alerts/recent", response_model=AlertPageResponse, tags=["alerts"])
def get_recent_alerts(request: Request, limit: int = Query(20, ge=1, le=100)):
    # Giả lập check Token an ninh đơn giản để ăn khớp case 401 của đề bài
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return make_problem_response(
            status_code= status.HTTP_401_UNAUTHORIZED,
            title="Chua xac thuc",
            detail="Thieu hoac sai Bearer Token o header",
            instance="/alerts/recent",
            type_url="https://campus.local/errors/unauthorized"
        )
        
    mock_data = [
        {
            "id": uuid.uuid4(),
            "sourceService": "access-gate",
            "alertType": "UNAUTHORIZED_ACCESS",
            "severity": "HIGH",
            "message": "Phat hien the khong hop le quet lien tuc tai GATE-01",
            "relatedEventId": uuid.uuid4(),
            "status": "OPEN",
            "createdAt": datetime.utcnow(),
            "resolvedAt": None
        }
    ]
    return {"items": mock_data}

@app.post("/events", response_model=EventAccepted, status_code=201, tags=["events"])
async def create_campus_event(request: Request):
    try:
        body = await request.json()
    except Exception:
        return make_problem_response(400, "Du lieu sai dinh dang", "Payload gui len khong phai JSON hop le", "/events")

    # Xử lý đa hình (Polymorphism) dựa vào trường discriminator: eventType
    event_type = body.get("eventType")
    if not event_type:
        return make_problem_response(422, "Vi pham quy tac nghiep vu", "Thieu truong discriminator 'eventType'", "/events")

    if event_type not in ["SENSOR_READING", "ACCESS_CHECK"]:
        return make_problem_response(422, "Vi pham quy tac nghiep vu", f"eventType '{event_type}' khong hop le", "/events")

    event_id_str = body.get("eventId")
    if not event_id_str:
        return make_problem_response(400, "Du lieu sai dinh dang", "Thieu truong bat buoc 'eventId'", "/events")
        
    # Giả lập tính năng Idempotency (Chống trùng lặp tin nhắn) - Case lỗi 409
    if event_id_str == "00000000-0000-0000-0000-000000000000":
        return make_problem_response(
            status_code=409,
            title="Xung dot nghiep vu",
            detail="eventId nay da duoc xu ly truoc do (Trung lap tin nhan)",
            instance="/events",
            type_url="https://campus.local/errors/conflict"
        )

    return {
        "eventId": uuid.UUID(event_id_str),
        "acceptedAt": datetime.utcnow()
    }