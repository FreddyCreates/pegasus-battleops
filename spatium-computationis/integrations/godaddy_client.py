"""
GoDaddy API Client — Shared module for domain, hosting, and DNS operations.

Wraps the GoDaddy REST API for use by marketing and webmaster agents.
Requires GODADDY_API_KEY and GODADDY_API_SECRET environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


GODADDY_BASE_URL = "https://api.godaddy.com/v1"
GODADDY_OTE_URL = "https://api.ote-godaddy.com/v1"  # Test environment


@dataclass
class DomainInfo:
    """Domain registration information."""
    domain: str
    status: str
    expires: str | None = None
    renewable: bool = True
    nameservers: list[str] | None = None


@dataclass
class DNSRecord:
    """DNS record representation."""
    record_type: str  # A, AAAA, CNAME, MX, TXT, NS, SRV
    name: str
    data: str
    ttl: int = 3600
    priority: int | None = None


@dataclass
class SSLCertificate:
    """SSL certificate information."""
    certificate_id: str
    domain: str
    status: str
    expires: str | None = None
    cert_type: str = "DV_SSL"


class GoDaddyClient:
    """
    Client for GoDaddy API operations.

    Supports:
    - Domain management (list, get details, check availability)
    - DNS record management (list, create, update, delete)
    - SSL certificate operations
    - Hosting management
    """

    def __init__(self, api_key: str | None = None, api_secret: str | None = None, use_ote: bool = False):
        self.api_key = api_key or os.getenv("GODADDY_API_KEY", "")
        self.api_secret = api_secret or os.getenv("GODADDY_API_SECRET", "")
        self.base_url = GODADDY_OTE_URL if use_ote else GODADDY_BASE_URL

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"sso-key {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict | list:
        """Make an authenticated request to the GoDaddy API."""
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            timeout=30.0,
        ) as client:
            resp = await client.request(method, path, **kwargs)
            resp.raise_for_status()
            return resp.json()

    # -----------------------------------------------------------------------
    # Domain Operations
    # -----------------------------------------------------------------------

    async def list_domains(self) -> list[DomainInfo]:
        """List all domains in the account."""
        data = await self._request("GET", "/domains")
        return [
            DomainInfo(
                domain=d["domain"],
                status=d.get("status", "unknown"),
                expires=d.get("expires"),
                renewable=d.get("renewable", True),
                nameservers=d.get("nameServers"),
            )
            for d in data
        ]

    async def get_domain(self, domain: str) -> DomainInfo:
        """Get details for a specific domain."""
        d = await self._request("GET", f"/domains/{domain}")
        return DomainInfo(
            domain=d["domain"],
            status=d.get("status", "unknown"),
            expires=d.get("expires"),
            renewable=d.get("renewable", True),
            nameservers=d.get("nameServers"),
        )

    async def check_availability(self, domain: str) -> dict:
        """Check if a domain is available for registration."""
        return await self._request("GET", f"/domains/available?domain={domain}")

    async def renew_domain(self, domain: str, years: int = 1) -> dict:
        """Renew a domain registration."""
        return await self._request(
            "POST",
            f"/domains/{domain}/renew",
            json={"period": years},
        )

    # -----------------------------------------------------------------------
    # DNS Operations
    # -----------------------------------------------------------------------

    async def list_dns_records(self, domain: str, record_type: str | None = None) -> list[DNSRecord]:
        """List DNS records for a domain."""
        path = f"/domains/{domain}/records"
        if record_type:
            path += f"/{record_type}"
        data = await self._request("GET", path)
        return [
            DNSRecord(
                record_type=r["type"],
                name=r["name"],
                data=r["data"],
                ttl=r.get("ttl", 3600),
                priority=r.get("priority"),
            )
            for r in data
        ]

    async def add_dns_record(self, domain: str, record: DNSRecord) -> None:
        """Add a DNS record."""
        payload = [
            {
                "type": record.record_type,
                "name": record.name,
                "data": record.data,
                "ttl": record.ttl,
            }
        ]
        if record.priority is not None:
            payload[0]["priority"] = record.priority
        await self._request("PATCH", f"/domains/{domain}/records", json=payload)

    async def update_dns_record(self, domain: str, record: DNSRecord) -> None:
        """Update an existing DNS record."""
        payload = [{"data": record.data, "ttl": record.ttl}]
        if record.priority is not None:
            payload[0]["priority"] = record.priority
        await self._request(
            "PUT",
            f"/domains/{domain}/records/{record.record_type}/{record.name}",
            json=payload,
        )

    async def delete_dns_record(self, domain: str, record_type: str, name: str) -> None:
        """Delete a DNS record."""
        await self._request("DELETE", f"/domains/{domain}/records/{record_type}/{name}")

    # -----------------------------------------------------------------------
    # SSL Operations
    # -----------------------------------------------------------------------

    async def list_certificates(self) -> list[SSLCertificate]:
        """List SSL certificates."""
        data = await self._request("GET", "/certificates")
        return [
            SSLCertificate(
                certificate_id=c["certificateId"],
                domain=c.get("commonName", ""),
                status=c.get("status", "unknown"),
                expires=c.get("validEnd"),
                cert_type=c.get("type", "DV_SSL"),
            )
            for c in data
        ]

    async def purchase_certificate(self, domain: str, cert_type: str = "DV_SSL") -> dict:
        """Purchase a new SSL certificate."""
        return await self._request(
            "POST",
            "/certificates",
            json={
                "commonName": domain,
                "type": cert_type,
                "period": 1,
            },
        )

    # -----------------------------------------------------------------------
    # Hosting Operations
    # -----------------------------------------------------------------------

    async def list_hosting_accounts(self) -> list[dict]:
        """List hosting accounts."""
        return await self._request("GET", "/hosting")

    async def deploy_site(self, hosting_id: str, files: dict[str, str]) -> dict:
        """Deploy files to a hosting account (simplified)."""
        return await self._request(
            "POST",
            f"/hosting/{hosting_id}/deploy",
            json={"files": files},
        )
