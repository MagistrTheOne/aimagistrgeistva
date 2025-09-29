"""Automation services for AI Мага."""

from app.services.automations.task_service import task_service
from app.services.automations.finance_service import finance_service
from app.services.automations.document_service import document_service

__all__ = ["task_service", "finance_service", "document_service"]
