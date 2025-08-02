"""
Comprehensive regex patterns for form validation
Tenant-aware validation patterns with internationalization support
"""

import re
from typing import Dict, List, Optional, Pattern
from dataclasses import dataclass


@dataclass
class ValidationPattern:
    """Structured validation pattern with metadata"""
    name: str
    pattern: str
    description: str
    flags: int = re.IGNORECASE
    examples_valid: List[str] = None
    examples_invalid: List[str] = None
    compiled: Optional[Pattern] = None
    
    def __post_init__(self):
        self.compiled = re.compile(self.pattern, self.flags)
        if self.examples_valid is None:
            self.examples_valid = []
        if self.examples_invalid is None:
            self.examples_invalid = []


# Core validation patterns
VALIDATION_PATTERNS = {
    # Email patterns
    'email_basic': ValidationPattern(
        name='Basic Email',
        pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        description='Basic email format validation',
        examples_valid=['user@example.com', 'test.email+tag@domain.co.uk'],
        examples_invalid=['invalid.email', '@domain.com', 'user@']
    ),
    
    'email_strict': ValidationPattern(
        name='Strict Email',
        pattern=r'^[a-zA-Z0-9]([a-zA-Z0-9._-])*[a-zA-Z0-9]@[a-zA-Z0-9]([a-zA-Z0-9.-])*[a-zA-Z0-9]\.[a-zA-Z]{2,}$',
        description='Strict email validation with more rigorous rules',
        examples_valid=['user@example.com', 'john.doe@company.org'],
        examples_invalid=['user..name@example.com', '.user@example.com']
    ),
    
    # Phone number patterns
    'phone_us': ValidationPattern(
        name='US Phone Number',
        pattern=r'^\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$',
        description='US phone number format',
        examples_valid=['(555) 123-4567', '555-123-4567', '+1 555 123 4567'],
        examples_invalid=['555-12-3456', '1234567890123']
    ),
    
    'phone_international': ValidationPattern(
        name='International Phone',
        pattern=r'^\+?[1-9]\d{1,14}$',
        description='International phone number (E.164 format)',
        examples_valid=['+1234567890', '+44123456789'],
        examples_invalid=['+123', '123456789012345678']
    ),
    
    'phone_flexible': ValidationPattern(
        name='Flexible Phone',
        pattern=r'^[\+]?[1-9][\d\s\-\(\)\.]{7,15}$',
        description='Flexible phone number format',
        examples_valid=['123-456-7890', '+1 (555) 123-4567', '555.123.4567'],
        examples_invalid=['123', '++1234567890']
    ),
    
    # Address patterns
    'zip_us': ValidationPattern(
        name='US ZIP Code',
        pattern=r'^\d{5}(-\d{4})?$',
        description='US ZIP code (5 digits or 5+4)',
        examples_valid=['12345', '12345-6789'],
        examples_invalid=['1234', '123456', 'ABCDE']
    ),
    
    'postal_canada': ValidationPattern(
        name='Canadian Postal Code',
        pattern=r'^[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d$',
        description='Canadian postal code format',
        examples_valid=['K1A 0A6', 'M5V3A8', 'H3B-2Y7'],
        examples_invalid=['12345', 'A1A1A1', 'Z0Z 0Z0']
    ),
    
    'postal_uk': ValidationPattern(
        name='UK Postal Code',
        pattern=r'^[A-Za-z]{1,2}\d[A-Za-z\d]?\s?\d[A-Za-z]{2}$',
        description='UK postal code format',
        examples_valid=['SW1A 1AA', 'M1 1AA', 'B33 8TH'],
        examples_invalid=['12345', 'SW1A', 'SW1A 1A']
    ),
    
    # URL patterns
    'url_http': ValidationPattern(
        name='HTTP URL',
        pattern=r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$',
        description='HTTP/HTTPS URL validation',
        examples_valid=['https://example.com', 'http://www.example.com/path'],
        examples_invalid=['ftp://example.com', 'example.com', 'http://']
    ),
    
    'url_any': ValidationPattern(
        name='Any URL',
        pattern=r'^[a-zA-Z][a-zA-Z\d+\-.]*:\/\/[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$',
        description='Any protocol URL validation',
        examples_valid=['https://example.com', 'ftp://files.example.com'],
        examples_invalid=['example.com', '://example.com']
    ),
    
    # Identification patterns
    'ssn_us': ValidationPattern(
        name='US Social Security Number',
        pattern=r'^\d{3}-?\d{2}-?\d{4}$',
        description='US Social Security Number',
        examples_valid=['123-45-6789', '123456789'],
        examples_invalid=['123-45-678', '123-456-789']
    ),
    
    'ein_us': ValidationPattern(
        name='US Employer ID Number',
        pattern=r'^\d{2}-?\d{7}$',
        description='US Employer Identification Number',
        examples_valid=['12-3456789', '123456789'],
        examples_invalid=['123-456789', '12-34567']
    ),
    
    # Credit card patterns
    'credit_card_visa': ValidationPattern(
        name='Visa Credit Card',
        pattern=r'^4[0-9]{12}(?:[0-9]{3})?$',
        description='Visa credit card number',
        examples_valid=['4111111111111111', '4012888888881881'],
        examples_invalid=['5111111111111111', '411111111111111']
    ),
    
    'credit_card_mastercard': ValidationPattern(
        name='MasterCard Credit Card',
        pattern=r'^5[1-5][0-9]{14}$',
        description='MasterCard credit card number',
        examples_valid=['5555555555554444', '5105105105105100'],
        examples_invalid=['4555555555554444', '5055555555554444']
    ),
    
    'credit_card_any': ValidationPattern(
        name='Any Credit Card',
        pattern=r'^(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})$',
        description='Any major credit card format',
        examples_valid=['4111111111111111', '5555555555554444', '378282246310005'],
        examples_invalid=['1234567890123456', '0000000000000000']
    ),
    
    # IP Address patterns
    'ipv4': ValidationPattern(
        name='IPv4 Address',
        pattern=r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
        description='IPv4 address validation',
        examples_valid=['192.168.1.1', '10.0.0.1', '255.255.255.255'],
        examples_invalid=['256.1.1.1', '192.168.1', '192.168.1.1.1']
    ),
    
    'ipv6': ValidationPattern(
        name='IPv6 Address',
        pattern=r'^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4})$',
        description='IPv6 address validation (simplified)',
        examples_valid=['2001:0db8:85a3:0000:0000:8a2e:0370:7334', '::1'],
        examples_invalid=['2001:0db8:85a3::8a2e::7334', '192.168.1.1']
    ),
    
    'mac_address': ValidationPattern(
        name='MAC Address',
        pattern=r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$',
        description='MAC address validation',
        examples_valid=['00:1A:2B:3C:4D:5E', '00-1a-2b-3c-4d-5e'],
        examples_invalid=['00:1A:2B:3C:4D', '00:1G:2B:3C:4D:5E']
    ),
    
    # Text patterns
    'alpha_only': ValidationPattern(
        name='Alphabetic Only',
        pattern=r'^[A-Za-z]+$',
        description='Alphabetic characters only',
        examples_valid=['John', 'Mary'],
        examples_invalid=['John123', 'John-Doe', 'John ']
    ),
    
    'alphanumeric': ValidationPattern(
        name='Alphanumeric',
        pattern=r'^[A-Za-z0-9]+$',
        description='Alphanumeric characters only',
        examples_valid=['John123', 'Test456'],
        examples_invalid=['John-Doe', 'Test 123', '!@#']
    ),
    
    'username': ValidationPattern(
        name='Username',
        pattern=r'^[A-Za-z0-9._-]{3,20}$',
        description='Username format (3-20 chars, letters, numbers, dots, underscores, hyphens)',
        examples_valid=['john_doe', 'user123', 'test.user'],
        examples_invalid=['jo', 'user@domain', 'very_long_username_that_exceeds_limit']
    ),
    
    'slug': ValidationPattern(
        name='URL Slug',
        pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$',
        description='URL-friendly slug format',
        examples_valid=['hello-world', 'my-blog-post', 'test123'],
        examples_invalid=['Hello World', 'test_post', '-invalid', 'invalid-']
    ),
    
    # Password patterns
    'password_simple': ValidationPattern(
        name='Simple Password',
        pattern=r'^.{8,}$',
        description='Minimum 8 characters',
        examples_valid=['password123', 'mypassword'],
        examples_invalid=['pass', '1234567']
    ),
    
    'password_medium': ValidationPattern(
        name='Medium Password',
        pattern=r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d@$!%*?&]{8,}$',
        description='At least 8 chars with uppercase, lowercase, and digit',
        examples_valid=['Password123', 'MyPass1'],
        examples_invalid=['password', 'PASSWORD123', 'Password']
    ),
    
    'password_strong': ValidationPattern(
        name='Strong Password',
        pattern=r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{12,}$',
        description='At least 12 chars with uppercase, lowercase, digit, and special char',
        examples_valid=['MyPassword123!', 'Secure@Pass1'],
        examples_invalid=['Password123', 'MyPassword!', 'MyPassword123']
    ),
    
    # Date patterns
    'date_iso': ValidationPattern(
        name='ISO Date',
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description='ISO date format (YYYY-MM-DD)',
        examples_valid=['2023-12-25', '2000-01-01'],
        examples_invalid=['12/25/2023', '2023-13-01', '2023-12-32']
    ),
    
    'date_us': ValidationPattern(
        name='US Date',
        pattern=r'^(0?[1-9]|1[0-2])\/(0?[1-9]|[12]\d|3[01])\/\d{4}$',
        description='US date format (MM/DD/YYYY)',
        examples_valid=['12/25/2023', '1/1/2000'],
        examples_invalid=['2023-12-25', '13/01/2023', '12/32/2023']
    ),
    
    'time_24h': ValidationPattern(
        name='24-Hour Time',
        pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$',
        description='24-hour time format (HH:MM)',
        examples_valid=['14:30', '09:15', '23:59'],
        examples_invalid=['25:00', '14:60', '9:15']
    ),
    
    # File patterns
    'filename_safe': ValidationPattern(
        name='Safe Filename',
        pattern=r'^[A-Za-z0-9._-]+$',
        description='Safe filename characters only',
        examples_valid=['document.pdf', 'image_01.jpg', 'file-name.txt'],
        examples_invalid=['file name.pdf', 'file/path.txt', 'file<>.txt']
    ),
    
    # Currency patterns
    'currency_usd': ValidationPattern(
        name='USD Currency',
        pattern=r'^\$?(\d{1,3}(,\d{3})*|\d+)(\.\d{2})?$',
        description='US Dollar currency format',
        examples_valid=['$1,234.56', '1234.56', '$1,000', '100'],
        examples_invalid=['$1,23.45', '1234.567', '$1,2345']
    ),
    
    # Geographic patterns
    'latitude': ValidationPattern(
        name='Latitude',
        pattern=r'^[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?)$',
        description='Latitude coordinate (-90 to 90)',
        examples_valid=['40.7128', '-73.9352', '0', '90.0'],
        examples_invalid=['91', '-91', '40.7128.123']
    ),
    
    'longitude': ValidationPattern(
        name='Longitude',
        pattern=r'^[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$',
        description='Longitude coordinate (-180 to 180)',
        examples_valid=['40.7128', '-73.9352', '0', '180.0'],
        examples_invalid=['181', '-181', '40.7128.123']
    ),
}


