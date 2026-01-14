'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { CheckCircle, XCircle } from 'lucide-react';

export default function VerifyPage() {
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [error, setError] = useState('');
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const verifyToken = async () => {
      try {
        // Check if Supabase is configured
        if (!supabase) {
          throw new Error('Authentication not configured');
        }

        // First, check URL hash for tokens (Supabase magic link puts them there)
        // The Supabase client should automatically detect hash params and exchange them
        // We need to give it a moment to process

        // Check for hash params (access_token, refresh_token, etc.)
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        const accessToken = hashParams.get('access_token');
        const refreshToken = hashParams.get('refresh_token');

        if (accessToken) {
          // Supabase should have automatically set the session from hash params
          // Wait a moment for it to process
          await new Promise(resolve => setTimeout(resolve, 500));
        }

        // Now check for session
        const { data, error: sessionError } = await supabase.auth.getSession();

        if (sessionError) {
          throw sessionError;
        }

        if (data.session) {
          setStatus('success');
          // Redirect to home page after short delay
          setTimeout(() => {
            router.push('/');
          }, 1500);
          return;
        }

        // If no session yet, try to exchange tokens from query params
        const tokenHash = searchParams.get('token_hash');
        const type = searchParams.get('type');

        if (tokenHash && type) {
          const { error: verifyError } = await supabase.auth.verifyOtp({
            token_hash: tokenHash,
            type: type as 'email' | 'magiclink',
          });

          if (verifyError) {
            throw verifyError;
          }

          setStatus('success');
          setTimeout(() => {
            router.push('/');
          }, 1500);
          return;
        }

        // Try magiclink type as well
        if (tokenHash) {
          const { error: verifyError } = await supabase.auth.verifyOtp({
            token_hash: tokenHash,
            type: 'magiclink',
          });

          if (verifyError) {
            throw verifyError;
          }

          setStatus('success');
          setTimeout(() => {
            router.push('/');
          }, 1500);
          return;
        }

        // If we still don't have a session, something went wrong
        throw new Error('No valid session or token found. Please try signing in again.');
      } catch (err) {
        console.error('Verification error:', err);
        setStatus('error');
        setError(err instanceof Error ? err.message : 'Verification failed');
      }
    };

    verifyToken();
  }, [router, searchParams]);

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="spinner mx-auto mb-4" />
          <h1 className="text-xl font-semibold text-gray-900 mb-2">Verifying...</h1>
          <p className="text-gray-600">Please wait while we sign you in.</p>
        </div>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-xl font-semibold text-gray-900 mb-2">You&apos;re in!</h1>
          <p className="text-gray-600">Redirecting to your portal...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center max-w-md px-4">
        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <XCircle className="w-8 h-8 text-red-600" />
        </div>
        <h1 className="text-xl font-semibold text-gray-900 mb-2">Verification Failed</h1>
        <p className="text-gray-600 mb-6">{error || 'The link may have expired or already been used.'}</p>
        <button
          onClick={() => router.push('/auth')}
          className="btn btn-primary"
        >
          Request New Link
        </button>
      </div>
    </div>
  );
}
