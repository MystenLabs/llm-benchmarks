import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs-extra';
import path from 'path';
import { handleApiError, throwApiError, ErrorType } from '@/app/utils/errorHandler';
import { applyRateLimit } from '@/app/utils/rateLimiter';
import { logger } from '@/app/utils/logger';

interface ReportFile {
  name: string;
  path: string;
  type: 'chart' | 'json' | 'move' | 'other';
  timestamp: string;
  size: number;
  createdAt: Date;
}

function getFileType(filename: string): 'chart' | 'json' | 'move' | 'other' {
  if (filename.includes('error_chart')) {
    return 'chart';
  } else if (filename.endsWith('.json') || filename.endsWith('.jsonl')) {
    return 'json';
  } else if (filename.endsWith('.move')) {
    return 'move';
  } else {
    return 'other';
  }
}

function parseTimestamp(filename: string): string {
  // Extract timestamp format like 20250226_214758
  const match = filename.match(/\d{8}_\d{6}/);
  if (match) {
    const timestamp = match[0];
    const year = timestamp.substring(0, 4);
    const month = timestamp.substring(4, 6);
    const day = timestamp.substring(6, 8);
    const hour = timestamp.substring(9, 11);
    const minute = timestamp.substring(11, 13);
    const second = timestamp.substring(13, 15);
    
    return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
  }
  return '';
}

// Handler function
async function handler(request: NextRequest) {
  try {
    const requestPath = new URL(request.url).pathname;
    logger.info(`Processing reports list request`);
    
    // Updated path to use public/test_outputs instead of looking one level up
    const outputsDir = path.resolve(process.cwd(), 'public/test_outputs');
    logger.info(`Outputs directory: ${outputsDir}`);
    
    // Check if the directory exists
    if (!await fs.pathExists(outputsDir)) {
      throwApiError(
        ErrorType.NOT_FOUND,
        'Reports directory not found',
        { directory: outputsDir },
        requestPath
      );
    }
    
    // Read all files in the directory
    const files = await fs.readdir(outputsDir);
    logger.debug(`Found ${files.length} files in the reports directory`);
    
    // Get file details and filter to only include HTML reports and related files
    const reports: ReportFile[] = [];
    
    for (const file of files) {
      // Skip directories for now
      const filePath = path.join(outputsDir, file);
      
      try {
        const stats = await fs.stat(filePath);
        
        if (stats.isFile()) {
          reports.push({
            name: file,
            path: filePath,
            type: getFileType(file),
            timestamp: parseTimestamp(file),
            size: stats.size,
            createdAt: stats.birthtime
          });
        }
      } catch (statError) {
        // Log the error but continue processing other files
        logger.warn(`Error reading file stats for ${file}:`, statError);
      }
    }
    
    // Group files by their base name (without extension)
    const groupedReports: Record<string, ReportFile[]> = {};
    
    reports.forEach(report => {
      // Extract the timestamp from the filename (format: YYYYMMDD_HHMMSS)
      const timestampMatch = report.name.match(/(\d{8}_\d{6})/);
      if (!timestampMatch) {
        // If no timestamp found, use the full filename as the group key
        const baseNameWithoutExt = path.parse(report.name).name;
        if (!groupedReports[baseNameWithoutExt]) {
          groupedReports[baseNameWithoutExt] = [];
        }
        groupedReports[baseNameWithoutExt].push(report);
        return;
      }
      
      const timestamp = timestampMatch[1];
      
      // Find the contract type part (everything before the timestamp)
      const contractTypeMatch = report.name.match(/(.*?)_\d{8}_\d{6}/);
      const contractType = contractTypeMatch ? contractTypeMatch[1] : 'unknown';
      
      // Use a combination of contract type and timestamp as the group key
      const groupKey = `${contractType}_${timestamp}`;
      
      if (!groupedReports[groupKey]) {
        groupedReports[groupKey] = [];
      }
      
      groupedReports[groupKey].push(report);
    });
    
    const reportCount = Object.keys(groupedReports).length;
    logger.info(`Returning ${reportCount} grouped reports`);
    
    return NextResponse.json({ 
      reports: groupedReports,
      timestamp: new Date().toISOString(),
      count: reportCount
    });
    
  } catch (error) {
    return handleApiError(error, new URL(request.url).pathname);
  }
}

// Apply rate limiting to the handler
export const GET = (request: NextRequest) => applyRateLimit(request, handler); 