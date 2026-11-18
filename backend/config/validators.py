from django.core.validators import RegexValidator

phone_validator = RegexValidator(
    regex=r"^\+?[0-9][0-9\-\s]{5,19}$",
    message="Enter a valid phone number (6-20 digits, may start with + and contain spaces or dashes).",
)
