'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/auth/AuthProvider';
import api from '@/lib/api';
import { MessageSquare, FileText, Zap, ArrowRight } from 'lucide-react';

export default function WelcomePage() {
  const { user, refreshUser } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const handleGetStarted = async () => {
    setLoading(true);
    try {
      await api.markWelcomeSeen();
      await refreshUser();
      router.push('/');
    } catch (error) {
      console.error('Error:', error);
      router.push('/');
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left side - Gradient with content */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary to-teal-600 p-12 flex-col justify-center">
        <h1 className="text-white text-4xl font-bold mb-6">
          Welcome to your project portal
        </h1>
        <p className="text-white/80 text-xl mb-12">
          Everything you need to collaborate on your project in one place.
        </p>

        <div className="space-y-6">
          <Feature
            icon={MessageSquare}
            title="Share Your Knowledge"
            description="Answer questions and provide context that helps us build exactly what you need."
          />
          <Feature
            icon={FileText}
            title="Upload Documents"
            description="Share files, reports, and examples that inform the project."
          />
          <Feature
            icon={Zap}
            title="Stay in Sync"
            description="See project updates and provide feedback as we build."
          />
        </div>
      </div>

      {/* Right side - Welcome card */}
      <div className="flex-1 flex items-center justify-center p-8 bg-gray-50">
        <div className="w-full max-w-md">
          {/* Mobile header */}
          <div className="lg:hidden text-center mb-8">
            <h1 className="text-2xl font-bold text-primary mb-2">ReadyToGo.ai</h1>
            <p className="text-gray-600">Your project portal</p>
          </div>

          <div className="card">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Hi{user?.first_name ? `, ${user.first_name}` : ''}!
            </h2>
            <p className="text-gray-600 mb-8">
              Your consultant has set up a project portal for you. Here&apos;s how it works:
            </p>

            <div className="space-y-6 mb-8">
              <Step
                number={1}
                title="Prepare for Discovery"
                description="Answer a few questions before your call to save time."
              />
              <Step
                number={2}
                title="Share Project Context"
                description="After the call, provide additional details and documents."
              />
              <Step
                number={3}
                title="Collaborate"
                description="Use the AI assistant to add information anytime."
              />
            </div>

            <button
              onClick={handleGetStarted}
              disabled={loading}
              className="w-full btn btn-primary py-3 justify-center"
            >
              {loading ? (
                <span className="spinner" />
              ) : (
                <>
                  Get Started
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>

          <p className="mt-6 text-center text-sm text-gray-500">
            Questions? Contact your consultant.
          </p>
        </div>
      </div>
    </div>
  );
}

function Feature({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-4">
      <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center flex-shrink-0">
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div>
        <h3 className="text-white font-semibold mb-1">{title}</h3>
        <p className="text-white/70 text-sm">{description}</p>
      </div>
    </div>
  );
}

function Step({
  number,
  title,
  description,
}: {
  number: number;
  title: string;
  description: string;
}) {
  return (
    <div className="flex gap-4">
      <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0">
        <span className="text-primary font-semibold text-sm">{number}</span>
      </div>
      <div>
        <h3 className="font-semibold text-gray-900 mb-1">{title}</h3>
        <p className="text-sm text-gray-600">{description}</p>
      </div>
    </div>
  );
}
