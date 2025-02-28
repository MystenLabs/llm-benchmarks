/**
 * Error handling utilities for API routes
 */

import { NextResponse } from 'next/server';
import { logger } from './logger';

// Error types for better categorization
export enum ErrorType {
  NOT_FOUND = 'NOT_FOUND',
  INVALID_REQUEST = 'INVALID_REQUEST',
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',
  INTERNAL_ERROR = 'INTERNAL_ERROR',
}

// Map error types to HTTP status codes
const statusCodes: Record<ErrorType, number> = {
  [ErrorType.NOT_FOUND]: 404,
  [ErrorType.INVALID_REQUEST]: 400,
  [ErrorType.UNAUTHORIZED]: 401,
  [ErrorType.FORBIDDEN]: 403,
  [ErrorType.INTERNAL_ERROR]: 500,
};

// Error response structure for API
interface ErrorResponse {
  error: string;
  message: string;
  timestamp: string;
  path?: string;
  details?: any;
}

/**
 * Class for API errors with proper status codes and standardized format
 */
export class ApiError extends Error {
  type: ErrorType;
  details?: any;
  path?: string;

  constructor(type: ErrorType, message: string, details?: any, path?: string) {
    super(message);
    this.name = 'ApiError';
    this.type = type;
    this.details = details;
    this.path = path;
  }
}

/**
 * Centralized error handling function for all API routes
 */
export function handleApiError(error: unknown, path?: string): NextResponse {
  // Default error response for unknown errors
  let errorResponse: ErrorResponse = {
    error: 'Internal Server Error',
    message: 'An unexpected error occurred',
    timestamp: new Date().toISOString(),
    path,
  };

  let status = 500;

  // Handle our custom ApiError with specific types
  if (error instanceof ApiError) {
    status = statusCodes[error.type];
    errorResponse = {
      error: error.type,
      message: error.message,
      timestamp: new Date().toISOString(),
      path: error.path || path,
      details: error.details,
    };
    
    // Log the API error with the appropriate level based on status code
    if (status >= 500) {
      logger.error(`API Error (${error.type}): ${error.message}`, { 
        path: error.path || path,
        details: error.details
      });
    } else if (status >= 400) {
      logger.warn(`API Error (${error.type}): ${error.message}`, { 
        path: error.path || path
      });
    }
  } 
  // Handle standard JavaScript errors
  else if (error instanceof Error) {
    errorResponse.message = error.message;
    
    // Add stack trace in development environment
    if (process.env.NODE_ENV === 'development') {
      errorResponse.details = {
        stack: error.stack,
      };
    }
    
    // Log the error
    logger.error(`Unhandled Error: ${error.message}`, {
      path,
      stack: error.stack
    });
  }
  // Handle unknown errors
  else {
    logger.error('Unknown Error Type', {
      path,
      error
    });
  }

  return NextResponse.json(errorResponse, { status });
}

/**
 * Helper function to create a specific API error and throw it
 */
export function throwApiError(type: ErrorType, message: string, details?: any, path?: string): never {
  throw new ApiError(type, message, details, path);
} 