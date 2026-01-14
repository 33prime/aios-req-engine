import { useState } from 'react';
import { Button, Card } from '@/components/ui';

export function ResearchIngest({ projectId }: { projectId: string }) {
  const [researchJSON, setResearchJSON] = useState('');
  const [loading, setLoading] = useState(false);

  const handleIngest = async () => {
    setLoading(true);
    try {
      const researchData = JSON.parse(researchJSON);
      const apiBase = process.env.NEXT_PUBLIC_API_BASE || '';

      const response = await fetch(`${apiBase}/v1/research/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          research_data: researchData
        })
      });

      if (response.ok) {
        alert('Research ingested successfully!');
        setResearchJSON('');
      } else {
        alert('Failed to ingest research');
      }
    } catch (error: any) {
      alert('Invalid JSON or error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="p-6">
      <h2 className="text-xl font-bold mb-4">Ingest Research Document</h2>
      <textarea
        value={researchJSON}
        onChange={(e) => setResearchJSON(e.target.value)}
        placeholder="Paste research JSON here..."
        rows={10}
        className="w-full mb-4 p-3 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      />
      <Button onClick={handleIngest} disabled={loading || !researchJSON}>
        {loading ? 'Ingesting...' : 'Ingest Research'}
      </Button>
    </Card>
  );
}



