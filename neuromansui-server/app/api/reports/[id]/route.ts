import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs-extra';
import path from 'path';
import { handleApiError, throwApiError, ErrorType } from '@/app/utils/errorHandler';
import { logger } from '@/app/utils/logger';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<NextResponse> {
  try {
    // Await the asynchronous params
    const { id } = await params;
    
    // Get the file parameter from the URL
    const searchParams = new URL(request.url).searchParams;
    const filename = searchParams.get('file');
    const requestPath = `${request.nextUrl.pathname}${request.nextUrl.search}`;
    
    logger.info(`Processing report file request`, { id, filename });
    
    if (!filename) {
      throwApiError(
        ErrorType.INVALID_REQUEST,
        'File parameter is required',
        null,
        requestPath
      );
    }
    
    // Path to the outputs directory - relative to project root
    const outputsDir = path.resolve(process.cwd(), '../test_outputs');
    const filePath = path.join(outputsDir, filename);
    
    // Basic security check to prevent path traversal
    const normalizedFilePath = path.normalize(filePath);
    if (!normalizedFilePath.startsWith(outputsDir)) {
      throwApiError(
        ErrorType.FORBIDDEN,
        'Invalid file path - path traversal detected',
        { providedPath: filename },
        requestPath
      );
    }
    
    // Check if the file exists
    if (!await fs.pathExists(filePath)) {
      throwApiError(
        ErrorType.NOT_FOUND,
        `File not found: ${filename}`,
        null,
        requestPath
      );
    }
    
    // Read the file
    try {
      const fileContent = await fs.readFile(filePath, 'utf-8');
      const fileStats = await fs.stat(filePath);
      
      // Determine content type based on file extension
      let contentType = 'text/plain';
      if (filePath.endsWith('.html')) {
        contentType = 'text/html';
      } else if (filePath.endsWith('.json')) {
        contentType = 'application/json';
      } else if (filePath.endsWith('.jsonl')) {
        contentType = 'application/jsonl';
      } else if (filePath.endsWith('.move')) {
        contentType = 'text/plain';
      }
      
      logger.info(`Successfully served file: ${filename}`, {
        size: fileStats.size,
        type: contentType
      });
      
      // Create a response with appropriate headers
      return new NextResponse(fileContent, {
        headers: {
          'Content-Type': contentType,
          'Content-Length': fileStats.size.toString(),
          'Cache-Control': 'public, max-age=3600', // Cache for 1 hour
        },
      });
    } catch (readError) {
      throwApiError(
        ErrorType.INTERNAL_ERROR,
        `Error reading file: ${readError instanceof Error ? readError.message : 'Unknown error'}`,
        null,
        requestPath
      );
    }
  } catch (error) {
    return handleApiError(error, request.nextUrl.pathname);
  }
}