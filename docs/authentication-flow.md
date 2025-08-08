# Authentication Flow Documentation

This document describes the proper authentication flow for the Trading Simulator application, which integrates Firebase Authentication with a custom backend registration system.

## Overview

The application uses a two-step authentication process:
1. **Firebase Authentication**: Handles user signup/login on the frontend
2. **Backend Registration**: Creates user record and portfolio in the backend database

## Frontend Integration Flow

### 1. Firebase Signup (New Users)

When a new user signs up:

```dart
// 1. Create user with Firebase
UserCredential credential = await FirebaseAuth.instance
    .createUserWithEmailAndPassword(email: email, password: password);

// 2. Get Firebase ID token
String? token = await credential.user?.getIdToken();

// 3. Call backend registration endpoint
final response = await http.post(
  Uri.parse('${baseUrl}/api/auth/register'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({
    'firebase_token': token,
    'email': email,
    'display_name': displayName,
  }),
);

if (response.statusCode == 200) {
  // User successfully registered in backend
  final userData = jsonDecode(response.body);
  // Store user data locally if needed
} else {
  // Handle registration error
}
```

### 2. Firebase Login (Existing Users)

When an existing user logs in:

```dart
// 1. Sign in with Firebase
UserCredential credential = await FirebaseAuth.instance
    .signInWithEmailAndPassword(email: email, password: password);

// 2. Check if user exists in backend
final response = await http.get(
  Uri.parse('${baseUrl}/api/auth/profile'),
  headers: {
    'Authorization': 'Bearer ${await credential.user?.getIdToken()}',
  },
);

if (response.statusCode == 200) {
  // User exists in backend, proceed normally
  final userData = jsonDecode(response.body);
} else if (response.statusCode == 404) {
  // User not found in backend, redirect to registration
  // This should rarely happen but handles edge cases
} else {
  // Handle other errors
}
```

### 3. Local Data Migration (After Login)

If the user has local data from using the app anonymously:

```dart
// After successful login, check for local data
if (hasLocalData()) {
  final localData = getLocalData();
  
  // Call migration endpoint
  final response = await http.post(
    Uri.parse('${baseUrl}/sync/migrate'),
    headers: {
      'Authorization': 'Bearer ${await user?.getIdToken()}',
      'Content-Type': 'application/json',
    },
    body: jsonEncode({
      'anonymous_user_id': localAnonymousId,
      'firebase_user_id': user!.uid,
      'sync_timestamp': DateTime.now().toIso8601String(),
      'data': localData,
    }),
  );
  
  if (response.statusCode == 200) {
    // Migration successful, clear local data
    clearLocalData();
  } else {
    // Handle migration error
  }
}
```

## Backend Endpoints

### `/api/auth/register` (POST)

Creates a new user in the backend database after Firebase authentication.

**Request Body:**
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "email": "user@example.com",
  "display_name": "John Doe"
}
```

**Response:**
```json
{
  "user_id": "firebase-uid-123",
  "email": "user@example.com", 
  "username": "user_firebase",
  "display_name": "John Doe",
  "avatar_url": null,
  "created_at": "2025-08-08T10:00:00Z",
  "updated_at": null,
  "is_active": true
}
```

**What it does:**
- Verifies Firebase token
- Creates user record in database
- Creates default portfolio with $10,000 starting balance
- Generates unique username if needed

### `/api/auth/profile` (GET)

Returns the current user's profile information.

**Headers:**
```
Authorization: Bearer <firebase-token>
```

**Response:**
```json
{
  "user_id": "firebase-uid-123",
  "email": "user@example.com",
  "username": "user_firebase", 
  "display_name": "John Doe",
  "avatar_url": null,
  "created_at": "2025-08-08T10:00:00Z",
  "updated_at": "2025-08-08T11:00:00Z",
  "is_active": true
}
```

### `/api/auth/profile` (PUT)

Updates the current user's profile information.

**Request Body:**
```json
{
  "username": "new_username",
  "display_name": "New Display Name",
  "avatar_url": "https://example.com/avatar.jpg"
}
```

### `/sync/migrate` (POST)

Migrates local data to authenticated user account. **User must be registered first.**

**Request Body:**
```json
{
  "anonymous_user_id": "anonymous-123",
  "firebase_user_id": "firebase-uid-123", 
  "sync_timestamp": "2025-08-08T10:00:00Z",
  "data": {
    "portfolio": {
      "user_id": "anonymous-123",
      "cash_balance": "9500.00",
      "initial_balance": "10000.00"
    },
    "holdings": [...],
    "transactions": [...],
    "watchlist": [...]
  }
}
```

## Error Handling

### Common Error Scenarios

1. **Invalid Firebase Token** (401)
   - Token expired or malformed
   - Solution: Refresh token and retry

2. **User Already Exists** (Registration)
   - Returns existing user data instead of error
   - This is normal behavior

3. **User Not Found** (Migration/Profile)
   - User not registered in backend
   - Solution: Call `/api/auth/register` first

4. **Username Taken** (Profile Update)
   - Username already exists
   - Solution: Choose different username

## Security Considerations

1. **Firebase Token Verification**: All authenticated endpoints verify Firebase tokens
2. **User Ownership**: Users can only access/modify their own data
3. **Token Expiration**: Frontend should handle token refresh automatically
4. **HTTPS Only**: All authentication endpoints should use HTTPS in production

## Database Schema

### Users Table
- `user_id` (Primary Key): Firebase UID
- `email`: User's email address
- `username`: Unique username
- `display_name`: Optional display name
- `avatar_url`: Optional avatar URL
- `created_at`: Registration timestamp
- `updated_at`: Last update timestamp
- `is_active`: Account status

### Portfolios Table  
- `portfolio_id` (Primary Key): Auto-increment
- `user_id` (Foreign Key): References users.user_id
- `cash_balance`: Current cash balance
- `initial_balance`: Starting balance ($10,000)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

## Testing the Flow

1. **Test Registration:**
   ```bash
   # Get Firebase token from your app
   curl -X POST http://localhost:8000/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"firebase_token": "YOUR_TOKEN", "email": "test@example.com"}'
   ```

2. **Test Profile Access:**
   ```bash
   curl -X GET http://localhost:8000/api/auth/profile \
     -H "Authorization: Bearer YOUR_FIREBASE_TOKEN"
   ```

3. **Test Migration:**
   ```bash
   curl -X POST http://localhost:8000/sync/migrate \
     -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
     -H "Content-Type: application/json" \
     -d @migration_data.json
   ```

## Migration from Anonymous to Authenticated

The application supports local-first architecture where users can:

1. **Use app anonymously** with local data storage
2. **Sign up/login later** to sync data to cloud
3. **Access data from multiple devices** after authentication

The migration process ensures no data loss when transitioning from anonymous to authenticated usage.
