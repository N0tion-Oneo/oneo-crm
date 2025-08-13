"""
Encryption utilities for secure share links
"""
import base64
import json
import time
import hashlib
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.cache import cache


class ShareLinkEncryption:
    """Symmetric encryption for share links using Fernet"""
    
    def __init__(self):
        # Use Django SECRET_KEY to derive encryption key
        key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        # Fernet requires base64-encoded 32-byte key
        self.cipher = Fernet(base64.urlsafe_b64encode(key))
    
    def encrypt_share_data(self, record_id, user_id, expires_timestamp, access_mode='editable'):
        """Encrypt share link data into single token"""
        
        # Create payload with all necessary data
        payload = {
            'record_id': str(record_id),
            'user_id': user_id,
            'expires': expires_timestamp,
            'created': int(time.time()),  # For additional validation
            'access_mode': access_mode  # 'readonly' or 'editable'
        }
        
        # Convert to JSON and encrypt
        json_payload = json.dumps(payload, separators=(',', ':')).encode()
        encrypted_bytes = self.cipher.encrypt(json_payload)
        
        # Base64 encode for URL-safe usage
        encrypted_token = base64.urlsafe_b64encode(encrypted_bytes).decode()
        
        return encrypted_token
    
    def decrypt_share_data(self, encrypted_token):
        """Decrypt and validate share link data"""
        try:
            # Decode from base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode())
            
            # Decrypt payload
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            payload = json.loads(decrypted_bytes.decode())
            
            # Validate payload structure
            required_fields = ['record_id', 'user_id', 'expires', 'created']
            if not all(field in payload for field in required_fields):
                return None, "Invalid payload structure"
            
            # Set default access_mode for backward compatibility
            if 'access_mode' not in payload:
                payload['access_mode'] = 'editable'
            
            # Check expiry
            if time.time() > payload['expires']:
                return None, "Share link has expired"
            
            return payload, None
            
        except Exception as e:
            return None, f"Invalid or corrupted share link: {str(e)}"
    
    def generate_working_day_expiry(self, working_days=5):
        """Generate expiry timestamp for N working days"""
        current_date = datetime.now().date()
        days_added = 0
        
        while days_added < working_days:
            current_date += timedelta(days=1)
            if current_date.weekday() < 5:  # Mon-Fri
                days_added += 1
        
        # Set to 5 PM on final working day
        expiry_datetime = datetime.combine(
            current_date, 
            datetime.min.time().replace(hour=17)
        )
        return int(expiry_datetime.timestamp())
    
    def calculate_working_days_remaining(self, expires_timestamp):
        """Calculate working days remaining until expiry"""
        if expires_timestamp <= time.time():
            return 0
            
        expires_date = datetime.fromtimestamp(expires_timestamp).date()
        current_date = datetime.now().date()
        
        working_days = 0
        check_date = current_date
        
        while check_date < expires_date:
            if check_date.weekday() < 5:  # Mon-Fri
                working_days += 1
            check_date += timedelta(days=1)
        
        return working_days