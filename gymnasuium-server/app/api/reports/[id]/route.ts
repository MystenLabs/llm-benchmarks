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
    
    // Updated path to use public/test_outputs instead of looking one level up
    const outputsDir = path.resolve(process.cwd(), 'public/test_outputs');
    logger.info(`Outputs directory: ${outputsDir}`);
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
      let modifiedContent = fileContent;
      
      if (filePath.endsWith('.html') && filePath.includes('error_chart')) {
        contentType = 'text/html';
        
        // Inject an explanatory section for error chart HTML files
        const explanationHtml = `
        <div style="width: 95%; margin: 20px auto; padding: 15px; background-color: ${filePath.includes('_dark') ? '#1e293b' : '#f8fafc'}; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); color: ${filePath.includes('_dark') ? '#e2e8f0' : '#334155'}; font-family: Arial, sans-serif;">
          <h2 style="margin-top: 0; color: ${filePath.includes('_dark') ? '#3b82f6' : '#1e40af'}; font-size: 1.5rem;">Understanding This Error Chart</h2>
          <p style="line-height: 1.6;">
            This visualization tracks how AI models learn Move semantics by showing compiler error evolution across debugging iterations. Each iteration represents an LLM debugging cycle where the model attempts to fix errors from previous compiler feedback.
          </p>
          <p style="line-height: 1.6;">
            We're tracking more than just "does it compile?". These charts reveal how well models grasp Move's unique concepts like resource ownership, abilities, and type constraints—patterns that challenge both AI and human developers.
          </p>
          <div style="display: flex; flex-wrap: wrap; gap: 15px; margin: 15px 0;">
            <div style="flex: 1; min-width: 280px; background-color: ${filePath.includes('_dark') ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.05)'}; padding: 12px; border-radius: 6px; border-left: 3px solid ${filePath.includes('_dark') ? '#3b82f6' : '#1e40af'};">
              <h3 style="margin-top: 0; margin-bottom: 8px; font-size: 1.1rem; color: ${filePath.includes('_dark') ? '#60a5fa' : '#1e40af'};">Chart Elements</h3>
              <ul style="padding-left: 20px; margin: 0;">
                <li style="margin-bottom: 6px;">The <strong>stacked bars</strong> show different error types per iteration</li>
                <li style="margin-bottom: 6px;">The <strong>red trend line</strong> tracks total error count</li>
                <li style="margin-bottom: 6px;">The <strong>percentage annotations</strong> show improvement or regression between iterations</li>
                <li style="margin-bottom: 6px;"><strong>Hover</strong> over any bar segment to see detailed error information</li>
                <li style="margin-bottom: 0;"><strong>Star icons</strong> indicate successful compilation iterations</li>
              </ul>
            </div>
            <div style="flex: 1; min-width: 280px; background-color: ${filePath.includes('_dark') ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.05)'}; padding: 12px; border-radius: 6px; border-left: 3px solid ${filePath.includes('_dark') ? '#3b82f6' : '#1e40af'};">
              <h3 style="margin-top: 0; margin-bottom: 8px; font-size: 1.1rem; color: ${filePath.includes('_dark') ? '#60a5fa' : '#1e40af'};">Common Move Errors</h3>
              <ul style="padding-left: 20px; margin: 0;">
                <li style="margin-bottom: 6px;"><strong>Ability constraint</strong> errors (E05001): Incorrect use of copy, drop, key, store</li>
                <li style="margin-bottom: 6px;"><strong>Unbound module</strong> errors: Solidity-influenced imports or outdated patterns</li>
                <li style="margin-bottom: 6px;"><strong>Invalid object</strong> declarations: Missing UID or incorrect structure</li>
                <li style="margin-bottom: 6px;"><strong>Unexpected name</strong> errors: Using incorrect module references</li>
                <li style="margin-bottom: 0;"><strong>Invalid entry function</strong> signatures: Incorrect return types</li>
              </ul>
            </div>
          </div>
          <p style="line-height: 1.6;">
            Toggle between iterations using the tabs above to view each version of the contract code. First iterations often contain Solidity-influenced patterns, while later iterations reveal how (and if) the model correctly adapts to Move's unique semantics.
          </p>
          <p style="line-height: 1.6; font-style: italic; opacity: 0.8;">
            This data helps us identify where to improve Move documentation, track AI progress in understanding Move, develop better prompting strategies, and benchmark different models.
          </p>
        </div>`;
        
        // Insert the explanation after the container div opening
        modifiedContent = modifiedContent.replace(
          '<div class="container">',
          '<div class="container">' + explanationHtml
        );
      } else if (filePath.endsWith('.html')) {
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
      return new NextResponse(modifiedContent, {
        headers: {
          'Content-Type': contentType,
          'Content-Length': Buffer.byteLength(modifiedContent).toString(),
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