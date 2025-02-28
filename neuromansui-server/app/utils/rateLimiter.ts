/**
 * A simple in-memory rate limiter for API endpoints
 */

import { NextRequest, NextResponse } from 'next/server';
import { logger } from './logger';
import { throwApiError, ErrorType } from './errorHandler';

// Configuration for different routes (requests per minute)
interface RateLimitConfig {
  // Default limit for all API routes
  default: number;
  // Specific limits for different route patterns
  routes: {
    [key: string]: number;
  }
}

// Default configuration
const config: RateLimitConfig = {
  default: 60, // 60 requests per minute by default
  routes: {
    '/api/reports': 100, // 100 requests per minute for reports listing
    '/api/reports/.*': 150, // 150 requests per minute for individual reports
  }
};

// Store for tracking request counts
interface RequestCount {
  count: number;
  resetTime: number;
}

// In-memory store for rate limiting
// In a production environment, use Redis or a similar service
const requestStore = new Map<string, RequestCount>();

// Clean up expired entries periodically (every minute)
setInterval(() => {
  const now = Date.now();
  for (const [key, value] of requestStore.entries()) {
    if (value.resetTime <= now) {
      requestStore.delete(key);
    }
  }
}, 60 * 1000);

/**
 * Get the rate limit for a specific path
 */
function getRateLimit(path: string): number {
  // Check for specific route matches first
  for (const [routePattern, limit] of Object.entries(config.routes)) {
    if (new RegExp(`^${routePattern}$`).test(path)) {
      return limit;
    }
  }
  
  // Fall back to default limit
  return config.default;
}

/**
 * Create a rate limiting key based on IP and path
 */
function getRateLimitKey(ip: string, path: string): string {
  // Extract the base path (first two segments) for limiting
  const pathSegments = path.split('/').filter(Boolean);
  const basePath = pathSegments.length > 1 
    ? `/${pathSegments[0]}/${pathSegments[1]}`
    : path;
    
  return `${ip}:${basePath}`;
}

/**
 * Get client IP address from a request
 */
function getClientIp(request: NextRequest): string {
  // Try the x-forwarded-for header first (common for proxies)
  const forwardedFor = request.headers.get('x-forwarded-for');
  if (forwardedFor) {
    // Extract the first IP if there are multiple
    return forwardedFor.split(',')[0].trim();
  }
  
  // Fall back to other headers that might contain client IP
  const realIp = request.headers.get('x-real-ip');
  if (realIp) {
    return realIp;
  }
  
  // Default to 'unknown' if we can't determine the IP
  return 'unknown';
}

/**
 * Rate limiter middleware function
 */
export function rateLimiter(request: NextRequest, routePath: string): void {
  // Get client IP
  const ip = getClientIp(request);
  
  // Get the rate limit for this path
  const rateLimit = getRateLimit(routePath);
  
  // Create the rate limiting key
  const key = getRateLimitKey(ip, routePath);
  
  // Get the current time
  const now = Date.now();
  
  // Get or create the request count record
  let record = requestStore.get(key);
  if (!record || record.resetTime <= now) {
    // Create a new record with reset time 1 minute from now
    record = { count: 0, resetTime: now + 60 * 1000 };
  }
  
  // Increment the request count
  record.count++;
  
  // Store the updated record
  requestStore.set(key, record);
  
  // Calculate remaining requests
  const remaining = Math.max(0, rateLimit - record.count);
  
  // Check if rate limit exceeded
  if (record.count > rateLimit) {
    logger.warn(`Rate limit exceeded for ${ip} on ${routePath}`, {
      count: record.count,
      limit: rateLimit,
      ip
    });
    
    // Throw rate limit error
    throwApiError(
      ErrorType.FORBIDDEN,
      'Rate limit exceeded',
      {
        limit: rateLimit,
        remaining: 0,
        resetAt: new Date(record.resetTime).toISOString()
      },
      routePath
    );
  }
  
  // Log high usage if approaching limit
  if (remaining <= Math.ceil(rateLimit * 0.1)) {
    logger.warn(`Client approaching rate limit: ${ip} on ${routePath}`, {
      remaining,
      limit: rateLimit,
      ip
    });
  }
}

/**
 * Apply rate limiting to a specific API endpoint
 */
export async function applyRateLimit(
  request: NextRequest,
  handler: (request: NextRequest) => Promise<NextResponse>
): Promise<NextResponse> {
  try {
    // Apply rate limiting
    rateLimiter(request, request.nextUrl.pathname);
    
    // Continue to the handler
    return await handler(request);
  } catch (error) {
    // Handle rate limiting errors
    if (error instanceof Error) {
      return NextResponse.json(
        {
          error: 'Rate limit exceeded',
          message: error.message,
          path: request.nextUrl.pathname,
          timestamp: new Date().toISOString()
        },
        { status: 429 }
      );
    }
    throw error;
  }
} 