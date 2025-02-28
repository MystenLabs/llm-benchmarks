'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface ReportFile {
  name: string;
  path: string;
  type: 'chart' | 'json' | 'move' | 'other';
  timestamp: string;
  size: number;
  createdAt: string;
}

interface GroupedReports {
  [key: string]: ReportFile[];
}

export default function Home() {
  const [reports, setReports] = useState<GroupedReports>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchReports() {
      try {
        const response = await fetch('/api/reports');
        if (!response.ok) {
          throw new Error(`Error fetching reports: ${response.statusText}`);
        }
        const data = await response.json();
        setReports(data.reports);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch reports');
      } finally {
        setLoading(false);
      }
    }

    fetchReports();
  }, []);

  // Format file size for display
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <main className="flex min-h-screen flex-col items-center p-6 md:p-12">
      <h1 className="text-4xl font-bold mb-8">Neuromansui Report Server</h1>
      
      {loading ? (
        <div className="flex items-center justify-center w-full py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          <span className="ml-3">Loading reports...</span>
        </div>
      ) : error ? (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded w-full max-w-4xl">
          <p className="font-bold">Error</p>
          <p>{error}</p>
        </div>
      ) : Object.keys(reports).length === 0 ? (
        <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded w-full max-w-4xl">
          <p className="font-bold">No reports found</p>
          <p>No reports have been generated yet. Run neuromansui to generate reports.</p>
        </div>
      ) : (
        <div className="w-full max-w-6xl">
          {Object.entries(reports).map(([reportName, files]) => {
            // Find the HTML chart file if it exists
            const chartFile = files.find(file => file.type === 'chart' && !file.name.includes('dark'));
            const darkChartFile = files.find(file => file.type === 'chart' && file.name.includes('dark'));
            const moveFile = files.find(file => file.type === 'move');
            const jsonFiles = files.filter(file => file.type === 'json');
            
            return (
              <div key={reportName} className="mb-8 bg-white shadow-md rounded-lg p-6">
                <h2 className="text-2xl font-semibold mb-4">{reportName}</h2>
                
                {chartFile && (
                  <div className="mb-4">
                    <h3 className="text-lg font-medium mb-2">Report Chart</h3>
                    <div className="flex flex-col sm:flex-row gap-3">
                      <Link 
                        href={`/reports/view?id=${reportName}&file=${chartFile.name}`}
                        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 inline-flex items-center"
                      >
                        <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3m0 0l3 3m-3-3v9m6-6v9" />
                        </svg>
                        View Light Chart
                      </Link>
                      
                      {darkChartFile && (
                        <Link 
                          href={`/reports/view?id=${reportName}&file=${darkChartFile.name}`}
                          className="px-4 py-2 bg-gray-800 text-white rounded hover:bg-gray-900 inline-flex items-center"
                        >
                          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                          </svg>
                          View Dark Chart
                        </Link>
                      )}
                    </div>
                  </div>
                )}
                
                {moveFile && (
                  <div className="mb-4">
                    <h3 className="text-lg font-medium mb-2">Contract Code</h3>
                    <Link 
                      href={`/reports/code?id=${reportName}&file=${moveFile.name}`}
                      className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 inline-flex items-center"
                    >
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                      </svg>
                      View Code
                    </Link>
                  </div>
                )}
                
                {jsonFiles.length > 0 && (
                  <div>
                    <h3 className="text-lg font-medium mb-2">Raw Data</h3>
                    <div className="flex flex-wrap gap-2">
                      {jsonFiles.map(file => (
                        <Link
                          key={file.name}
                          href={`/api/reports/${reportName}?file=${file.name}`} 
                          className="px-3 py-1 bg-gray-200 text-gray-800 rounded hover:bg-gray-300 text-sm inline-flex items-center"
                          target="_blank"
                        >
                          {file.name.endsWith('.json') ? 'JSON' : 'JSONL'} ({formatFileSize(file.size)})
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
                
                <div className="mt-4 text-sm text-gray-500">
                  Generated: {files[0]?.timestamp || 'Unknown date'}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </main>
  );
}
