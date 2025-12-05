"""Telemetry data for VRF generator"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel
from src.logger import Logger

logger = Logger("vrf-telemetry")


class WaitReason(Enum):
    """Wait reason"""
    BOT_CHECK = "bot_check"
    REDIRECT = "redirect"
    SCROLL = "scroll"
    MOUSE_MOVE = "mouse_move"
    HUMAN_INTERACTION = "human_interaction"  # combined scroll+mouse
    SESSION_ERROR = "session_error"
    NAVIGATION_ERROR = "navigation_error"
    PAGE_LOAD = "page_load"
    AJAX_REQUEST = "ajax_request"
    IMAGE_BLOCK = "image_block"
    OTHER = "other"


class WaitEvent(BaseModel):
    """Wait event"""
    duration: float
    reason: WaitReason
    context: Optional[str] = None  # e.g., "chapter_page_load"


class VRFGeneratorTelemetry():
    """Telemetry data for VRF generator"""
    def __init__(self, url: Optional[str] = None):
        self.url = url
        self.allowed_requests = 0
        self.captured_requests = 0
        self.denied_requests = 0
        self.total_requests = 0
        self.wait: List[WaitEvent] = []
        self.silent_errors: List[Exception] = []
        self.errors: List[Exception] = []
        self.warnings: List[str] = []

    # --- Request logging ---
    def log_allowed(self, url: str, context: Optional[str] = None):
        """Log allowed requests"""
        self.allowed_requests += 1
        self.total_requests += 1
        logger.debug(f"[ALLOWED] {url} | context={context}")

    def log_captured(self, url: str, context: Optional[str] = None):
        """Log captured requests"""
        self.captured_requests += 1
        self.total_requests += 1
        logger.debug(f"[CAPTURED] {url} | context={context}")

    def log_denied(self, url: str, context: Optional[str] = None):
        """Log denied requests"""
        self.denied_requests += 1
        self.total_requests += 1
        logger.debug(f"[DENIED] {url} | context={context}")

    # --- Wait events ---
    def log_wait(self, duration: float, reason: WaitReason, context: Optional[str] = None):
        """Log wait event"""
        self.wait.append(WaitEvent(duration=duration, reason=reason, context=context))
        logger.debug(f"[WAIT] {reason} for {duration:.2f}s | context={context}")

    # --- Errors ---
    def record_error(self, error: Exception, fatal: bool = False, context: Optional[str] = None):
        """Record an error once; fatal goes to errors, otherwise to silent_errors"""
        if fatal:
            self.errors.append(error)
            logger.error(f"[ERROR] {error} | context={context}")
        else:
            self.silent_errors.append(error)
            logger.debug(f"[SILENT ERROR] {error} | context={context}")

    # --- Warnings ---
    def record_warning(self, message: str, context: Optional[str] = None):
        """Log warning"""
        self.warnings.append(message)
        logger.warning(f"[WARNING] {message} | context={context}")

    # --- Snapshot ---
    def to_dict(self):
        """Return full telemetry snapshot"""
        return {
            "url": self.url,
            "allowed_requests": self.allowed_requests,
            "captured_requests": self.captured_requests,
            "denied_requests": self.denied_requests,
            "total_requests": self.total_requests,
            "wait_events": [e.model_dump() for e in self.wait],
            "silent_errors_count": len(self.silent_errors),
            "errors_count": len(self.errors),
            "warnings_count": len(self.warnings),
            "total_duration": sum(e.duration for e in self.wait),
        }
