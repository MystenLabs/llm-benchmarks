'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';

// Create a client component that uses useSearchParams
function ReportContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
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
    
    // Use Next.js router for client-side navigation instead of window.location
    router.push(`/api/reports/${id}?file=${encodeURIComponent(file)}`);
  }, [id, file, router]);
  
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

// Wrap the component that uses useSearchParams in a Suspense boundary
export default function ViewReport() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen flex-col items-center justify-center p-6 md:p-12">
        <div className="flex flex-col items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          <span className="mt-4">Loading report...</span>
        </div>
      </div>
    }>
      <ReportContent />
    </Suspense>
  );
} 