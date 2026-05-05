import index from "../index.html";
import { proxyApiRequest } from "./serverProxy";

const port = Number(process.env.PORT ?? "3000");
const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

Bun.serve({
  port: port,
  routes: {
    "/api/*": (request) => proxyApiRequest(request, backendUrl),
    "/*": index
  },
  development: {
    hmr: true,
    console: true
  }
});

console.log(`AssemblyVoice frontend running at http://localhost:${port}`);
