import { useState } from 'react';
import { Button, Textarea, Card } from '@/components/ui';

export function ResearchIngest({ projectId }: { projectId: string }) {
  const [researchJSON, setResearchJSON] = useState('');
  const [loading, setLoading] = useState(false);

  const handleIngest = async () => {
    setLoading(true);
    try {
      const researchData = JSON.parse(researchJSON);

      const response = await fetch('/v1/research/ingest', {
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
    } catch (error) {
      alert('Invalid JSON or error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="p-6">
      <h2 className="text-xl font-bold mb-4">Ingest Research Document</h2>
      <Textarea
        value={researchJSON}
        onChange={(e) => setResearchJSON(e.target.value)}
        placeholder="Paste research JSON here..."
        rows={10}
        className="mb-4"
      />
      <Button onClick={handleIngest} disabled={loading || !researchJSON}>
        {loading ? 'Ingesting...' : 'Ingest Research'}
      </Button>
    </Card>
  );
}
