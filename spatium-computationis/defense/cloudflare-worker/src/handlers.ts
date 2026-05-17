/**
 * Request Handlers for the Defense Worker
 * ⛨ Core defense logic at Cloudflare's edge
 * 👁️ Shadow Decryption + Error Eyes integration
 * 🚪 Gatekeeper routing
 */

import {
  ThreatContext,
  WorkerEnv,
  DefenseDecision,
  CloudflareRequestCF,
  RequestEnvelope,
  HONEYPOT_PATHS,
  SCANNER_SIGNATURES,
  VERIFIED_BOT_AGENTS,
  AI_VISITOR_PATTERNS,
} from './types';
import { generateChallengePage, generateBlockPage, generateVIPWelcomePage } from './pages';

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

  // Detect AI visitors (VIP handling)
  const aiSource = detectAIVisitor(threatContext.userAgent, threatContext.clientIP);

  // Build request envelope for deeper processing
  const envelope = await buildRequestEnvelope(request, cf, aiSource);

  // Make defense decision
  const decision = makeDefenseDecision(threatContext, isHoneypotPath, aiSource, envelope);

  // Send telemetry to Spatium API (non-blocking)
  ctx.waitUntil(sendToSpatiumAPI(env, envelope, decision));

  // Apply decision
  switch (decision.action) {
    case 'block':
      return generateBlockPage(threatContext.rayId, decision.reason);

    case 'challenge':
      return generateChallengePage(threatContext.rayId);

    case 'vip_gate':
      // VIP AI visitors get special welcome
      return generateVIPWelcomePage(threatContext.rayId, aiSource || 'ai');

    case 'honeypot':
    case 'engage':
      // Let request through to honeypot endpoints
      // Add headers to identify this as honeypot-routed traffic
      const honeypotRequest = new Request(request, {
        headers: new Headers([
          ...Array.from(request.headers.entries()),
          ['X-Spatium-Honeypot', 'true'],
          ['X-Spatium-Decision', decision.action],
          ['X-Spatium-Route', decision.route || 'adversary_lab'],
          ['X-Spatium-Threat-Score', threatContext.threatScore.toString()],
          ['X-Spatium-Bot-Score', threatContext.botScore.toString()],
        ]),
      });
      return fetch(honeypotRequest);

    case 'shadow_decrypt':
      // Route to shadow decryption endpoint
      const shadowRequest = new Request(request, {
        headers: new Headers([
          ...Array.from(request.headers.entries()),
          ['X-Spatium-Shadow', 'true'],
          ['X-Spatium-Route', 'shadow_decrypt'],
          ['X-Spatium-Envelope-Id', envelope.envelopeId],
        ]),
      });
      return fetch(shadowRequest);

    case 'error_repair':
      // Route to error repair endpoint
      const repairRequest = new Request(request, {
        headers: new Headers([
          ...Array.from(request.headers.entries()),
          ['X-Spatium-Repair', 'true'],
          ['X-Spatium-Route', 'error_repair'],
          ['X-Spatium-Envelope-Id', envelope.envelopeId],
        ]),
      });
      return fetch(repairRequest);

    case 'allow':
    default:
      // Add envelope ID for tracking
      const trackedRequest = new Request(request, {
        headers: new Headers([
          ...Array.from(request.headers.entries()),
          ['X-Spatium-Envelope-Id', envelope.envelopeId],
          ...(aiSource ? [['X-Spatium-AI-Source', aiSource]] : []),
        ]),
      });
      return fetch(trackedRequest);
  }
}

/**
 * Detect if visitor is a known AI
 */
function detectAIVisitor(userAgent: string | null, clientIP: string): string | null {
  if (!userAgent) return null;
  const uaLower = userAgent.toLowerCase();

  for (const [aiName, patterns] of Object.entries(AI_VISITOR_PATTERNS)) {
    // Check user agent patterns
    if (patterns.userAgents.some((ua) => uaLower.includes(ua))) {
      return aiName;
    }
    // Check IP prefixes
    if (patterns.ipPrefixes.some((prefix) => clientIP.startsWith(prefix))) {
      return aiName;
    }
  }

  // Generic AI detection
  const aiIndicators = ['ai', 'bot', 'assistant', 'llm', 'language-model'];
  if (aiIndicators.some((ind) => uaLower.includes(ind))) {
    return 'unknown_ai';
  }

  return null;
}

/**
 * Build request envelope for deeper processing
 */
async function buildRequestEnvelope(
  request: Request,
  cf?: CloudflareRequestCF,
  aiSource?: string | null
): Promise<RequestEnvelope> {
  const url = new URL(request.url);

  // Parse query params
  const rawQuery: Record<string, string> = {};
  url.searchParams.forEach((value, key) => {
    rawQuery[key] = value;
  });

  // Parse headers
  const rawHeaders: Record<string, string> = {};
  request.headers.forEach((value, key) => {
    rawHeaders[key] = value;
  });

  // Get body if present
  let rawBody: string | undefined;
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    try {
      rawBody = await request.text();
    } catch {
      rawBody = undefined;
    }
  }

  // Detect if content looks encrypted or malformed
  const isEncrypted = rawBody ? isContentEncrypted(rawBody) : false;
  const isMalformed = rawBody ? isContentMalformed(rawBody, rawHeaders['content-type']) : false;

  return {
    envelopeId: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    sourceIp: request.headers.get('CF-Connecting-IP') || 'unknown',
    rawMethod: request.method,
    rawPath: url.pathname,
    rawHeaders,
    rawQuery,
    rawBody,
    cfRay: request.headers.get('CF-Ray') || undefined,
    cfCountry: cf?.country,
    cfAsn: cf?.asn,
    cfAsnOrg: cf?.asOrganization,
    cfThreatScore: cf?.threatScore,
    cfBotScore: cf?.botManagement?.score,
    cfVerifiedBot: cf?.botManagement?.verifiedBot ?? false,
    cfTlsVersion: cf?.tlsVersion,
    cfTlsCipher: cf?.tlsCipher,
    isEncrypted,
    isMalformed,
    hasError: false,
    aiSourceDetected: aiSource || undefined,
  };
}

