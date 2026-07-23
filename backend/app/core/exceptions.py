class DomainError(Exception):
    code: str = "domain_error"
    status_code: int = 400
    message: str = "Domain error."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        if message:
            self.message = message


class EmailAlreadyTaken(DomainError):
    code = "email_already_taken"
    status_code = 409
    message = "Email already registered."


class UserNotFound(DomainError):
    code = "user_not_found"
    status_code = 404
    message = "User not found."


class InvalidCredentials(DomainError):
    code = "invalid_credentials"
    status_code = 401
    message = "Invalid credentials."


class InvalidCurrentPassword(DomainError):
    code = "invalid_current_password"
    status_code = 400
    message = "Current password is incorrect."


class PasswordMustDiffer(DomainError):
    code = "password_must_differ"
    status_code = 400
    message = "New password must differ from the current password."


class InvalidRefreshToken(DomainError):
    code = "invalid_refresh_token"
    status_code = 401
    message = "Invalid or expired refresh token."


class RefreshTokenReuse(DomainError):
    code = "refresh_token_reuse_detected"
    status_code = 401
    message = "Refresh token reuse detected. All sessions have been revoked."


class AuthenticationRequired(DomainError):
    code = "authentication_required"
    status_code = 401
    message = "Authentication required."


class CsrfValidationFailed(DomainError):
    code = "csrf_validation_failed"
    status_code = 403
    message = "CSRF validation failed."


class UntrustedOrigin(DomainError):
    code = "untrusted_origin"
    status_code = 403
    message = "Request origin is not allowed."


class HabitNotFound(DomainError):
    code = "habit_not_found"
    status_code = 404
    message = "Habit not found."


class SavingGoalNotFound(DomainError):
    code = "saving_goal_not_found"
    status_code = 404
    message = "Saving goal not found."


class SavingContributionNotFound(DomainError):
    code = "saving_contribution_not_found"
    status_code = 404
    message = "Saving contribution not found."


class AccountNotFound(DomainError):
    code = "account_not_found"
    status_code = 404
    message = "Account not found."


class CategoryNotFound(DomainError):
    code = "category_not_found"
    status_code = 404
    message = "Category not found."


class TransactionNotFound(DomainError):
    code = "transaction_not_found"
    status_code = 404
    message = "Transaction not found."


class RecurringTransactionNotFound(DomainError):
    code = "recurring_transaction_not_found"
    status_code = 404
    message = "Recurring transaction not found."


class RecurringOccurrenceAlreadyRegistered(DomainError):
    code = "recurring_occurrence_already_registered"
    status_code = 409
    message = "This recurring occurrence has already been registered."


class RecurringRuleInactive(DomainError):
    code = "recurring_rule_inactive"
    status_code = 400
    message = "Recurring transaction must be active."


class RecurringDateNotScheduled(DomainError):
    code = "recurring_date_not_scheduled"
    status_code = 400
    message = "Transaction date is not a scheduled recurring occurrence."


class MonthlyBudgetNotFound(DomainError):
    code = "monthly_budget_not_found"
    status_code = 404
    message = "Monthly budget not found."


class MonthlyBudgetAlreadyExists(DomainError):
    code = "monthly_budget_already_exists"
    status_code = 409
    message = "A monthly budget already exists for this category and month."


class BudgetRequiresExpenseCategory(DomainError):
    code = "budget_requires_expense_category"
    status_code = 400
    message = "Monthly budgets require an expense category."


class ResourceInUse(DomainError):
    code = "resource_in_use"
    status_code = 409
    message = "Resource is in use."


class ValidationError(DomainError):
    code = "validation_error"
    status_code = 400
    message = "Invalid input."
