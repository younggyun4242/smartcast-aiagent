from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import time

router = APIRouter(prefix="/admin", tags=["관리자"])

# 간단한 메트릭 저장용
_metrics = {
    "start_time": time.time(),
    "total_messages": 0,
    "error_count": 0,
    "last_message_time": None
}

class StatusResponse(BaseModel):
    """상태 응답 모델"""
    uptime_seconds: float
    total_messages: int
    error_count: int
    last_message_time: float | None
    
@router.get("/status", response_model=StatusResponse)
async def get_status():
    """서버 상태 확인"""
    try:
        current_time = time.time()
        return {
            "uptime_seconds": current_time - _metrics["start_time"],
            "total_messages": _metrics["total_messages"],
            "error_count": _metrics["error_count"],
            "last_message_time": _metrics["last_message_time"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 메트릭 업데이트 함수
def update_metrics(message_count: int = 0, error_count: int = 0):
    """메트릭 업데이트"""
    _metrics["total_messages"] += message_count
    _metrics["error_count"] += error_count
    if message_count > 0:
        _metrics["last_message_time"] = time.time() 