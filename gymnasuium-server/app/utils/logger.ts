/**
 * Standardized logger for the application
 */

// Log levels for different types of messages
export enum LogLevel {
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARN = 'WARN',
  ERROR = 'ERROR',
  FATAL = 'FATAL',
}

// Object to store log settings
const logSettings = {
  // Default level is INFO in production, DEBUG in development
  minLevel: process.env.NODE_ENV === 'production' 
    ? LogLevel.INFO 
    : LogLevel.DEBUG,
  // Whether to include timestamps in logs
  timestamps: true,
  // Whether to colorize logs in development
  colorize: process.env.NODE_ENV !== 'production',
};

// Order of log levels for filtering
const logLevelOrder: Record<LogLevel, number> = {
  [LogLevel.DEBUG]: 0,
  [LogLevel.INFO]: 1,
  [LogLevel.WARN]: 2,
  [LogLevel.ERROR]: 3,
  [LogLevel.FATAL]: 4,
};

// Colors for different log levels
const colors: Record<LogLevel, string> = {
  [LogLevel.DEBUG]: '\x1b[36m', // Cyan
  [LogLevel.INFO]: '\x1b[32m',  // Green
  [LogLevel.WARN]: '\x1b[33m',  // Yellow
  [LogLevel.ERROR]: '\x1b[31m', // Red
  [LogLevel.FATAL]: '\x1b[35m', // Magenta
};

const resetColor = '\x1b[0m';

/**
 * Format the log message with timestamp, level, and any metadata
 */
function formatLogMessage(level: LogLevel, message: string, meta?: any): string {
  let formattedMessage = '';
  
  // Add timestamp if enabled
  if (logSettings.timestamps) {
    const timestamp = new Date().toISOString();
    formattedMessage += `[${timestamp}] `;
  }
  
  // Add colored log level if enabled
  if (logSettings.colorize) {
    formattedMessage += `${colors[level]}[${level}]${resetColor} `;
  } else {
    formattedMessage += `[${level}] `;
  }
  
  // Add the actual message
  formattedMessage += message;
  
  // Add metadata if present
  if (meta) {
    if (typeof meta === 'object') {
      try {
        formattedMessage += ` | ${JSON.stringify(meta)}`;
      } catch (e) {
        formattedMessage += ` | [Object cannot be stringified]`;
      }
    } else {
      formattedMessage += ` | ${meta}`;
    }
  }
  
  return formattedMessage;
}

/**
 * The main logger function that handles filtering by log level
 */
function log(level: LogLevel, message: string, meta?: any): void {
  // Skip logs below the minimum level
  if (logLevelOrder[level] < logLevelOrder[logSettings.minLevel]) {
    return;
  }
  
  const formattedMessage = formatLogMessage(level, message, meta);
  
  // Use appropriate console method based on level
  switch (level) {
    case LogLevel.DEBUG:
      console.debug(formattedMessage);
      break;
    case LogLevel.INFO:
      console.info(formattedMessage);
      break;
    case LogLevel.WARN:
      console.warn(formattedMessage);
      break;
    case LogLevel.ERROR:
    case LogLevel.FATAL:
      console.error(formattedMessage);
      // Optionally send to error monitoring service here
      break;
  }
}

// Create specific logging methods for each level
export const logger = {
  debug: (message: string, meta?: any) => log(LogLevel.DEBUG, message, meta),
  info: (message: string, meta?: any) => log(LogLevel.INFO, message, meta),
  warn: (message: string, meta?: any) => log(LogLevel.WARN, message, meta),
  error: (message: string, meta?: any) => log(LogLevel.ERROR, message, meta),
  fatal: (message: string, meta?: any) => log(LogLevel.FATAL, message, meta),
  
  // Method to configure logger settings
  configure: (options: {
    minLevel?: LogLevel;
    timestamps?: boolean;
    colorize?: boolean;
  }) => {
    if (options.minLevel) logSettings.minLevel = options.minLevel;
    if (options.timestamps !== undefined) logSettings.timestamps = options.timestamps;
    if (options.colorize !== undefined) logSettings.colorize = options.colorize;
  }
}; 