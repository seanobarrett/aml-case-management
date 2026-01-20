"""
PII redaction service for audit log payloads.

References:
- D12: Structured payload with explicit PII field list; service-layer redaction
- Principle VI: Sensitive Data Protection
"""

import copy
from typing import Any


# PII fields to redact (explicit list per D12)
PII_FIELDS = {
    # Personal identifiers
    "firstName",
    "first_name",
    "lastName",
    "last_name",
    "fullName",
    "full_name",
    "name",

    # Contact information
    "email",
    "emailAddress",
    "email_address",
    "phone",
    "phoneNumber",
    "phone_number",
    "mobile",
    "mobileNumber",
    "mobile_number",

    # Identity documents
    "dateOfBirth",
    "date_of_birth",
    "dob",
    "ssn",
    "socialSecurityNumber",
    "social_security_number",
    "passport",
    "passportNumber",
    "passport_number",
    "driverLicense",
    "driver_license",
    "licenseNumber",
    "license_number",

    # Financial
    "accountNumber",
    "account_number",
    "bankAccount",
    "bank_account",
    "cardNumber",
    "card_number",
    "taxId",
    "tax_id",
    "tfn",

    # Address
    "address",
    "streetAddress",
    "street_address",
    "addressLine1",
    "address_line_1",
    "addressLine2",
    "address_line_2",
    "suburb",
    "postcode",
    "zipCode",
    "zip_code",
}

# Redaction marker
REDACTED = "[REDACTED]"


class PIIRedactionService:
    """Service for redacting PII from payloads before audit logging."""

    def __init__(self, additional_fields: set[str] | None = None):
        """
        Initialize the PII redaction service.

        Args:
            additional_fields: Additional field names to treat as PII
        """
        self.pii_fields = PII_FIELDS.copy()
        if additional_fields:
            self.pii_fields.update(additional_fields)

    def redact(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Create a redacted copy of the payload.

        Recursively traverses the payload and replaces PII field values
        with "[REDACTED]" marker.

        Args:
            payload: Original payload dictionary

        Returns:
            New dictionary with PII fields redacted
        """
        if not payload:
            return {}

        return self._redact_recursive(copy.deepcopy(payload))

    def _redact_recursive(self, obj: Any) -> Any:
        """
        Recursively redact PII fields in an object.

        Args:
            obj: Object to process (dict, list, or scalar)

        Returns:
            Processed object with PII redacted
        """
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if self._is_pii_field(key):
                    result[key] = REDACTED
                elif isinstance(value, (dict, list)):
                    result[key] = self._redact_recursive(value)
                else:
                    result[key] = value
            return result

        elif isinstance(obj, list):
            return [self._redact_recursive(item) for item in obj]

        else:
            return obj

    def _is_pii_field(self, field_name: str) -> bool:
        """
        Check if a field name indicates PII.

        Uses case-insensitive comparison against known PII field names.

        Args:
            field_name: Field name to check

        Returns:
            True if field is PII
        """
        return field_name.lower() in {f.lower() for f in self.pii_fields}

    def get_pii_field_list(self) -> list[str]:
        """
        Get the list of PII fields being redacted.

        Useful for documentation and auditing the redaction rules.

        Returns:
            Sorted list of PII field names
        """
        return sorted(self.pii_fields)


# Default singleton instance
_default_service = PIIRedactionService()


def redact_pii(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Convenience function to redact PII from a payload.

    Args:
        payload: Original payload

    Returns:
        Redacted copy of the payload
    """
    return _default_service.redact(payload)


def is_pii_field(field_name: str) -> bool:
    """
    Check if a field name is considered PII.

    Args:
        field_name: Field name to check

    Returns:
        True if field is PII
    """
    return _default_service._is_pii_field(field_name)
