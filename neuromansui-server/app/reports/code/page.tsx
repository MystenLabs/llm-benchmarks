'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import hljs from 'highlight.js/lib/core';
import rust from 'highlight.js/lib/languages/rust';
import 'highlight.js/styles/github-dark.css';

export default function CodeViewer() {
  const searchParams = useSearchParams();
  const id = searchParams.get('id');
  const file = searchParams.get('file');
  
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id || !file) {
      setError('Missing required parameters');
      setLoading(false);
      return;
    }

    async function fetchCode() {
      try {
        const response = await fetch(`/api/reports/${id}?file=${encodeURIComponent(file || '')}`);
        if (!response.ok) {
          throw new Error(`Error fetching code: ${response.statusText}`);
        }
        const data = await response.text();
        setCode(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch code');
      } finally {
        setLoading(false);
      }
    }

    fetchCode();
  }, [id, file]);

  // Load and initialize syntax highlighting
  useEffect(() => {
    if (!loading && !error && code) {
      // Register the Rust language for Move syntax highlighting
      hljs.registerLanguage('rust', rust);
      hljs.highlightAll();
      
      // Add line numbers
      const codeBlocks = document.querySelectorAll('pre code');
      codeBlocks.forEach(block => {
        const lines = block.innerHTML.split('\n');
        const numberedLines = lines.map((line, i) => 
          `<span class="line-number">${i + 1}</span>${line}`
        ).join('\n');
        block.innerHTML = numberedLines;
      });
    }
  }, [loading, error, code]);

  return (
    <div className="flex min-h-screen flex-col items-center p-6 md:p-12">
      <div className="w-full max-w-6xl">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl font-bold">Contract Code</h1>
          <Link href="/" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
            Back to Dashboard
          </Link>
        </div>

        {loading ? (
          <div className="flex items-center justify-center w-full py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
            <span className="ml-3">Loading code...</span>
          </div>
        ) : error ? (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
            <p className="font-bold">Error</p>
            <p>{error}</p>
          </div>
        ) : (
          <div className="bg-white shadow-md rounded-lg p-6 overflow-hidden">
            <h2 className="text-xl font-semibold mb-4">{file}</h2>
            <div className="relative overflow-auto">
              <pre className="rounded-md p-4 bg-gray-800 text-white overflow-x-auto">
                <code className="language-rust">{code}</code>
              </pre>
            </div>
          </div>
        )}
      </div>
      
      <style jsx global>{`
        .line-number {
          display: inline-block;
          width: 3em;
          text-align: right;
          padding-right: 1em;
          user-select: none;
          color: #666;
          border-right: 1px solid #555;
          margin-right: 0.5em;
        }
        
        pre {
          tab-size: 2;
        }
      `}</style>
    </div>
  );
} 