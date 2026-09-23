import { createServer } from "vite";

export default async function startVisualServer() {
  const server = await createServer({ server: { host: "127.0.0.1", port: 4274, strictPort: true } });
  await server.listen();
  return async () => { await server.close(); };
}
