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
    
    # WordPress deep probes (from traffic analysis)
    "/wp-includes/wlwmanifest.xml": {
        "type": TrapType.CONFIG_FILE,
        "description": "Fake WLW manifest",
        "response_type": "application/xml",
    },
    "/wp-includes/js/jquery/jquery.min.js": {
        "type": TrapType.CONFIG_FILE,
        "description": "Fake jQuery",
        "response_type": "application/javascript",
    },
    "/wp-content/plugins/": {
        "type": TrapType.CONFIG_FILE,
        "description": "Fake plugin directory",
        "response_type": "text/html",
    },
    "/wp-content/themes/": {
        "type": TrapType.CONFIG_FILE,
        "description": "Fake theme directory",
        "response_type": "text/html",
    },
    "/wp-json/": {
        "type": TrapType.API_ENDPOINT,
        "description": "Fake WP REST API",
        "response_type": "application/json",
    },
    "/wp-admin/admin-ajax.php": {
        "type": TrapType.API_ENDPOINT,
        "description": "Fake admin AJAX",
        "response_type": "application/json",
    },
    "/xmlrpc.php": {
        "type": TrapType.API_ENDPOINT,
        "description": "Fake XML-RPC",
        "response_type": "text/xml",
    },
    
    # Cloudflare probes (from traffic analysis)
    "/cdn-cgi/rum": {
        "type": TrapType.DEBUG_INFO,
        "description": "Fake CF RUM beacon",
        "response_type": "application/json",
    },
    "/cdn-cgi/trace": {
        "type": TrapType.DEBUG_INFO,
        "description": "Fake CF trace",
        "response_type": "text/plain",
    },
    "/cdn-cgi/challenge-platform/": {
        "type": TrapType.DEBUG_INFO,
        "description": "Fake CF challenge",
        "response_type": "text/html",
    },
    
    # Cloud infrastructure probes
    "/.aws/credentials": {
        "type": TrapType.CONFIG_FILE,
        "description": "Fake AWS credentials",
        "response_type": "text/plain",
    },
    "/.docker/config.json": {
        "type": TrapType.CONFIG_FILE,
        "description": "Fake Docker config",
        "response_type": "application/json",
    },
    "/actuator/health": {
        "type": TrapType.DEBUG_INFO,
        "description": "Fake Spring health",
        "response_type": "application/json",
    },
    "/actuator/env": {
        "type": TrapType.DEBUG_INFO,
        "description": "Fake Spring env",
        "response_type": "application/json",
    },
    
    # Linux system paths (LFI probes)
    "/etc/passwd": {
        "type": TrapType.CONFIG_FILE,
        "description": "Fake passwd file",
        "response_type": "text/plain",
    },
    "/proc/self/environ": {
        "type": TrapType.CONFIG_FILE,
        "description": "Fake proc environ",
        "response_type": "text/plain",
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


def _fake_aws_credentials() -> str:
    """Generate fake AWS credentials file."""
    return f"""[default]
aws_access_key_id = AKIA{_random_string(16).upper()}
aws_secret_access_key = {_random_string(40)}
region = us-east-1

[production]
aws_access_key_id = AKIA{_random_string(16).upper()}
aws_secret_access_key = {_random_string(40)}
region = us-west-2
role_arn = arn:aws:iam::123456789012:role/ProductionAdmin
"""


def _fake_docker_config() -> dict:
    """Generate fake Docker config."""
    return {
        "auths": {
            "registry.spatium.local": {
                "auth": _random_string(64),
                "email": "deploy@spatium.local"
            },
            "docker.io": {
                "auth": _random_string(64)
            },
            "ghcr.io": {
                "auth": _random_string(64)
            }
        },
        "credsStore": "desktop"
    }


def _fake_spring_actuator_health() -> dict:
    """Generate fake Spring Boot health endpoint."""
    return {
        "status": "UP",
        "components": {
            "db": {
                "status": "UP",
                "details": {
                    "database": "PostgreSQL",
                    "validationQuery": "isValid()"
                }
            },
            "redis": {
                "status": "UP",
                "details": {
                    "version": "7.0.11"
                }
            },
            "diskSpace": {
                "status": "UP",
                "details": {
                    "total": 107374182400,
                    "free": 85899345920,
                    "threshold": 10485760
                }
            }
        }
    }


def _fake_spring_actuator_env() -> dict:
    """Generate fake Spring Boot env endpoint."""
    return {
        "activeProfiles": ["production"],
        "propertySources": [
            {
                "name": "systemEnvironment",
                "properties": {
                    "DB_PASSWORD": {"value": f"******{_random_string(4)}"},
                    "AWS_SECRET_KEY": {"value": "******"},
                    "SPRING_PROFILES_ACTIVE": {"value": "production"},
                }
            },
            {
                "name": "application.properties",
                "properties": {
                    "server.port": {"value": "8080"},
                    "spring.datasource.url": {"value": "jdbc:postgresql://db.internal:5432/spatium"},
                }
            }
        ]
    }


def _fake_cloudflare_trace() -> str:
    """Generate fake Cloudflare trace output."""
    return f"""fl=fake123
h=spatium-computationis.local
ip=10.0.0.1
ts={datetime.now(timezone.utc).timestamp()}
visit_scheme=https
uag=Mozilla/5.0 (compatible; Googlebot/2.1)
colo=SJC
sliver=none
http=http/2
loc=US
tls=TLSv1.3
sni=plaintext
warp=off
gateway=off
rbi=off
kex=X25519
"""


def _fake_wp_wlw_manifest() -> str:
    """Generate fake Windows Live Writer manifest."""
    return """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns="http://schemas.microsoft.com/wlw/manifest/weblog">
  <options>
    <clientType>WordPress</clientType>
    <supportsKeywords>Yes</supportsKeywords>
    <supportsGetTags>Yes</supportsGetTags>
  </options>
  <weblog>
    <serviceName>WordPress</serviceName>
    <imageUrl>images/wlw/wp-icon.png</imageUrl>
    <watermarkImageUrl>images/wlw/wp-watermark.png</watermarkImageUrl>
    <homepageLinkText>View site</homepageLinkText>
    <adminLinkText>Dashboard</adminLinkText>
    <adminUrl>
      <![CDATA[{blog-postapi-url}/../wp-admin/]]>
    </adminUrl>
  </weblog>
</manifest>
"""


def _fake_wp_rest_api() -> dict:
    """Generate fake WordPress REST API response."""
    return {
        "name": "Spatium Computationis",
        "description": "Research & Development",
        "url": "https://spatium-computationis.local",
        "home": "https://spatium-computationis.local",
        "gmt_offset": 0,
        "timezone_string": "UTC",
        "namespaces": ["wp/v2", "wp-site-health/v1"],
        "authentication": [],
        "routes": {
            "/wp/v2": {"namespace": "wp/v2", "methods": ["GET"]},
            "/wp/v2/posts": {"namespace": "wp/v2", "methods": ["GET", "POST"]},
            "/wp/v2/users": {"namespace": "wp/v2", "methods": ["GET"]},
        }
    }


def _fake_passwd_file() -> str:
    """Generate fake /etc/passwd file."""
    return """root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin
spatium:x:1000:1000:Spatium,,,:/home/spatium:/bin/bash
postgres:x:999:999:PostgreSQL administrator,,,:/var/lib/postgresql:/bin/bash
deploy:x:1001:1001:Deploy User:/home/deploy:/bin/bash
"""


def _fake_proc_environ() -> str:
    """Generate fake /proc/self/environ."""
    return f"PATH=/usr/local/bin:/usr/bin:/bin\x00HOME=/home/spatium\x00USER=spatium\x00DB_PASSWORD={_random_string(16)}\x00SECRET_KEY={_random_string(32)}\x00AWS_ACCESS_KEY_ID=AKIA{_random_string(16).upper()}\x00"


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
        # Check for partial path matches
        for trap_path, config in TRAP_REGISTRY.items():
            if path.startswith(trap_path) or trap_path in path:
                trap_config = config
                break
    
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
        elif ".aws/credentials" in path:
            return _fake_aws_credentials(), "text/plain", 200
        elif ".docker/config.json" in path:
            return _fake_docker_config(), "application/json", 200
        elif "wlwmanifest.xml" in path:
            return _fake_wp_wlw_manifest(), "application/xml", 200
        elif "jquery" in path:
            return "/* jQuery v3.6.0 - HONEYPOT */", "application/javascript", 200
        elif "etc/passwd" in path:
            return _fake_passwd_file(), "text/plain", 200
        elif "proc/self/environ" in path:
            return _fake_proc_environ(), "text/plain", 200
        elif "wp-content/plugins" in path or "wp-content/themes" in path:
            return "<html><body><h1>Index of /</h1><hr><pre>../</pre></body></html>", "text/html", 200
    
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
        elif "wp-json" in path:
            return _fake_wp_rest_api(), "application/json", 200
        elif "admin-ajax" in path:
            return {"success": False, "data": "Unauthorized"}, "application/json", 403
        elif "xmlrpc" in path:
            return """<?xml version="1.0"?><methodResponse><fault><value><struct><member><name>faultCode</name><value><int>403</int></value></member><member><name>faultString</name><value><string>XML-RPC services are disabled</string></value></member></struct></value></fault></methodResponse>""", "text/xml", 200
        else:
            return {"status": "ok", "admin_token": f"admin_{_random_string(32)}"}, "application/json", 200
    
    # Debug info
    elif trap_type == TrapType.DEBUG_INFO:
        if "phpinfo" in path or "info.php" in path:
            return "<html><body><h1>PHP Version 8.2.0</h1><p>HONEYPOT</p></body></html>", "text/html", 200
        elif "cdn-cgi/trace" in path:
            return _fake_cloudflare_trace(), "text/plain", 200
        elif "cdn-cgi/rum" in path:
            return {"beacon": "ok", "timing": random.randint(100, 500)}, "application/json", 200
        elif "cdn-cgi/challenge" in path:
            return "<html><body>Challenge required</body></html>", "text/html", 403
        elif "actuator/health" in path:
            return _fake_spring_actuator_health(), "application/json", 200
        elif "actuator/env" in path:
            return _fake_spring_actuator_env(), "application/json", 200
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
