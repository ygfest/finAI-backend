from fastapi import HTTPException

class TodoError(HTTPException):
    """Base exception for todo-related errors"""
    pass

class TodoNotFoundError(TodoError):
    def __init__(self, todo_id=None):
        message = "Todo not found" if todo_id is None else f"Todo with id {todo_id} not found"
        super().__init__(status_code=404, detail=message)

class TodoCreationError(TodoError):
    def __init__(self, error: str):
        super().__init__(status_code=500, detail=f"Failed to create todo: {error}")

class UserError(HTTPException):
    """Base exception for user-related errors"""
    pass

class UserNotFoundError(UserError):
    def __init__(self, user_id=None):
        message = "User not found" if user_id is None else f"User with id {user_id} not found"
        super().__init__(status_code=404, detail=message)

class PasswordMismatchError(UserError):
    def __init__(self):
        super().__init__(status_code=400, detail="New passwords do not match")

class InvalidPasswordError(UserError):
    def __init__(self):
        super().__init__(status_code=401, detail="Current password is incorrect")

class AuthenticationError(HTTPException):
    def __init__(self, message: str = "Could not validate user"):
        super().__init__(status_code=401, detail=message)

class LoginError(HTTPException):
    """Base exception for login-related errors"""
    def __init__(self, message: str = "Login failed"):
        super().__init__(status_code=401, detail=message)

class InvalidCredentialsError(LoginError):
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message=message)

class UserAccountLockedError(LoginError):
    def __init__(self, message: str = "Account is temporarily locked"):
        super().__init__(status_code=423, detail=message)

class UserAccountDisabledError(LoginError):
    def __init__(self, message: str = "Account is disabled"):
        super().__init__(status_code=403, detail=message)

class TokenGenerationError(HTTPException):
    def __init__(self, message: str = "Failed to generate access token"):
        super().__init__(status_code=500, detail=message)
