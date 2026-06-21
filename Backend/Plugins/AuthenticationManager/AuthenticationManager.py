"""
Vibhu-Oska AI-OS — Authentication Manager Plugin
Provides JWT token generation/validation and database-backed API key verification.
Uses pure-Python cryptographic primitives (hmac, hashlib, secrets) to remain dependency-free.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from Backend.Plugins.ConfigLoader.ConfigLoader import ConfigLoader
from Backend.Plugins.ToolRegistry.BaseService import BaseService
from Shared.Models import PluginInfo, CoreStatus, ExecutionTarget


class AuthenticationManager(BaseService):
    """
    Authentication & Security Manager Service.
    Handles user login tokens (JWT) and client/system API keys.
    """

    def __init__(self, jwt_secret: str | None = None, token_expiry_seconds: int = 86400) -> None:
        self._jwt_secret = jwt_secret
        self._token_expiry_seconds = token_expiry_seconds
        self._initialized = False
        self._db_connector: Any = None

    def info(self) -> PluginInfo:
        return PluginInfo(
            name="auth_manager",
            version="0.1.0",
            description="Manages JWT credentials, API keys, and access tokens for API Gateway requests.",
            capabilities=["auth", "jwt", "api_keys", "credentials"],
            status=CoreStatus.HEALTHY if self._initialized else CoreStatus.UNKNOWN,
            preferred_target=ExecutionTarget.CPU,
        )

    async def initialize(self) -> None:
        """Lifecycle hook: load JWT secret and query db connector to run migrations."""
        if self._initialized:
            return

        config = ConfigLoader.load()
        
        # Load JWT Secret or generate a dynamic one if not configured
        self._jwt_secret = config.get("security.jwt_secret")
        if not self._jwt_secret:
            # Generate a secure fallback secret for this session
            self._jwt_secret = secrets.token_hex(32)

        # Get database connector from the registry (if available)
        # In a real setup, we retrieve it from the registry on startup or lazily
        try:
            from Backend.Plugins.ToolRegistry.Registry import ToolRegistry
            registry = ToolRegistry()
            self._db_connector = registry.get_safe("database_connector")
        except Exception:
            self._db_connector = None

        # Try to run migration for api_keys table
        if self._db_connector:
            try:
                await self._db_connector.execute(
                    "execute",
                    query="""
                        CREATE TABLE IF NOT EXISTS api_keys (
                            key_hash TEXT PRIMARY KEY,
                            user_id TEXT NOT NULL,
                            name TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP,
                            revoked INTEGER DEFAULT 0,
                            FOREIGN KEY(user_id) REFERENCES users(user_id)
                        );
                    """
                )
            except Exception as e:
                # Log or handle warning silently
                pass

        self._initialized = True

    async def shutdown(self) -> None:
        self._initialized = False

    def health_check(self) -> bool:
        return self._initialized

    async def execute(self, action: str, **kwargs: Any) -> Any:
        """
        Execute auth commands.

        Actions:
            - "generate_token": Generate a JWT token.
              Args: user_id (str), role (str, optional), scopes (list, optional), expiry (int, optional)
            - "verify_token": Verify a JWT token.
              Args: token (str) -> returns payload or None
            - "create_api_key": Generate a new API key.
              Args: user_id (str), name (str), expiry_days (int, optional) -> returns {"api_key": str}
            - "verify_api_key": Check if an API key is valid.
              Args: api_key (str) -> returns bool
            - "revoke_api_key": Revoke an API key.
              Args: api_key (str) -> returns bool
        """
        if not self._initialized:
            await self.initialize()

        if action == "generate_token":
            user_id = kwargs.get("user_id")
            if not user_id:
                raise ValueError("user_id is required to generate a token")
            role = kwargs.get("role", "visitor")
            scopes = kwargs.get("scopes", [])
            expiry = kwargs.get("expiry", self._token_expiry_seconds)
            return self._generate_token(user_id, role, scopes, expiry)

        elif action == "verify_token":
            token = kwargs.get("token")
            if not token:
                raise ValueError("token is required to verify")
            return self._verify_token(token)

        elif action == "create_api_key":
            user_id = kwargs.get("user_id")
            name = kwargs.get("name")
            if not user_id or not name:
                raise ValueError("user_id and name are required to create an API key")
            expiry_days = kwargs.get("expiry_days")
            return await self._create_api_key(user_id, name, expiry_days)

        elif action == "verify_api_key":
            api_key = kwargs.get("api_key")
            if not api_key:
                raise ValueError("api_key is required to verify")
            return await self._verify_api_key(api_key)

        elif action == "revoke_api_key":
            api_key = kwargs.get("api_key")
            if not api_key:
                raise ValueError("api_key is required to revoke")
            return await self._revoke_api_key(api_key)

        else:
            raise ValueError(f"Action '{action}' is not supported by AuthenticationManager.")

    # ══════════════════════════════════════════════════════════════════════
    # Helper Crypto Operations (Base64url + HMAC HS256)
    # ══════════════════════════════════════════════════════════════════════

    def _base64url_encode(self, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    def _base64url_decode(self, data: str) -> bytes:
        rem = len(data) % 4
        if rem > 0:
            data += "=" * (4 - rem)
        return base64.urlsafe_b64decode(data.encode("utf-8"))

    # ══════════════════════════════════════════════════════════════════════
    # Core Methods
    # ══════════════════════════════════════════════════════════════════════

    def _generate_token(self, user_id: str, role: str, scopes: list[str], expiry: int) -> str:
        now = int(time.time())
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": user_id,
            "role": role,
            "scopes": scopes,
            "iat": now,
            "exp": now + expiry,
            "jti": secrets.token_hex(16),
        }
        
        header_b64 = self._base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_b64 = self._base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        signature = hmac.new(self._jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        signature_b64 = self._base64url_encode(signature)
        
        return f"{header_b64}.{payload_b64}.{signature_b64}"

    def _verify_token(self, token: str) -> dict[str, Any] | None:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            
            header_b64, payload_b64, signature_b64 = parts
            signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
            
            expected_sig = hmac.new(self._jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
            expected_sig_b64 = self._base64url_encode(expected_sig)
            
            if not hmac.compare_digest(signature_b64, expected_sig_b64):
                return None
                
            payload_bytes = self._base64url_decode(payload_b64)
            payload = json.loads(payload_bytes.decode("utf-8"))
            
            if "exp" in payload and time.time() > payload["exp"]:
                return None  # Expired
                
            return payload
        except Exception:
            return None

    def _hash_key(self, api_key: str) -> str:
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    async def _create_api_key(self, user_id: str, name: str, expiry_days: int | None = None) -> dict[str, Any]:
        # Generate a standard secure prefix key: e.g., 'vo_live_...'
        prefix = "vo_live_"
        raw_key = prefix + secrets.token_urlsafe(32)
        key_hash = self._hash_key(raw_key)
        
        expires_at = None
        if expiry_days:
            expires_at = int(time.time() + (expiry_days * 86400))
            
        if self._db_connector:
            await self._db_connector.execute(
                "execute",
                query="""
                    INSERT INTO api_keys (key_hash, user_id, name, expires_at, revoked)
                    VALUES (?, ?, ?, ?, 0)
                """,
                params=(key_hash, user_id, name, expires_at)
            )
            return {"api_key": raw_key, "name": name, "user_id": user_id, "expires_at": expires_at}
        else:
            raise RuntimeError("DatabaseConnector is not available to store API keys.")

    async def _verify_api_key(self, api_key: str) -> bool:
        if not self._db_connector:
            return False
            
        key_hash = self._hash_key(api_key)
        rows = await self._db_connector.execute(
            "query",
            query="SELECT user_id, expires_at, revoked FROM api_keys WHERE key_hash = ?",
            params=(key_hash,)
        )
        
        if not rows:
            return False
            
        record = rows[0]
        if record["revoked"]:
            return False
            
        expires_at = record["expires_at"]
        if expires_at and time.time() > expires_at:
            return False
            
        return True

    async def _revoke_api_key(self, api_key: str) -> bool:
        if not self._db_connector:
            return False
            
        key_hash = self._hash_key(api_key)
        result = await self._db_connector.execute(
            "execute",
            query="UPDATE api_keys SET revoked = 1 WHERE key_hash = ?",
            params=(key_hash,)
        )
        return result.get("rowcount", 0) > 0
