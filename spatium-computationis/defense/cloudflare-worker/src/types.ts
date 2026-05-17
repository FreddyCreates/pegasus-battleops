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
  action: 'allow' | 'challenge' | 'block' | 'honeypot' | 'engage';
  reason: string;
  confidence: number;
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
}

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