# International phone patterns by country
INTERNATIONAL_PHONE_PATTERNS = {
    'US': ValidationPattern(
        name='US Phone',
        pattern=r'^\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$',
        description='US phone number'
    ),
    'UK': ValidationPattern(
        name='UK Phone',
        pattern=r'^\+?44[-.\s]?[0-9]{2,4}[-.\s]?[0-9]{4,6}$',
        description='UK phone number'
    ),
    'CA': ValidationPattern(
        name='Canada Phone',
        pattern=r'^\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$',
        description='Canadian phone number'
    ),
    'AU': ValidationPattern(
        name='Australia Phone',
        pattern=r'^\+?61[-.\s]?[0-9]{1}[-.\s]?[0-9]{4}[-.\s]?[0-9]{4}$',
        description='Australian phone number'
    ),
}


def get_pattern(pattern_name: str) -> Optional[ValidationPattern]:
    """Get a validation pattern by name"""
    return VALIDATION_PATTERNS.get(pattern_name)


def get_international_phone_pattern(country: str) -> Optional[ValidationPattern]:
    """Get phone pattern for specific country"""
    return INTERNATIONAL_PHONE_PATTERNS.get(country.upper())


def validate_with_pattern(pattern_name: str, value: str) -> bool:
    """Validate a value against a named pattern"""
    pattern = get_pattern(pattern_name)
    if not pattern:
        return False
    return bool(pattern.compiled.match(value))


