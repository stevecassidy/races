# API Authentication Guide (v1)

This guide explains how to authenticate against the v1 API in practice.
For endpoint-level request/response shapes, use OpenAPI:

- `/api/v1/schema/` (raw schema)
- `/api/v1/docs/` (Swagger UI)

## Base URL

All v1 endpoints are mounted under:

- `/api/v1/`

## 1) Sign in to get tokens

Request:

```http
POST /api/v1/auth/token/
Content-Type: application/json

{
  "username": "your-username",
  "password": "your-password"
}
```

Successful response (200):

```json
{
  "access": "<jwt-access-token>",
  "refresh": "<jwt-refresh-token>"
}
```

Invalid credentials return `401`.

## 2) Call protected endpoints with the access token

Use the access token in the `Authorization` header:

```http
Authorization: Bearer <jwt-access-token>
```

Example:

```http
GET /api/v1/auth/me/
Authorization: Bearer <jwt-access-token>
```

If the token is missing/invalid/expired, the API returns `401`.

## 3) Refresh the access token

When the access token expires, call:

```http
POST /api/v1/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "<jwt-refresh-token>"
}
```

Successful response (200):

```json
{
  "access": "<new-jwt-access-token>"
}
```

Then retry protected API calls with the new access token.

## 4) Profile endpoints and auth requirements

Protected:

- `GET /api/v1/auth/me/`
- `GET /api/v1/auth/profile/`
- `PATCH /api/v1/auth/profile/`

Public (no login required):

- `POST /api/v1/auth/register/`
- `POST /api/v1/auth/password-reset/`
- `POST /api/v1/auth/password-reset/confirm/`
- `POST /api/v1/auth/token/`
- `POST /api/v1/auth/token/refresh/`

## 5) Password reset flow

### Request reset

```http
POST /api/v1/auth/password-reset/
Content-Type: application/json

{
  "email": "user@example.com"
}
```

Response is always 200 with a generic message, whether or not the email exists.

### Confirm reset

```http
POST /api/v1/auth/password-reset/confirm/
Content-Type: application/json

{
  "uid": "<uid-from-reset-link>",
  "token": "<token-from-reset-link>",
  "new_password": "new-password"
}
```

Invalid/expired reset token returns `400`.

## 6) Recommended client behavior

- Keep `refresh` token separate from access token handling.
- Treat `401` on protected routes as a trigger to refresh once, then retry.
- If refresh fails, clear auth state and force re-login.
