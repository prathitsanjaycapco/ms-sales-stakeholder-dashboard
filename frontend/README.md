# Morgan Stanley Account Intelligence frontend

React and Vite single-page application for the executive, pod, stakeholder, and resourcing experiences.

## Run locally

```powershell
npm.cmd ci
npm.cmd run dev
```

`VITE_API_URL` defaults to `/api`. For standalone development, Vite proxies that path to `http://127.0.0.1:8000`; set `VITE_PROXY_TARGET` to another API base URL when needed.

## Validate

```powershell
npm run test:unit
npm run build
npm run test:visual
```

Browser workflow tests require a running API. Start the backend separately and run `npm run test:e2e`, or use the sibling-repository Docker Compose environment in the infrastructure repository.
