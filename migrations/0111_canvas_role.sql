-- Add canvas_role to personas for Canvas View actor selection
ALTER TABLE personas
  ADD COLUMN canvas_role TEXT CHECK (canvas_role IN ('primary', 'secondary'));

-- Index for fast lookup of canvas actors per project
CREATE INDEX idx_personas_canvas_role ON personas (project_id, canvas_role)
  WHERE canvas_role IS NOT NULL;

COMMENT ON COLUMN personas.canvas_role IS 'Canvas View role: primary (max 2) or secondary (max 1). NULL = not selected for canvas.';
