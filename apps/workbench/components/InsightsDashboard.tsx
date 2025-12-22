import { useEffect, useState } from 'react';
import { Badge, Button, Card } from '@/components/ui';

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
    fetch(`/v1/insights?project_id=${projectId}`)
      .then(res => res.json())
      .then(data => setInsights(data));
  }, [projectId]);

  const handleApply = async (insightId: string) => {
    const response = await fetch(`/v1/insights/${insightId}/apply`, {
      method: 'PATCH'
    });
    if (response.ok) {
      alert('Insight applied!');
      // Refresh insights
    }
  };

  const handleConfirm = async (insightId: string) => {
    const response = await fetch(`/v1/insights/${insightId}/confirm`, {
      method: 'POST'
    });
    if (response.ok) {
      alert('Confirmation item created!');
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Research Insights</h2>
      {insights.map(insight => (
        <Card key={insight.id} className="p-4">
          <div className="flex justify-between items-start mb-2">
            <h3 className="font-bold text-lg">{insight.title}</h3>
            <Badge variant={
              insight.severity === 'critical' ? 'destructive' :
              insight.severity === 'important' ? 'warning' : 'default'
            }>
              {insight.severity}
            </Badge>
          </div>

          <p className="text-sm text-gray-600 mb-2"><strong>Finding:</strong> {insight.finding}</p>
          <p className="text-sm text-gray-600 mb-2"><strong>Why:</strong> {insight.why}</p>

          <div className="mb-2">
            <strong className="text-sm">Targets:</strong>
            <div className="flex gap-2 mt-1">
              {insight.targets.map((t, i) => (
                <Badge key={i} variant="outline">{t.kind}: {t.label}</Badge>
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
            <Button size="sm" onClick={() => handleApply(insight.id)}>
              Apply
            </Button>
            <Button size="sm" variant="outline" onClick={() => handleConfirm(insight.id)}>
              Create Confirmation
            </Button>
          </div>
        </Card>
      ))}
    </div>
  );
}
