import { useEffect, useState } from "react";
import { NewProject } from "./views/NewProject";
import { ProjectStudio } from "./views/ProjectStudio";

const lastProjectKey = "psyteardown.lastProjectId";

function projectIdFromPath(): string | null {
  const match = window.location.pathname.match(/^\/projects\/([^/]+)\/?$/);
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

export default function App() {
  const [projectId, setProjectId] = useState(projectIdFromPath);
  const [lastProjectId, setLastProjectId] = useState<string | null>(() => {
    try { return window.localStorage.getItem(lastProjectKey); } catch { return null; }
  });

  useEffect(() => {
    const handlePopState = () => setProjectId(projectIdFromPath());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  function navigate(nextProjectId: string | null) {
    const path = nextProjectId ? `/projects/${encodeURIComponent(nextProjectId)}` : "/";
    window.history.pushState({}, "", path);
    setProjectId(nextProjectId);
    if (nextProjectId) {
      setLastProjectId(nextProjectId);
      try { window.localStorage.setItem(lastProjectKey, nextProjectId); } catch { /* private mode */ }
    }
  }

  return projectId ? (
    <ProjectStudio projectId={projectId} onExit={() => navigate(null)} />
  ) : (
    <NewProject lastProjectId={lastProjectId} onCreated={(id) => navigate(id)} />
  );
}
