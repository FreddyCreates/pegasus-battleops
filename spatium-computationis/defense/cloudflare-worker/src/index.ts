/**
 * Spatium Computationis Defense Worker
 * ⛨ Cloudflare Edge Security Integration
 *
 * This worker intercepts traffic at Cloudflare's edge to:
 * 1. Analyze bot behavior using Cloudflare's bot management
 * 2. Route suspicious traffic to honeypot endpoints
 * 3. Send threat intelligence to the Spatium API
 * 4. Apply adaptive defense rules in real-time
 */

import { handleRequest } from './handlers';
import { ThreatContext, WorkerEnv } from './types';

export default {
  async fetch(
    request: Request,
    env: WorkerEnv,
    ctx: ExecutionContext
  ): Promise<Response> {
    return handleRequest(request, env, ctx);
  },

  // Optional: Scheduled handler for periodic tasks
  async scheduled(
    controller: ScheduledController,
    env: WorkerEnv,
    ctx: ExecutionContext
  ): Promise<void> {
    // Periodic cleanup, metrics aggregation, etc.
    console.log('Scheduled task running at:', new Date().toISOString());
  },
};
