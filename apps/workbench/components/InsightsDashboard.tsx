import { useEffect, useState } from 'react';

interface Insight {
  id: string;
  title: string;
  severity: 'minor' | 'important' | 'critical';
  category: string;
  finding: string;
  why: string;
  targets: Array<{ kind: string; label: string }>;
  evidence: Array<{ chunk_id: string; excerpt: string }>;
  status: string;
}

export function InsightsDashboard({ projectId }: { projectId: string }) {
  const [insights, setInsights] = useState<Insight[]>([]);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/insights?project_id=${projectId}`)
      .then(res => res.json())
      .then(data => {
        console.log('Insights API response:', data);
        setInsights(Array.isArray(data) ? data : []);
      })
      .catch(error => {
        console.error('Failed to fetch insights:', error);
        setInsights([]);
      });
  }, [projectId]);

  const handleApply = async (insightId: string) => {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/insights/${insightId}/apply`, {
      method: 'PATCH'
    });
    if (response.ok) {
      alert('Insight applied!');
      // Refresh insights
      window.location.reload();
    } else {
      const error = await response.text();
      alert(`Failed to apply insight: ${error}`);
    }
  };

  const handleConfirm = async (insightId: string) => {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/insights/${insightId}/confirm`, {
      method: 'POST'
    });
    if (response.ok) {
      alert('Confirmation item created!');
      // Refresh insights
      window.location.reload();
    } else {
      const error = await response.text();
      alert(`Failed to create confirmation: ${error}`);
    }
  };

  const getSeverityBadgeClasses = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'important':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Research Insights</h2>
      {insights.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>No insights found. Run the Red Team analysis to generate insights.</p>
        </div>
      ) : (
        insights.map(insight => (
          <div key={insight.id} className="card">
            <div className="flex justify-between items-start mb-2">
              <h3 className="font-bold text-lg">{insight.title}</h3>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getSeverityBadgeClasses(insight.severity)}`}>
                {insight.severity}
              </span>
            </div>

            <p className="text-sm text-gray-600 mb-2"><strong>Finding:</strong> {insight.finding}</p>
            <p className="text-sm text-gray-600 mb-2"><strong>Why:</strong> {insight.why}</p>

            <div className="mb-2">
              <strong className="text-sm">Targets:</strong>
              <div className="flex gap-2 mt-1 flex-wrap">
                {insight.targets.map((t, i) => (
                  <span key={i} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    {t.kind}: {t.label}
                  </span>
                ))}
              </div>
            </div>

            <div className="mb-4">
              <strong className="text-sm">Evidence:</strong>
              {insight.evidence.slice(0, 2).map((e, i) => (
                <p key={i} className="text-xs italic text-gray-500 mt-1">"{e.excerpt}"</p>
              ))}
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => handleApply(insight.id)}
                className="btn btn-primary"
              >
                Apply
              </button>
              <button
                onClick={() => handleConfirm(insight.id)}
                className="btn btn-secondary"
              >
                Create Confirmation
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
