/**
 * Type definitions for the Defense Worker
 */

export interface WorkerEnv {
  // Environment variables
  ENVIRONMENT: string;
  SPATIUM_API_URL?: string;
  SPATIUM_API_SECRET?: string;
  WEBHOOK_SECRET?: string;

  // KV Namespace bindings
  THREAT_CACHE?: KVNamespace;

  // Analytics Engine binding
  THREAT_ANALYTICS?: AnalyticsEngineDataset;
}

export interface ThreatContext {
  rayId: string;
  clientIP: string;
  path: string;
  method: string;
  userAgent: string | null;
  botScore: number;
  verifiedBot: boolean;
  threatScore: number;
  country: string;
  asn: number;
  asnOrg: string;
  ja3Hash: string | null;
  ja4: string | null;
  timestamp: string;
}

export interface DefenseDecision {
  action: 'allow' | 'challenge' | 'block' | 'honeypot' | 'engage' | 'vip_gate' | 'shadow_decrypt' | 'error_repair';
  reason: string;
  confidence: number;
  route?: 'adversary_lab' | 'knowledge_realm' | 'vip_gate' | 'drop' | 'quarantine' | 'replay';
}

export interface CloudflareRequestCF {
  botManagement?: {
    score: number;
    verifiedBot: boolean;
    staticResource: boolean;
    ja3Hash?: string;
    ja4?: string;
  };
  threatScore?: number;
  country?: string;
  asn?: number;
  asOrganization?: string;
  tlsVersion?: string;
  tlsCipher?: string;
}

/**
 * Request Envelope - Universal container sent to Spatium backend
 */
export interface RequestEnvelope {
  envelopeId: string;
  timestamp: string;
  sourceIp: string;
  sourceFingerprint?: string;
  rawMethod: string;
  rawPath: string;
  rawHeaders: Record<string, string>;
  rawQuery: Record<string, string>;
  rawBody?: string;
  cfRay?: string;
  cfCountry?: string;
  cfAsn?: number;
  cfAsnOrg?: string;
  cfThreatScore?: number;
  cfBotScore?: number;
  cfVerifiedBot: boolean;
  cfTlsVersion?: string;
  cfTlsCipher?: string;
  isEncrypted: boolean;
  isMalformed: boolean;
  hasError: boolean;
  errorType?: string;
  errorCode?: number;
  aiSourceDetected?: string;
}

// Known AI visitor patterns
export const AI_VISITOR_PATTERNS: Record<string, { userAgents: string[]; ipPrefixes: string[] }> = {
  claude: {
    userAgents: ['claude', 'anthropic'],
    ipPrefixes: ['35.'],
  },
  google: {
    userAgents: ['googlebot', 'google', 'apis-google'],
    ipPrefixes: ['66.249.', '64.233.', '72.14.'],
  },
  openai: {
    userAgents: ['openai', 'gpt', 'chatgpt'],
    ipPrefixes: ['20.', '52.'],
  },
  bing: {
    userAgents: ['bingbot', 'msnbot', 'bing'],
    ipPrefixes: ['157.55.', '207.46.', '40.77.'],
  },
  perplexity: {
    userAgents: ['perplexity', 'pplx'],
    ipPrefixes: [],
  },
};

// Honeypot paths that attract attackers
export const HONEYPOT_PATHS = [
  '/.env',
  '/.env.local',
  '/.env.production',
  '/config.php',
  '/wp-config.php',
  '/wp-admin',
  '/wp-login.php',
  '/phpmyadmin',
  '/admin',
  '/administrator',
  '/.git',
  '/.git/config',
  '/.git/HEAD',
  '/backup.sql',
  '/database.sql',
  '/db.sql',
  '/api/admin',
  '/api/debug',
  '/graphql',
  '/phpinfo.php',
  '/server-status',
] as const;

// Known good bot user agents (partial matches)
export const VERIFIED_BOT_AGENTS = [
  'googlebot',
  'bingbot',
  'slurp',
  'duckduckbot',
  'baiduspider',
  'yandexbot',
  'facebot',
  'ia_archiver',
] as const;

// Known bad tool signatures (partial matches)
export const SCANNER_SIGNATURES = [
  'sqlmap',
  'nikto',
  'nmap',
  'masscan',
  'wpscan',
  'burp',
  'nuclei',
  'zgrab',
  'dirbuster',
  'gobuster',
  'ffuf',
  'hydra',
] as const;
