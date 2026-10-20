from fastapi import Request, status
from fastapi.responses import JSONResponse

class AppException(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, error_code: str = "BAD_REQUEST"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

class NotFoundException(AppException):
    def __init__(self, resource: str):
        super().__init__(
            message=f"{resource} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND"
        )

class UnauthorizedException(AppException):
    def __init__(self, message: str = "Could not validate credentials"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED"
        )

class ForbiddenException(AppException):
    def __init__(self, message: str = "Not enough permissions"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN"
        )

class ConflictException(AppException):
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT"
        )

class VehicleAlreadyBookedException(ConflictException):
    def __init__(self, message: str = "Vehicle is already booked or unavailable"):
        super().__init__(message=message)

class VehicleNotFoundException(NotFoundException):
    def __init__(self, vehicle_id: str):
        super().__init__(resource=f"Vehicle {vehicle_id}")

async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "message": exc.message},
    )