/**
 * Check if content looks encrypted (high entropy)
 */
function isContentEncrypted(content: string): boolean {
  if (!content || content.length < 20) return false;

  // Check for base64-like patterns
  const base64Pattern = /^[A-Za-z0-9+/=]+$/;
  if (base64Pattern.test(content.trim())) {
    return content.length > 100; // Long base64 might be encrypted
  }

  // Check for high entropy (lots of unique characters)
  const uniqueChars = new Set(content).size;
  const entropyRatio = uniqueChars / Math.min(content.length, 256);

  return entropyRatio > 0.7; // High entropy suggests encryption
}

/**
 * Check if content is malformed
 */
function isContentMalformed(content: string, contentType?: string): boolean {
  if (!content) return false;

  // Check JSON
  if (contentType?.includes('json')) {
    try {
      JSON.parse(content);
      return false;
    } catch {
      return true;
    }
  }

  // Check for obviously broken content
  const brokenPatterns = [
    /^\s*[}\]]/,  // Starts with closing bracket
    /[{[]\s*$/,   // Ends with opening bracket
    /['"][^'"]*$/,  // Unclosed string
  ];

  return brokenPatterns.some((p) => p.test(content));
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
  isHoneypotPath: boolean,
  aiSource: string | null,
  envelope: RequestEnvelope
): DefenseDecision {
  // VIP AI visitors get special handling
  if (aiSource && aiSource !== 'unknown_ai' && ctx.threatScore < 30) {
    return {
      action: 'vip_gate',
      reason: `vip_ai_visitor:${aiSource}`,
      confidence: 0.85,
      route: 'vip_gate',
    };
  }

  // Encrypted or malformed content → Shadow Decryption
  if (envelope.isEncrypted || envelope.isMalformed) {
    return {
      action: 'shadow_decrypt',
      reason: envelope.isEncrypted ? 'encrypted_content' : 'malformed_content',
      confidence: 0.7,
      route: 'quarantine',
    };
  }

  // Verified bots always pass
  if (ctx.verifiedBot || isKnownGoodBot(ctx.userAgent)) {
    return {
      action: 'allow',
      reason: 'verified_bot',
      confidence: 0.95,
      route: 'knowledge_realm',
    };
  }

  // Known scanner tools
  if (detectScanner(ctx.userAgent)) {
    return {
      action: isHoneypotPath ? 'engage' : 'challenge',
      reason: 'scanner_detected',
      confidence: 0.9,
      route: 'adversary_lab',
    };
  }

  // Critical threat score - block
  if (ctx.threatScore >= 80) {
    return {
      action: 'block',
      reason: 'critical_threat_score',
      confidence: 0.95,
      route: 'drop',
    };
  }

  // High threat score - challenge or redirect to honeypot
  if (ctx.threatScore >= 50) {
    return {
      action: isHoneypotPath ? 'engage' : 'challenge',
      reason: 'high_threat_score',
      confidence: 0.85,
      route: 'adversary_lab',
    };
  }

  // Very low bot score (likely bot) + honeypot path = engage
  if (ctx.botScore < 30 && isHoneypotPath) {
    return {
      action: 'engage',
      reason: 'suspicious_bot_honeypot_access',
      confidence: 0.8,
      route: 'adversary_lab',
    };
  }

  // Low bot score - challenge
  if (ctx.botScore < 30) {
    return {
      action: 'challenge',
      reason: 'low_bot_score',
      confidence: 0.7,
      route: 'quarantine',
    };
  }

  // Honeypot path access by uncertain visitor
  if (isHoneypotPath && ctx.botScore < 60) {
    return {
      action: 'honeypot',
      reason: 'honeypot_path_access',
      confidence: 0.6,
      route: 'adversary_lab',
    };
  }

  // Unknown AI - route to knowledge realm but monitor
  if (aiSource === 'unknown_ai') {
    return {
      action: 'allow',
      reason: 'unknown_ai_visitor',
      confidence: 0.6,
      route: 'knowledge_realm',
    };
  }

  // Medium threat - allow but monitor
  if (ctx.threatScore >= 20 || ctx.botScore < 50) {
    return {
      action: 'allow',
      reason: 'monitoring',
      confidence: 0.5,
      route: 'quarantine',
    };
  }

  // Default - allow
  return {
    action: 'allow',
    reason: 'no_threat_indicators',
    confidence: 0.9,
    route: 'knowledge_realm',
  };
}

/**
 * Send telemetry to Spatium API (non-blocking)
 */
async function sendToSpatiumAPI(
  env: WorkerEnv,
  envelope: RequestEnvelope,
  decision: DefenseDecision
): Promise<void> {
  const apiUrl = env.SPATIUM_API_URL;
  const apiSecret = env.SPATIUM_API_SECRET;

  if (!apiUrl) {
    return; // API not configured
  }

  try {
    await fetch(`${apiUrl}/defense/envelope`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(apiSecret && { 'X-API-Secret': apiSecret }),
      },
      body: JSON.stringify({
        envelope,
        decision: decision.action,
        decisionReason: decision.reason,
        decisionConfidence: decision.confidence,
        decisionRoute: decision.route,
      }),
    });
  } catch (error) {
    // Non-blocking - log and continue
    console.error('Failed to send to Spatium API:', error);
  }
}
