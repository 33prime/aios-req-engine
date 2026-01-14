'use client';

import { useState } from 'react';
import { Mail, ArrowRight, CheckCircle } from 'lucide-react';
import api from '@/lib/api';

export default function AuthPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await api.sendMagicLink(email, `${window.location.origin}/auth/verify`);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send magic link');
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <div className="min-h-screen flex">
        {/* Left side - Gradient */}
        <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary to-teal-600 p-12 flex-col justify-between">
          <div>
            <h1 className="text-white text-2xl font-bold">ReadyToGo.ai</h1>
          </div>
          <div className="text-white">
            <h2 className="text-3xl font-bold mb-4">Your project, simplified.</h2>
            <p className="text-white/80 text-lg">
              Access your project details, share information, and collaborate seamlessly.
            </p>
          </div>
          <div className="text-white/60 text-sm">
            Secure access via magic link
          </div>
        </div>

        {/* Right side - Check email message */}
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="w-full max-w-md text-center">
            <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="w-8 h-8 text-primary" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Check your email</h1>
            <p className="text-gray-600 mb-6">
              We sent a magic link to <strong>{email}</strong>
            </p>
            <p className="text-sm text-gray-500 mb-8">
              Click the link in your email to sign in. The link will expire in 24 hours.
            </p>
            <button
              onClick={() => setSent(false)}
              className="text-primary hover:underline text-sm"
            >
              Use a different email
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      {/* Left side - Gradient */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary to-teal-600 p-12 flex-col justify-between">
        <div>
          <h1 className="text-white text-2xl font-bold">ReadyToGo.ai</h1>
        </div>
        <div className="text-white">
          <h2 className="text-3xl font-bold mb-4">Your project, simplified.</h2>
          <p className="text-white/80 text-lg">
            Access your project details, share information, and collaborate seamlessly.
          </p>
        </div>
        <div className="text-white/60 text-sm">
          Secure access via magic link
        </div>
      </div>

      {/* Right side - Login form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden text-center mb-8">
            <h1 className="text-2xl font-bold text-primary">ReadyToGo.ai</h1>
          </div>

          <h1 className="text-2xl font-bold text-gray-900 mb-2">Welcome back</h1>
          <p className="text-gray-600 mb-8">
            Enter your email to access your project portal.
          </p>

          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                Email address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  required
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>
            </div>

            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !email}
              className="w-full btn btn-primary py-3 justify-center disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="spinner" />
              ) : (
                <>
                  Continue with Email
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <p className="mt-8 text-center text-sm text-gray-500">
            Don&apos;t have access? Contact your consultant.
          </p>
        </div>
      </div>
    </div>
  );
}
