/**
 * Request Handlers for the Defense Worker
 * ⛨ Core defense logic at Cloudflare's edge
 */

import {
  ThreatContext,
  WorkerEnv,
  DefenseDecision,
  CloudflareRequestCF,
  HONEYPOT_PATHS,
  SCANNER_SIGNATURES,
  VERIFIED_BOT_AGENTS,
} from './types';
import { generateChallengePage, generateBlockPage } from './pages';

/**
 * Main request handler
 */
export async function handleRequest(
  request: Request,
  env: WorkerEnv,
  ctx: ExecutionContext
): Promise<Response> {
  const url = new URL(request.url);
  const cf = (request as Request & { cf?: CloudflareRequestCF }).cf;

  // Build threat context from request
  const threatContext = buildThreatContext(request, cf);

  // Check if this is a honeypot path
  const isHoneypotPath = isHoneypotTarget(url.pathname);

  // Make defense decision
  const decision = makeDefenseDecision(threatContext, isHoneypotPath);

  // Send telemetry to Spatium API (non-blocking)
  ctx.waitUntil(sendToSpatiumAPI(env, threatContext, decision));

  // Apply decision
  switch (decision.action) {
    case 'block':
      return generateBlockPage(threatContext.rayId, decision.reason);

    case 'challenge':
      return generateChallengePage(threatContext.rayId);

    case 'honeypot':
    case 'engage':
      // Let request through to honeypot endpoints
      // Add headers to identify this as honeypot-routed traffic
      const modifiedRequest = new Request(request, {
        headers: new Headers([
          ...Array.from(request.headers.entries()),
          ['X-Spatium-Honeypot', 'true'],
          ['X-Spatium-Decision', decision.action],
          ['X-Spatium-Threat-Score', threatContext.threatScore.toString()],
          ['X-Spatium-Bot-Score', threatContext.botScore.toString()],
        ]),
      });
      return fetch(modifiedRequest);

    case 'allow':
    default:
      return fetch(request);
  }
}

/**
 * Build threat context from request and Cloudflare data
 */
function buildThreatContext(
  request: Request,
  cf?: CloudflareRequestCF
): ThreatContext {
  return {
    rayId: request.headers.get('CF-Ray') || crypto.randomUUID(),
    clientIP: request.headers.get('CF-Connecting-IP') || 'unknown',
    path: new URL(request.url).pathname,
    method: request.method,
    userAgent: request.headers.get('User-Agent'),
    botScore: cf?.botManagement?.score ?? 99,
    verifiedBot: cf?.botManagement?.verifiedBot ?? false,
    threatScore: cf?.threatScore ?? 0,
    country: cf?.country ?? 'unknown',
    asn: cf?.asn ?? 0,
    asnOrg: cf?.asOrganization ?? 'unknown',
    ja3Hash: cf?.botManagement?.ja3Hash ?? null,
    ja4: cf?.botManagement?.ja4 ?? null,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Check if path is a honeypot target
 */
function isHoneypotTarget(path: string): boolean {
  const pathLower = path.toLowerCase();
  return HONEYPOT_PATHS.some((hp) => pathLower.includes(hp));
}

/**
 * Check for known scanner tools in user agent
 */
function detectScanner(userAgent: string | null): boolean {
  if (!userAgent) return false;
  const uaLower = userAgent.toLowerCase();
  return SCANNER_SIGNATURES.some((sig) => uaLower.includes(sig));
}

/**
 * Check for known good bots
 */
function isKnownGoodBot(userAgent: string | null): boolean {
  if (!userAgent) return false;
  const uaLower = userAgent.toLowerCase();
  return VERIFIED_BOT_AGENTS.some((bot) => uaLower.includes(bot));
}

/**
 * Make defense decision based on threat context
 */
function makeDefenseDecision(
  ctx: ThreatContext,
  isHoneypotPath: boolean
): DefenseDecision {
  // Verified bots always pass
  if (ctx.verifiedBot || isKnownGoodBot(ctx.userAgent)) {
    return {
      action: 'allow',
      reason: 'verified_bot',
      confidence: 0.95,
    };
  }

  // Known scanner tools
  if (detectScanner(ctx.userAgent)) {
    return {
      action: isHoneypotPath ? 'engage' : 'challenge',
      reason: 'scanner_detected',
      confidence: 0.9,
    };
  }

  // Critical threat score - block
  if (ctx.threatScore >= 80) {
    return {
      action: 'block',
      reason: 'critical_threat_score',
      confidence: 0.95,
    };
  }

  // High threat score - challenge or redirect to honeypot
  if (ctx.threatScore >= 50) {
    return {
      action: isHoneypotPath ? 'engage' : 'challenge',
      reason: 'high_threat_score',
      confidence: 0.85,
    };
  }

  // Very low bot score (likely bot) + honeypot path = engage
  if (ctx.botScore < 30 && isHoneypotPath) {
    return {
      action: 'engage',
      reason: 'suspicious_bot_honeypot_access',
      confidence: 0.8,
    };
  }

  // Low bot score - challenge
  if (ctx.botScore < 30) {
    return {
      action: 'challenge',
      reason: 'low_bot_score',
      confidence: 0.7,
    };
  }

  // Honeypot path access by uncertain visitor
  if (isHoneypotPath && ctx.botScore < 60) {
    return {
      action: 'honeypot',
      reason: 'honeypot_path_access',
      confidence: 0.6,
    };
  }

  // Medium threat - allow but monitor
  if (ctx.threatScore >= 20 || ctx.botScore < 50) {
    return {
      action: 'allow',
      reason: 'monitoring',
      confidence: 0.5,
    };
  }

  // Default - allow
  return {
    action: 'allow',
    reason: 'no_threat_indicators',
    confidence: 0.9,
  };
}

/**
 * Send telemetry to Spatium API (non-blocking)
 */
async function sendToSpatiumAPI(
  env: WorkerEnv,
  ctx: ThreatContext,
  decision: DefenseDecision
): Promise<void> {
  const apiUrl = env.SPATIUM_API_URL;
  const apiSecret = env.SPATIUM_API_SECRET;

  if (!apiUrl) {
    return; // API not configured
  }

  try {
    await fetch(`${apiUrl}/defense/cloudflare/event`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(apiSecret && { 'X-API-Secret': apiSecret }),
      },
      body: JSON.stringify({
        ...ctx,
        decision: decision.action,
        decisionReason: decision.reason,
        decisionConfidence: decision.confidence,
      }),
    });
  } catch (error) {
    // Non-blocking - log and continue
    console.error('Failed to send to Spatium API:', error);
  }
}
