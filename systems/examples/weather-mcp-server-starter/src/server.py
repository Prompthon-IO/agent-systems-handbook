from dataclasses import dataclass


@dataclass
class ForecastRequest:
    city: str
    days: int = 1


@dataclass
class ForecastResponse:
    city: str
    summary: str
    source: str


def validate_request(request: ForecastRequest) -> None:
    if not request.city.strip():
        raise ValueError("city is required")
    if request.days < 1 or request.days > 7:
        raise ValueError("days must stay within a small tool-safe range")


def get_forecast(request: ForecastRequest) -> ForecastResponse:
    validate_request(request)
    return ForecastResponse(
        city=request.city,
        summary="placeholder forecast",
        source="demo weather adapter",
    )
