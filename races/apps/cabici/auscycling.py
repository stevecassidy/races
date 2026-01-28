"""
AusCycling Verification API Client
"""

import requests
import logging
from django.utils import timezone
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AusCyclingAPIError(Exception):
    """Exception for AusCycling API errors"""
    pass


class AusCyclingClient:
    """Client for AusCycling Verification API"""
    
    BASE_URL = 'https://api.auscycling.org.au'
    TOKEN_ENDPOINT = '/verification-api/oauth/token'
    MEMBERSHIP_ENDPOINT = '/verification-api/v1/membership'
    
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expiry = None
    
    def get_access_token(self):
        """Get OAuth2 access token using client credentials flow"""
        
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
        
        url = f"{self.BASE_URL}{self.TOKEN_ENDPOINT}"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (compatible; AusCycling-MembershipValidator/1.0)',
        }
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        
        try:
            response = requests.post(url, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            # Set expiry to 5 minutes before actual expiry for safety
            expires_in = token_data.get('expires_in', 3600)
            self.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 300)
            
            logger.info("Successfully obtained AusCycling API access token")
            return self.access_token
            
        except requests.exceptions.Timeout as e:  
            logger.error("Timeout while obtaining AusCycling API access token", exc_info=True)  
            raise AusCyclingAPIError("Authentication request to AusCycling API timed out") from e  

        except requests.exceptions.HTTPError as e:  
            status_code = None  
            response_body = None  
            if e.response is not None:  
                status_code = e.response.status_code  
                # Log the raw text body; if bodies are large or sensitive, this may need revisiting.  
                response_body = e.response.text  
                logger.error(  
                    "HTTP error while obtaining AusCycling API access token: status=%s, body=%s",  
                    status_code,  
                    response_body,  
                    exc_info=True,  
                )  
            message = f"Authentication failed with HTTP status {status_code}" if status_code is not None else "Authentication failed with HTTP error"  
            raise AusCyclingAPIError(message) from e  

        except requests.exceptions.RequestException as e:  
            logger.error("Network error while obtaining AusCycling API access token: %s", e, exc_info=True)  
            raise AusCyclingAPIError("Authentication failed due to a network error") from e  
    
    def verify_membership(self, member_id, last_name, check_date, club_id=None):
        """
        Verify a member's membership status
        
        Args:
            member_id: AusCycling member ID (licence number)
            last_name: Member's last name
            check_date: Date to check membership validity (datetime.date)
            club_id: Optional club ID to verify club membership
            
        Returns:
            dict with keys:
                - success: bool
                - code: str (e.g., 'MEMBERSHIP_FOUND', 'MEMBERSHIP_NOT_FOUND')
                - message: str
        """
        
        token = self.get_access_token()
        url = f"{self.BASE_URL}{self.MEMBERSHIP_ENDPOINT}"
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (compatible; AusCycling-MembershipValidator/1.0)',
        }
        
        # Format the date as ISO 8601
        check_datetime = datetime.combine(check_date, datetime.min.time()).isoformat() + 'Z'
        
        payload = {
            'memberId': 'AC' + str(member_id),
            'memberLastName': last_name,
            'membershipTypes': ["RACE_AD","RACE_AD_TRAIL","RACE_AD_EVENT","RACE_OR","RACE_RG"],  # Only checking Race memberships
            'membershipDates': [check_datetime],
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            verification = data.get('verification', {})
            context = verification.get('context', {})
            
            result = {
                'success': verification.get('success', False),
                'code': context.get('code', 'UNKNOWN'),
                'data': context.get('data', {}),
                'message': self._get_message(context.get('code', 'UNKNOWN')),
            }
            
            logger.info(f"Membership verification for {member_id}: {result['code']}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Membership verification failed for {member_id}: {e}")
            raise AusCyclingAPIError(f"Verification request failed: {e}")
    
    def _get_message(self, code):
        """Convert API response code to human-readable message"""
        
        messages = {
            'MEMBERSHIP_FOUND': 'Valid Race membership found',
            'MEMBERSHIP_NOT_FOUND': 'No valid Race membership found',
            'MEMBERSHIP_SUSPENDED': 'Membership is suspended',
            'MEMBER_NOT_FOUND': 'Member not found in AusCycling system',
            'INVALID_LASTNAME': 'Last name does not match member record',
        }
        
        return messages.get(code, f'Unknown status: {code}')