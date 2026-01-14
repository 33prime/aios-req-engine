'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';

export default function ProjectPage() {
  const params = useParams();
  const router = useRouter();

  useEffect(() => {
    // Redirect to dashboard
    router.replace(`/${params.projectId}/dashboard`);
  }, [params.projectId, router]);

  return (
    <div className="flex items-center justify-center py-12">
      <div className="spinner" />
    </div>
  );
}
