"""
Honeypot Routes — Deceptive FastAPI endpoints
🜏 Attract attackers with fake but convincing endpoints.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from .collector import FingerprintCollector
from .traps import TRAP_REGISTRY, get_trap_response, get_trap_type

honeypot_router = APIRouter(tags=["honeypot"])


# ---------------------------------------------------------------------------
# Middleware-like request processing
# ---------------------------------------------------------------------------

async def process_honeypot_request(
    request: Request,
    path: str,
) -> Response:
    """
    Process a honeypot request: collect fingerprint, log event, serve fake data.
    """
    start_time = time.time()
    
    # Extract request details
    ip_address = request.client.host if request.client else "unknown"
    method = request.method
    user_agent = request.headers.get("user-agent")
    accept_language = request.headers.get("accept-language")
    accept_encoding = request.headers.get("accept-encoding")
    
    # Get headers as dict (exclude some sensitive ones)
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ["authorization", "cookie"]
    }
    
    # Get query params
    query_params = dict(request.query_params)
    
    # Get body for POST requests
    body = None
    if method in ["POST", "PUT", "PATCH"]:
        try:
            body = (await request.body()).decode("utf-8", errors="replace")
        except Exception:
            body = None
    
    # Generate fake response
    content, content_type, status_code = get_trap_response(path, method)
    
    # Calculate response time
    response_time_ms = (time.time() - start_time) * 1000
    
    # Collect fingerprint
    fingerprint = FingerprintCollector.collect(
        ip_address=ip_address,
        path=path,
        method=method,
        status_code=status_code,
        user_agent=user_agent,
        accept_language=accept_language,
        accept_encoding=accept_encoding,
        response_time_ms=response_time_ms,
    )
    
    # Record honeypot trigger
    trap_type = get_trap_type(path)
    if trap_type:
        FingerprintCollector.record_honeypot_trigger(
            fingerprint_id=fingerprint.fingerprint_id,
            ip_address=ip_address,
            trap_type=trap_type,
            trap_path=path,
            method=method,
            headers=headers,
            query_params=query_params,
            body=body,
            response_code=status_code,
            fake_data_served=True,
            engagement_type=f"fake_{trap_type.value}",
        )
    
    # Return appropriate response type
    if content_type == "application/json":
        return JSONResponse(
            content=content if isinstance(content, dict) else {"data": content},
            status_code=status_code,
        )
    elif content_type == "text/html":
        return HTMLResponse(content=content, status_code=status_code)
    else:
        return PlainTextResponse(
            content=content if isinstance(content, str) else str(content),
            status_code=status_code,
            media_type=content_type,
        )


# ---------------------------------------------------------------------------
# Config File Traps
# ---------------------------------------------------------------------------

@honeypot_router.get("/.env")
@honeypot_router.get("/.env.local")
@honeypot_router.get("/.env.production")
@honeypot_router.get("/.env.development")
async def env_file(request: Request):
    """Fake environment file — attracts credential hunters."""
    path = request.url.path
    return await process_honeypot_request(request, path)


@honeypot_router.get("/config.php")
@honeypot_router.get("/wp-config.php")
@honeypot_router.get("/configuration.php")
async def php_config(request: Request):
    """Fake PHP config — attracts WordPress/Joomla scanners."""
    path = request.url.path
    return await process_honeypot_request(request, path)


@honeypot_router.get("/settings.py")
@honeypot_router.get("/local_settings.py")
async def python_config(request: Request):
    """Fake Python config — attracts Django/Flask scanners."""
    path = request.url.path
    return await process_honeypot_request(request, path)


# ---------------------------------------------------------------------------
# Admin Panel Traps
# ---------------------------------------------------------------------------

@honeypot_router.get("/admin")
@honeypot_router.get("/admin/")
@honeypot_router.get("/admin/login")
@honeypot_router.post("/admin/login")
async def admin_panel(request: Request):
    """Fake admin panel — attracts admin brute-forcers."""
    return await process_honeypot_request(request, "/admin")


@honeypot_router.get("/wp-admin")
@honeypot_router.get("/wp-admin/")
@honeypot_router.get("/wp-admin/admin.php")
async def wp_admin(request: Request):
    """Fake WordPress admin — attracts WP scanners."""
    return await process_honeypot_request(request, "/wp-admin")


@honeypot_router.get("/administrator")
@honeypot_router.get("/administrator/")
async def joomla_admin(request: Request):
    """Fake Joomla admin — attracts Joomla scanners."""
    return await process_honeypot_request(request, "/administrator")


@honeypot_router.get("/cpanel")
@honeypot_router.get("/cpanel/")
async def cpanel(request: Request):
    """Fake cPanel — attracts hosting scanners."""
    return await process_honeypot_request(request, "/cpanel")


@honeypot_router.get("/phpmyadmin")
@honeypot_router.get("/phpmyadmin/")
@honeypot_router.get("/pma")
@honeypot_router.get("/pma/")
async def phpmyadmin(request: Request):
    """Fake phpMyAdmin — attracts database scanners."""
    return await process_honeypot_request(request, "/phpmyadmin")


# ---------------------------------------------------------------------------
# Login Form Traps
# ---------------------------------------------------------------------------

@honeypot_router.get("/wp-login.php")
@honeypot_router.post("/wp-login.php")
async def wp_login(request: Request):
    """Fake WordPress login — attracts credential stuffers."""
    return await process_honeypot_request(request, "/wp-login.php")


@honeypot_router.get("/login")
@honeypot_router.post("/login")
@honeypot_router.get("/signin")
@honeypot_router.post("/signin")
async def login_page(request: Request):
    """Fake login page — attracts credential stuffers."""
    return await process_honeypot_request(request, "/login")


@honeypot_router.get("/user/login")
@honeypot_router.post("/user/login")
async def user_login(request: Request):
    """Fake user login — attracts credential stuffers."""
    return await process_honeypot_request(request, "/user/login")


# ---------------------------------------------------------------------------
# API Endpoint Traps
# ---------------------------------------------------------------------------

@honeypot_router.api_route("/api/admin", methods=["GET", "POST", "PUT", "DELETE"])
@honeypot_router.api_route("/api/admin/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def api_admin(request: Request, path: str = ""):
    """Fake admin API — attracts API scanners."""
    return await process_honeypot_request(request, "/api/admin")


@honeypot_router.get("/api/v1/users")
@honeypot_router.get("/api/v1/users/{user_id}")
@honeypot_router.get("/api/users")
async def api_users(request: Request, user_id: str = ""):
    """Fake users API — attracts data harvesters."""
    return await process_honeypot_request(request, "/api/v1/users")


@honeypot_router.get("/api/v1/config")
@honeypot_router.get("/api/config")
async def api_config(request: Request):
    """Fake config API — attracts config hunters."""
    return await process_honeypot_request(request, "/api/v1/config")


@honeypot_router.get("/api/debug")
@honeypot_router.get("/api/v1/debug")
async def api_debug(request: Request):
    """Fake debug API — attracts debug info hunters."""
    return await process_honeypot_request(request, "/api/debug")


@honeypot_router.api_route("/graphql", methods=["GET", "POST"])
async def graphql_endpoint(request: Request):
    """Fake GraphQL — attracts GraphQL scanners."""
    return await process_honeypot_request(request, "/graphql")


# ---------------------------------------------------------------------------
# Debug/Info Traps
# ---------------------------------------------------------------------------

@honeypot_router.get("/debug")
@honeypot_router.get("/debug/")
async def debug_page(request: Request):
    """Fake debug page — attracts info gatherers."""
    return await process_honeypot_request(request, "/debug")


@honeypot_router.get("/server-status")
@honeypot_router.get("/server-info")
async def server_status(request: Request):
    """Fake Apache status — attracts server scanners."""
    return await process_honeypot_request(request, "/server-status")


@honeypot_router.get("/phpinfo.php")
@honeypot_router.get("/info.php")
@honeypot_router.get("/test.php")
async def php_info(request: Request):
    """Fake PHP info — attracts PHP scanners."""
    return await process_honeypot_request(request, "/phpinfo.php")


@honeypot_router.get("/status")
@honeypot_router.get("/_status")
@honeypot_router.get("/health")
async def status_endpoint(request: Request):
    """Fake status endpoint — attracts monitoring scanners."""
    return await process_honeypot_request(request, "/status")


# ---------------------------------------------------------------------------
# Backup File Traps
# ---------------------------------------------------------------------------

@honeypot_router.get("/backup.sql")
@honeypot_router.get("/backup.sql.gz")
@honeypot_router.get("/database.sql")
@honeypot_router.get("/db.sql")
@honeypot_router.get("/dump.sql")
async def sql_backup(request: Request):
    """Fake SQL backup — attracts backup hunters."""
    path = request.url.path
    return await process_honeypot_request(request, path if path in TRAP_REGISTRY else "/backup.sql")


@honeypot_router.get("/backup.zip")
@honeypot_router.get("/backup.tar.gz")
@honeypot_router.get("/site.zip")
async def archive_backup(request: Request):
    """Fake backup archive — attracts backup hunters."""
    return await process_honeypot_request(request, "/backup.zip")


# ---------------------------------------------------------------------------
# Git Exposure Traps
# ---------------------------------------------------------------------------

@honeypot_router.get("/.git/config")
@honeypot_router.get("/.git/HEAD")
@honeypot_router.get("/.git/index")
@honeypot_router.get("/.git/logs/HEAD")
async def git_files(request: Request):
    """Fake git files — attracts git exposure scanners."""
    path = request.url.path
    if "/config" in path:
        return await process_honeypot_request(request, "/.git/config")
    elif "/HEAD" in path:
        return await process_honeypot_request(request, "/.git/HEAD")
    return await process_honeypot_request(request, "/.git/config")


@honeypot_router.get("/.gitignore")
async def gitignore(request: Request):
    """Fake gitignore — reveals interesting paths to attackers."""
    return await process_honeypot_request(request, "/.gitignore")


# ---------------------------------------------------------------------------
# Database Traps
# ---------------------------------------------------------------------------

@honeypot_router.get("/db")
@honeypot_router.get("/database")
async def db_endpoint(request: Request):
    """Fake database endpoint — attracts DB hunters."""
    return await process_honeypot_request(request, "/db")


@honeypot_router.get("/mysql")
@honeypot_router.get("/mysql/")
async def mysql_endpoint(request: Request):
    """Fake MySQL endpoint — attracts MySQL hunters."""
    return await process_honeypot_request(request, "/mysql")


@honeypot_router.get("/mongodb")
@honeypot_router.get("/mongo")
async def mongodb_endpoint(request: Request):
    """Fake MongoDB endpoint — attracts MongoDB hunters."""
    return await process_honeypot_request(request, "/mongodb")


# ---------------------------------------------------------------------------
# Wildcard Catch-All for Common Attack Paths
# ---------------------------------------------------------------------------

# Common vulnerability paths
@honeypot_router.get("/xmlrpc.php")
@honeypot_router.post("/xmlrpc.php")
async def xmlrpc(request: Request):
    """Fake XML-RPC — attracts WordPress exploiters."""
    return await process_honeypot_request(request, "/xmlrpc.php")


@honeypot_router.get("/.htaccess")
@honeypot_router.get("/.htpasswd")
async def htaccess(request: Request):
    """Fake Apache config — attracts Apache scanners."""
    return await process_honeypot_request(request, "/.htaccess")


@honeypot_router.get("/robots.txt.bak")
@honeypot_router.get("/sitemap.xml.bak")
async def backup_files(request: Request):
    """Fake backup files — attracts backup hunters."""
    return await process_honeypot_request(request, "/backup.sql")
