"""
Honeypot Trap Definitions — Fake endpoints that attract attackers.
🜏 Each trap mimics a common attack target and serves convincing fake data.
"""

from __future__ import annotations

import json
import random
import string
from datetime import datetime, timezone
from typing import Any

from ..schemas import TrapType


# ---------------------------------------------------------------------------
# Trap Registry — Maps paths to trap configurations
# ---------------------------------------------------------------------------

TRAP_REGISTRY: dict[str, dict[str, Any]] = {
    # Config file traps
    "/.env": {
        "type": TrapType.CONFIG_FILE,
        "description": "Fake environment variables",
        "response_type": "text/plain",
    },
    "/.env.local": {
        "type": TrapType.CONFIG_FILE,
        "description": "Fake local environment",
        "response_type": "text/plain",
    },
    "/.env.production": {
        "type": TrapType.CONFIG_FILE,
        "description": "Fake production environment",
        "response_type": "text/plain",
    },
    "/config.php": {
        "type": TrapType.CONFIG_FILE,
        "description": "Fake PHP config",
        "response_type": "application/x-php",
    },
    "/wp-config.php": {
        "type": TrapType.CONFIG_FILE,
        "description": "Fake WordPress config",
        "response_type": "application/x-php",
    },
    "/settings.py": {
        "type": TrapType.CONFIG_FILE,
        "description": "Fake Django settings",
        "response_type": "text/x-python",
    },
    
    # Admin panel traps
    "/admin": {
        "type": TrapType.ADMIN_PANEL,
        "description": "Fake admin panel",
        "response_type": "text/html",
    },
    "/wp-admin": {
        "type": TrapType.ADMIN_PANEL,
        "description": "Fake WordPress admin",
        "response_type": "text/html",
    },
    "/administrator": {
        "type": TrapType.ADMIN_PANEL,
        "description": "Fake Joomla admin",
        "response_type": "text/html",
    },
    "/admin/login": {
        "type": TrapType.ADMIN_PANEL,
        "description": "Fake admin login",
        "response_type": "text/html",
    },
    "/cpanel": {
        "type": TrapType.ADMIN_PANEL,
        "description": "Fake cPanel",
        "response_type": "text/html",
    },
    "/phpmyadmin": {
        "type": TrapType.ADMIN_PANEL,
        "description": "Fake phpMyAdmin",
        "response_type": "text/html",
    },
    
    # Login traps
    "/wp-login.php": {
        "type": TrapType.LOGIN_FORM,
        "description": "Fake WordPress login",
        "response_type": "text/html",
    },
    "/login": {
        "type": TrapType.LOGIN_FORM,
        "description": "Fake login page",
        "response_type": "text/html",
    },
    "/user/login": {
        "type": TrapType.LOGIN_FORM,
        "description": "Fake user login",
        "response_type": "text/html",
    },
    "/signin": {
        "type": TrapType.LOGIN_FORM,
        "description": "Fake signin page",
        "response_type": "text/html",
    },
    
    # API traps
    "/api/admin": {
        "type": TrapType.API_ENDPOINT,
        "description": "Fake admin API",
        "response_type": "application/json",
    },
    "/api/v1/users": {
        "type": TrapType.API_ENDPOINT,
        "description": "Fake users endpoint",
        "response_type": "application/json",
    },
    "/api/v1/config": {
        "type": TrapType.API_ENDPOINT,
        "description": "Fake config API",
        "response_type": "application/json",
    },
    "/api/debug": {
        "type": TrapType.API_ENDPOINT,
        "description": "Fake debug endpoint",
        "response_type": "application/json",
    },
    "/graphql": {
        "type": TrapType.API_ENDPOINT,
        "description": "Fake GraphQL endpoint",
        "response_type": "application/json",
    },
    
    # Debug/info traps
    "/debug": {
        "type": TrapType.DEBUG_INFO,
        "description": "Fake debug info",
        "response_type": "text/html",
    },
    "/server-status": {
        "type": TrapType.DEBUG_INFO,
        "description": "Fake Apache status",
        "response_type": "text/html",
    },
    "/phpinfo.php": {
        "type": TrapType.DEBUG_INFO,
        "description": "Fake PHP info",
        "response_type": "text/html",
    },
    "/info.php": {
        "type": TrapType.DEBUG_INFO,
        "description": "Fake PHP info",
        "response_type": "text/html",
    },
    "/status": {
        "type": TrapType.DEBUG_INFO,
        "description": "Fake status endpoint",
        "response_type": "application/json",
    },
    
    # Backup file traps
    "/backup.sql": {
        "type": TrapType.BACKUP_FILE,
        "description": "Fake SQL backup",
        "response_type": "application/sql",
    },
    "/backup.zip": {
        "type": TrapType.BACKUP_FILE,
        "description": "Fake backup archive",
        "response_type": "application/zip",
    },
    "/database.sql": {
        "type": TrapType.BACKUP_FILE,
        "description": "Fake database dump",
        "response_type": "application/sql",
    },
    "/db.sql": {
        "type": TrapType.BACKUP_FILE,
        "description": "Fake database dump",
        "response_type": "application/sql",
    },
    
    # Git exposure traps
    "/.git/config": {
        "type": TrapType.GIT_REPO,
        "description": "Fake git config",
        "response_type": "text/plain",
    },
    "/.git/HEAD": {
        "type": TrapType.GIT_REPO,
        "description": "Fake git HEAD",
        "response_type": "text/plain",
    },
    "/.gitignore": {
        "type": TrapType.GIT_REPO,
        "description": "Fake gitignore",
        "response_type": "text/plain",
    },
    
    # Database traps
    "/db": {
        "type": TrapType.DATABASE,
        "description": "Fake database endpoint",
        "response_type": "application/json",
    },
    "/mysql": {
        "type": TrapType.DATABASE,
        "description": "Fake MySQL endpoint",
        "response_type": "text/html",
    },
    "/mongodb": {
        "type": TrapType.DATABASE,
        "description": "Fake MongoDB endpoint",
        "response_type": "application/json",
    },
}