def get_pattern_names() -> List[str]:
    """Get list of all available pattern names"""
    return list(VALIDATION_PATTERNS.keys())


def get_patterns_by_category() -> Dict[str, List[str]]:
    """Get patterns organized by category"""
    categories = {
        'Email': [k for k in VALIDATION_PATTERNS.keys() if 'email' in k],
        'Phone': [k for k in VALIDATION_PATTERNS.keys() if 'phone' in k],
        'Address': [k for k in VALIDATION_PATTERNS.keys() if k in ['zip_us', 'postal_canada', 'postal_uk']],
        'URL': [k for k in VALIDATION_PATTERNS.keys() if 'url' in k],
        'Identification': [k for k in VALIDATION_PATTERNS.keys() if k in ['ssn_us', 'ein_us']],
        'Credit Card': [k for k in VALIDATION_PATTERNS.keys() if 'credit_card' in k],
        'Network': [k for k in VALIDATION_PATTERNS.keys() if k in ['ipv4', 'ipv6', 'mac_address']],
        'Text': [k for k in VALIDATION_PATTERNS.keys() if k in ['alpha_only', 'alphanumeric', 'username', 'slug']],
        'Password': [k for k in VALIDATION_PATTERNS.keys() if 'password' in k],
        'Date/Time': [k for k in VALIDATION_PATTERNS.keys() if k in ['date_iso', 'date_us', 'time_24h']],
        'File': [k for k in VALIDATION_PATTERNS.keys() if 'filename' in k],
        'Currency': [k for k in VALIDATION_PATTERNS.keys() if 'currency' in k],
        'Geographic': [k for k in VALIDATION_PATTERNS.keys() if k in ['latitude', 'longitude']],
    }
    return categories