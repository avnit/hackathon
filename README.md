# hackathon

<!-- ARCH-DIAGRAM:START -->

## Architecture

> Auto-generated architecture diagram. See [`docs/context-map.md`](docs/context-map.md) for the full context map (core application, containers/cloud, and database connections).

```mermaid
flowchart TD
  User([User / Client])
  App["hackathon<br/><small>main.py</small><br/>FastAPI + Uvicorn"]
  AI["Vertex AI / Gemini<br/>(LLM / Agent Engine)"]
  DB0[("SQLite")]
  Img["Container image<br/>(Docker)"]
  Deploy["Google Cloud Run"]
  User --> App
  App --> AI
  App --> DB0
  App -.deploy.-> Img
  Img -.deploy.-> Deploy
```

<!-- ARCH-DIAGRAM:END -->
