"""
Agent: Webmaster GoDaddy 🌐
Role: Manage GoDaddy domains, DNS, hosting, and SSL certificates.

Provides:
- Domain lifecycle management (register, renew, transfer)
- DNS record configuration
- SSL certificate provisioning and renewal
- Website deployment to GoDaddy hosting
- Site health monitoring

Glyph: 🌐 (web management)
Capabilities: TRANSFORMATION, COMMUNICATION
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ...integrations.godaddy_client import GoDaddyClient, DNSRecord
from ...scaffolds.base import (
    AgentCapability,
    AgentConfig,
    CapabilityType,
    register_agent,
)


# ---------------------------------------------------------------------------
# Agent Registration
# ---------------------------------------------------------------------------

AGENT_CONFIG = AgentConfig(
    agent_name="webmaster-godaddy",
    agent_class="WebmasterGoDaddy",
    version="1.0.0",
    glyph="🌐",
    description="GoDaddy website management — domains, DNS, hosting, SSL",
    primary_region="marketing",
    capabilities=[
        AgentCapability(
            capability_id="wg-domain-management",
            capability_type=CapabilityType.COMMUNICATION,
            name="Domain Management",
            description="Register, renew, and manage GoDaddy domains",
            input_types=["domain_name", "action_request"],
            output_types=["domain_info", "action_result"],
        ),
        AgentCapability(
            capability_id="wg-dns-management",
            capability_type=CapabilityType.TRANSFORMATION,
            name="DNS Management",
            description="Configure DNS records for domains",
            input_types=["domain_name", "dns_config"],
            output_types=["dns_records", "action_result"],
        ),
        AgentCapability(
            capability_id="wg-ssl-management",
            capability_type=CapabilityType.COMMUNICATION,
            name="SSL Management",
            description="Provision and manage SSL certificates",
            input_types=["domain_name"],
            output_types=["certificate_info", "action_result"],
        ),
        AgentCapability(
            capability_id="wg-site-deployment",
            capability_type=CapabilityType.TRANSFORMATION,
            name="Site Deployment",
            description="Deploy and update websites on GoDaddy hosting",
            input_types=["hosting_id", "site_files"],
            output_types=["deployment_result"],
        ),
    ],
    requires_external_api=True,
    features={"godaddy_api": True, "auto_renewal": True, "ssl_auto_provision": True},
)


def _register() -> None:
    """Register this agent with the scaffold system."""
    register_agent(AGENT_CONFIG)


# ---------------------------------------------------------------------------
# Core Agent Logic
# ---------------------------------------------------------------------------

_client: GoDaddyClient | None = None


def _get_client() -> GoDaddyClient:
    global _client
    if _client is None:
        _client = GoDaddyClient()
    return _client


async def list_domains() -> list[dict[str, Any]]:
    """List all domains in the GoDaddy account."""
    client = _get_client()
    domains = await client.list_domains()
    return [
        {
            "domain": d.domain,
            "status": d.status,
            "expires": d.expires,
            "renewable": d.renewable,
        }
        for d in domains
    ]


async def get_domain_details(domain: str) -> dict[str, Any]:
    """Get detailed information about a domain."""
    client = _get_client()
    info = await client.get_domain(domain)
    return {
        "domain": info.domain,
        "status": info.status,
        "expires": info.expires,
        "renewable": info.renewable,
        "nameservers": info.nameservers,
    }


async def check_domain_availability(domain: str) -> dict[str, Any]:
    """Check if a domain is available for registration."""
    client = _get_client()
    return await client.check_availability(domain)


async def configure_dns(domain: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    """Configure DNS records for a domain."""
    client = _get_client()
    results = []
    for rec in records:
        dns_record = DNSRecord(
            record_type=rec["type"],
            name=rec["name"],
            data=rec["data"],
            ttl=rec.get("ttl", 3600),
            priority=rec.get("priority"),
        )
        await client.add_dns_record(domain, dns_record)
        results.append({"record": rec["name"], "status": "configured"})
    return {"domain": domain, "records_configured": results}


async def provision_ssl(domain: str) -> dict[str, Any]:
    """Provision an SSL certificate for a domain."""
    client = _get_client()
    result = await client.purchase_certificate(domain)
    return {"domain": domain, "ssl_status": "provisioning", "details": result}


async def deploy_website(domain: str, hosting_id: str, files: dict[str, str]) -> dict[str, Any]:
    """Deploy website files to GoDaddy hosting."""
    client = _get_client()
    result = await client.deploy_site(hosting_id, files)
    return {
        "domain": domain,
        "hosting_id": hosting_id,
        "status": "deployed",
        "files_count": len(files),
        "details": result,
    }


async def renew_domain(domain: str, years: int = 1) -> dict[str, Any]:
    """Renew a domain registration."""
    client = _get_client()
    result = await client.renew_domain(domain, years)
    return {"domain": domain, "renewed_years": years, "details": result}


async def run(request: dict[str, Any]) -> dict[str, Any]:
    """
    Main entry point for the webmaster agent.

    Accepts a request dict with 'action' and relevant parameters.
    """
    action = request.get("action", "")
    domain = request.get("domain", "")

    if action == "list_domains":
        return {"result": await list_domains()}
    elif action == "get_domain":
        return {"result": await get_domain_details(domain)}
    elif action == "check_availability":
        return {"result": await check_domain_availability(domain)}
    elif action == "configure_dns":
        records = request.get("records", [])
        return {"result": await configure_dns(domain, records)}
    elif action == "provision_ssl":
        return {"result": await provision_ssl(domain)}
    elif action == "deploy":
        hosting_id = request.get("hosting_id", "")
        files = request.get("files", {})
        return {"result": await deploy_website(domain, hosting_id, files)}
    elif action == "renew":
        years = request.get("years", 1)
        return {"result": await renew_domain(domain, years)}
    else:
        return {"error": f"Unknown action: {action}"}
