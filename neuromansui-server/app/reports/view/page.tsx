'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';

export default function ViewReport() {
  const searchParams = useSearchParams();
  const id = searchParams.get('id');
  const file = searchParams.get('file');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    if (!id || !file) {
      setError('Missing required parameters');
      setLoading(false);
      return;
    }
    
    // Instead of fetching and rendering the HTML content ourselves,
    // we'll redirect to the API endpoint that serves the raw HTML file
    // This ensures all the scripts and resources in the HTML report run correctly
    window.location.href = `/api/reports/${id}?file=${encodeURIComponent(file)}`;
  }, [id, file]);
  
  // This component will only be visible briefly before the redirect occurs
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-6 md:p-12">
      {loading ? (
        <div className="flex flex-col items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          <span className="mt-4">Loading report...</span>
        </div>
      ) : error ? (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded w-full max-w-md">
          <p className="font-bold">Error</p>
          <p>{error}</p>
          <div className="mt-4">
            <Link href="/" className="text-blue-500 hover:underline">
              Go back to dashboard
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  );
} 