# ---------------------------------------------------------------------------
# Fake Data Generators
# ---------------------------------------------------------------------------

def _random_string(length: int = 32) -> str:
    """Generate a random string that looks like a secret."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def _fake_env_file() -> str:
    """Generate fake environment variables."""
    return f"""# Environment Configuration
# WARNING: Do not commit to version control!

# Database
DB_HOST=db.internal.spatium.local
DB_PORT=5432
DB_NAME=spatium_production
DB_USER=spatium_admin
DB_PASSWORD={_random_string(24)}

# API Keys
OPENAI_API_KEY=sk-fake-{_random_string(48)}
STRIPE_SECRET_KEY=sk_live_fake_{_random_string(24)}
AWS_ACCESS_KEY_ID=AKIA{_random_string(16).upper()}
AWS_SECRET_ACCESS_KEY={_random_string(40)}

# Application
SECRET_KEY={_random_string(64)}
JWT_SECRET={_random_string(32)}
DEBUG=false
ENVIRONMENT=production

# Services
REDIS_URL=redis://:password123@redis.internal:6379/0
ELASTICSEARCH_URL=http://elastic:changeme@es.internal:9200

# External APIs
SENDGRID_API_KEY=SG.fake-{_random_string(32)}
TWILIO_AUTH_TOKEN={_random_string(32)}
"""


def _fake_wp_config() -> str:
    """Generate fake WordPress config."""
    return f"""<?php
/**
 * WordPress Configuration
 * HONEYPOT: This is not a real configuration file
 */

define('DB_NAME', 'wordpress_db');
define('DB_USER', 'wp_admin');
define('DB_PASSWORD', '{_random_string(16)}');
define('DB_HOST', 'mysql.internal');

