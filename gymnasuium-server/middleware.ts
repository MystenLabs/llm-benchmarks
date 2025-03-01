import { NextRequest, NextResponse } from 'next/server';
import { logger } from './app/utils/logger';

// Log levels for different types of messages
enum LogLevel {
  INFO = 'INFO',
  WARN = 'WARN',
  ERROR = 'ERROR',
}

/**
 * Logger function to standardize log format
 */
function log(level: LogLevel, message: string, meta?: any) {
  const timestamp = new Date().toISOString();
  const metaStr = meta ? ` | ${JSON.stringify(meta)}` : '';
  console.log(`[${timestamp}] [${level}] ${message}${metaStr}`);
}

/**
 * Middleware function for Next.js
 */
export async function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const start = Date.now();

  // Log the incoming request
  logger.info(`Incoming request: ${request.method} ${pathname}${search}`);

  try {
    // Continue to the actual route handler
    const response = NextResponse.next();

    // Log the response time
    const duration = Date.now() - start;
    logger.info(`Request completed in ${duration}ms: ${request.method} ${pathname}`, {
      status: response.status,
      duration,
    });

    return response;
  } catch (error) {
    // Log any unexpected errors
    logger.error(`Error processing request: ${request.method} ${pathname}`, {
      error: error instanceof Error ? error.message : 'Unknown error',
      stack: error instanceof Error ? error.stack : undefined,
    });

    // Create a standardized error response
    return new NextResponse(
      JSON.stringify({
        error: 'Internal Server Error',
        message: 'An unexpected error occurred',
        path: pathname,
        timestamp: new Date().toISOString(),
      }),
      {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
  }
}

// Configure which routes the middleware applies to
export const config = {
  matcher: [
    // Apply to all API routes
    '/api/:path*',
    // Apply to the report viewer routes
    '/reports/:path*',
  ],
}; 