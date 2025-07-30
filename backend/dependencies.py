from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Initialize Firebase Admin SDK
def initialize_firebase():
    """Initialize Firebase Admin SDK with service account credentials"""
    try:
        # Check if Firebase is already initialized
        firebase_admin.get_app()
    except ValueError:
        # Firebase not initialized, initialize it
        cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        cred_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        
        if cred_path and os.path.exists(cred_path):
            # Use service account file
            cred = credentials.Certificate(cred_path)
        elif cred_json:
            # Use service account JSON string (for deployments)
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
        else:
            # Fallback: try to use default credentials or application default
            print("Warning: No Firebase credentials found. Using application default.")
            cred = credentials.ApplicationDefault()
        
        firebase_admin.initialize_app(cred)

# Initialize Firebase on module import
initialize_firebase()

# Security scheme for bearer token
security = HTTPBearer()

class FirebaseUser:
    """Class to represent a Firebase authenticated user"""
    def __init__(self, uid: str, email: str = None, email_verified: bool = False):
        self.uid = uid
        self.email = email
        self.email_verified = email_verified

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> FirebaseUser:
    """
    Dependency to get current authenticated user from Firebase ID token.
    Validates the Firebase ID token sent in the Authorization header.
    """
    try:
        # Extract the token from the Authorization header
        token = credentials.credentials
        
        # Verify the ID token
        decoded_token = auth.verify_id_token(token)
        
        # Extract user information
        uid = decoded_token['uid']
        email = decoded_token.get('email')
        email_verified = decoded_token.get('email_verified', False)
        
        return FirebaseUser(uid=uid, email=email, email_verified=email_verified)
        
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ID token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expired ID token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Revoked ID token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"Error verifying Firebase token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user_id(current_user: FirebaseUser = Depends(get_current_user)) -> str:
    """
    Dependency to get just the current user's ID.
    Useful when you only need the user ID.
    """
    return current_user.uid

async def get_verified_user(current_user: FirebaseUser = Depends(get_current_user)) -> FirebaseUser:
    """
    Dependency to get current authenticated user, but only if email is verified.
    Use this for operations that require email verification.
    """
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    return current_user

# Optional: Mock authentication for development/testing
class MockFirebaseUser(FirebaseUser):
    """Mock Firebase user for development/testing"""
    def __init__(self):
        super().__init__(
            uid="mock_user_123",
            email="test@example.com",
            email_verified=True
        )

async def get_mock_user() -> FirebaseUser:
    """Mock dependency for development/testing without Firebase"""
    return MockFirebaseUser()

# Function to get the appropriate user dependency based on environment
def get_auth_dependency():
    """
    Returns the appropriate authentication dependency based on environment.
    Use mock authentication in development if MOCK_AUTH is enabled.
    """
    if os.getenv("MOCK_AUTH", "false").lower() == "true":
        print("Warning: Using mock authentication. Only use in development!")
        return get_mock_user
    return get_current_user

# Custom exception for authorization errors
class AuthorizationError(Exception):
    """Custom exception for authorization-related errors"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

# Function to check if user has permission for a resource
def check_user_permission(current_user_id: str, resource_user_id: str):
    """
    Check if the current user has permission to access a resource.
    Users can only access their own resources.
    """
    if current_user_id != resource_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )

# Dependency to validate admin permissions (for future use)
async def get_admin_user(current_user: FirebaseUser = Depends(get_current_user)) -> FirebaseUser:
    """
    Dependency to ensure current user has admin privileges.
    This would need to be implemented based on your admin user system.
    """
    # TODO: Implement admin user validation
    # For now, this is a placeholder
    
    # You could check custom claims in the Firebase token:
    # admin_claim = decoded_token.get('admin', False)
    # if not admin_claim:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    return current_user 