define('AUTH_KEY',         '{_random_string(64)}');
define('SECURE_AUTH_KEY',  '{_random_string(64)}');
define('LOGGED_IN_KEY',    '{_random_string(64)}');
define('NONCE_KEY',        '{_random_string(64)}');
define('AUTH_SALT',        '{_random_string(64)}');

$table_prefix = 'wp_';
define('WP_DEBUG', false);

if ( !defined('ABSPATH') )
    define('ABSPATH', dirname(__FILE__) . '/');

require_once(ABSPATH . 'wp-settings.php');
?>
"""


def _fake_admin_login_page() -> str:
    """Generate a convincing fake admin login page."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Admin Login - Spatium Computationis</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f1f1f1; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-box { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 320px; }
        h1 { text-align: center; color: #333; margin-bottom: 30px; }
        .glyph { font-size: 48px; text-align: center; display: block; margin-bottom: 10px; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #0052a3; }
        .forgot { text-align: center; margin-top: 15px; }
        .forgot a { color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="login-box">
        <span class="glyph">⌬</span>
        <h1>Admin Access</h1>
        <form method="POST" action="/admin/login">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Sign In</button>
        </form>
        <div class="forgot">
            <a href="/admin/forgot-password">Forgot password?</a>
        </div>
    </div>
</body>
</html>
"""


def _fake_users_api() -> dict:
    """Generate fake user data."""
    return {
        "users": [
            {
                "id": 1,
                "username": "admin",
                "email": "admin@spatium-computationis.local",
                "role": "administrator",
                "created_at": "2024-01-15T10:30:00Z",
                "last_login": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": 2,
                "username": "operator",
                "email": "operator@spatium-computationis.local",
                "role": "operator",
                "created_at": "2024-02-20T14:45:00Z",
                "api_key": f"op_{_random_string(32)}",
            },
            {
                "id": 3,
                "username": "service_account",
                "email": "service@spatium-computationis.local",
                "role": "service",
                "api_key": f"svc_{_random_string(40)}",
            },
        ],
        "total": 3,
        "page": 1,
    }


def _fake_debug_info() -> dict:
    """Generate fake debug/server info."""
    return {
        "server": {
            "hostname": "spatium-prod-01",
            "ip": "10.0.1.15",
            "os": "Ubuntu 22.04 LTS",
            "python": "3.11.4",
            "uptime_hours": random.randint(100, 1000),
        },
        "database": {
            "host": "db.internal",
            "port": 5432,
            "name": "spatium_production",
            "pool_size": 20,
            "active_connections": random.randint(5, 15),
        },
        "cache": {
            "type": "redis",
            "host": "redis.internal",
            "hit_rate": f"{random.uniform(85, 99):.1f}%",
        },
        "api_keys_active": random.randint(50, 200),
        "last_deploy": "2024-03-15T08:00:00Z",
        "debug_mode": True,  # Bait!
        "internal_endpoints": [
            "/api/internal/metrics",
            "/api/internal/health",
            "/api/internal/config",
        ],
    }


def _fake_git_config() -> str:
    """Generate fake git config."""
    return """[core]
    repositoryformatversion = 0
    filemode = true
    bare = false
    logallrefupdates = true
[remote "origin"]
    url = git@github.com:spatium-corp/spatium-computationis.git
    fetch = +refs/heads/*:refs/remotes/origin/*
[branch "main"]
    remote = origin
    merge = refs/heads/main
[user]
    name = Deploy Bot
    email = deploy@spatium-computationis.local
"""


def _fake_sql_backup() -> str:
    """Generate fake SQL backup header."""
    return f"""-- MySQL dump 10.13  Distrib 8.0.32
-- Host: db.internal    Database: spatium_production
-- HONEYPOT: This is fake data for security research
-- ------------------------------------------------------
-- Server version   8.0.32

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `api_key` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `users`
--

INSERT INTO `users` VALUES 
(1,'admin','admin@spatium.local','$2b$12$fake_hash_{_random_string(22)}','adm_{_random_string(32)}'),
(2,'operator','op@spatium.local','$2b$12$fake_hash_{_random_string(22)}','op_{_random_string(32)}');

-- Dump completed on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}
"""


# ---------------------------------------------------------------------------
# Response Generator
# ---------------------------------------------------------------------------

def get_trap_response(path: str, method: str = "GET") -> tuple[str | dict, str, int]:
    """
    Generate a convincing fake response for a honeypot trap.
    
    Returns: (content, content_type, status_code)
    """
    trap_config = TRAP_REGISTRY.get(path)
    if not trap_config:
        # Unknown trap path - return generic response
        return {"error": "Not found", "path": path}, "application/json", 404
    
    trap_type = trap_config["type"]
    content_type = trap_config["response_type"]
    
    # Config files
    if trap_type == TrapType.CONFIG_FILE:
        if ".env" in path:
            return _fake_env_file(), "text/plain", 200
        elif "wp-config" in path:
            return _fake_wp_config(), "application/x-php", 200
        elif "config.php" in path:
            return _fake_wp_config(), "application/x-php", 200
        elif "settings.py" in path:
            return f"# Django settings\nSECRET_KEY = '{_random_string(50)}'", "text/x-python", 200
    
    # Admin panels
    elif trap_type == TrapType.ADMIN_PANEL:
        return _fake_admin_login_page(), "text/html", 200
    
    # Login forms
    elif trap_type == TrapType.LOGIN_FORM:
        if method == "POST":
            # Log the credentials they tried!
            return {"status": "error", "message": "Invalid credentials"}, "application/json", 401
        return _fake_admin_login_page(), "text/html", 200
    
    # API endpoints
    elif trap_type == TrapType.API_ENDPOINT:
        if "users" in path:
            return _fake_users_api(), "application/json", 200
        elif "debug" in path or "config" in path:
            return _fake_debug_info(), "application/json", 200
        elif "graphql" in path:
            return {
                "data": None,
                "errors": [{"message": "Unauthorized", "extensions": {"code": "UNAUTHENTICATED"}}],
                "__schema_url": "/graphql/schema",
            }, "application/json", 401
        else:
            return {"status": "ok", "admin_token": f"admin_{_random_string(32)}"}, "application/json", 200
    
    # Debug info
    elif trap_type == TrapType.DEBUG_INFO:
        if "phpinfo" in path or "info.php" in path:
            return "<html><body><h1>PHP Version 8.2.0</h1><p>HONEYPOT</p></body></html>", "text/html", 200
        elif "status" in path:
            return _fake_debug_info(), "application/json", 200
        else:
            return _fake_debug_info(), "application/json", 200
    
    # Backup files
    elif trap_type == TrapType.BACKUP_FILE:
        if ".sql" in path:
            return _fake_sql_backup(), "application/sql", 200
        else:
            return "PK\x03\x04 (fake zip header)", "application/zip", 200
    
    # Git exposure
    elif trap_type == TrapType.GIT_REPO:
        if "config" in path:
            return _fake_git_config(), "text/plain", 200
        elif "HEAD" in path:
            return "ref: refs/heads/main", "text/plain", 200
        elif "gitignore" in path:
            return ".env\n*.log\nnode_modules/\n__pycache__/\n.secret", "text/plain", 200
    
    # Database endpoints
    elif trap_type == TrapType.DATABASE:
        return {
            "databases": ["spatium_production", "spatium_staging"],
            "connection_string": f"postgresql://admin:{_random_string(16)}@db.internal:5432/spatium",
        }, "application/json", 200
    
    # Default fallback
    return {"honeypot": True}, "application/json", 200


def is_honeypot_path(path: str) -> bool:
    """Check if a path is a registered honeypot trap."""
    return path in TRAP_REGISTRY


def get_trap_type(path: str) -> TrapType | None:
    """Get the trap type for a path."""
    config = TRAP_REGISTRY.get(path)
    return config["type"] if config else None
