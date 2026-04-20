import index from "../index.html";

const port = Number(process.env.PORT ?? "3000");

Bun.serve({
  port: port,
  routes: {
    "/*": index
  },
  development: {
    hmr: true,
    console: true
  }
});

console.log(`AssemblyVoice frontend running at http://localhost:${port}`);
