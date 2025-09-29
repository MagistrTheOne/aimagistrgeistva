"""Finance management service for expenses and budgets."""

from typing import List, Optional
from uuid import uuid4

from app.adapters.redis_client import redis_adapter
from app.core.logging import get_structlog_logger
from app.domain.models import Expense, Budget, ExpenseCreateRequest, BudgetCreateRequest

logger = get_structlog_logger(__name__)


class FinanceService:
    """Service for managing expenses and budgets."""

    def __init__(self):
        self.redis = redis_adapter

    async def add_expense(self, user_id: str, request: ExpenseCreateRequest) -> Expense:
        """Add a new expense."""
        expense = Expense(
            id=uuid4(),
            user_id=user_id,
            amount=request.amount,
            category=request.category,
            description=request.description,
            merchant=request.merchant,
            date=request.date,
            payment_method=request.payment_method,
            tags=request.tags
        )

        # Store in Redis
        await self.redis.add_expense(user_id, {
            "id": str(expense.id),
            "user_id": user_id,
            "amount": expense.amount,
            "currency": expense.currency,
            "category": expense.category,
            "description": expense.description,
            "merchant": expense.merchant,
            "date": expense.date.isoformat(),
            "payment_method": expense.payment_method,
            "tags": expense.tags,
            "is_recurring": expense.is_recurring,
            "recurring_pattern": expense.recurring_pattern,
            "created_at": expense.created_at.isoformat()
        })

        logger.info("Expense added", expense_id=str(expense.id), user_id=user_id, amount=expense.amount)
        return expense

    async def get_user_expenses(self, user_id: str, limit: int = 50, category: Optional[str] = None) -> List[Expense]:
        """Get user's expenses."""
        expenses_data = await self.redis.get_user_expenses(user_id, limit)
        expenses = []

        for expense_data in expenses_data:
            expense = Expense(**expense_data)
            if category is None or expense.category == category:
                expenses.append(expense)

        return expenses

    async def create_budget(self, user_id: str, request: BudgetCreateRequest) -> Budget:
        """Create a new budget."""
        budget = Budget(
            id=uuid4(),
            user_id=user_id,
            name=request.name,
            period=request.period,
            categories=request.categories,
            total_limit=request.total_limit
        )

        # Store in Redis (simplified - in production would use proper storage)
        budget_key = f"budget:{user_id}:{budget.id}"
        await self.redis.set_json(budget_key, {
            "id": str(budget.id),
            "user_id": user_id,
            "name": budget.name,
            "period": budget.period,
            "categories": budget.categories,
            "total_limit": budget.total_limit,
            "is_active": budget.is_active,
            "created_at": budget.created_at.isoformat()
        })

        logger.info("Budget created", budget_id=str(budget.id), user_id=user_id)
        return budget

    async def analyze_expenses(self, user_id: str) -> dict:
        """Analyze user's spending patterns."""
        expenses = await self.get_user_expenses(user_id, limit=100)

        if not expenses:
            return {"message": "Нет данных для анализа"}

        # Simple analysis
        total_spent = sum(exp.amount for exp in expenses)
        categories = {}
        for exp in expenses:
            categories[exp.category] = categories.get(exp.category, 0) + exp.amount

        top_category = max(categories.items(), key=lambda x: x[1]) if categories else None

        return {
            "total_expenses": len(expenses),
            "total_amount": total_spent,
            "top_category": top_category,
            "categories_breakdown": categories,
            "average_expense": total_spent / len(expenses) if expenses else 0
        }


# Global finance service instance
finance_service = FinanceService()
