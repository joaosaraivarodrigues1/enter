import "dotenv/config";
import express from "express";
import { loadProjectFromFile, runGraph, startDebuggerServer } from "@ironclad/rivet-node";

const OPENAI_API_KEY            = process.env.OPENAI_API_KEY?.replace(/\s/g, "");
const SUPABASE_URL              = process.env.SUPABASE_URL?.trim();
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY?.replace(/\s/g, "");

if (!OPENAI_API_KEY || !SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
  console.error("Missing env vars. Check .env file.");
  process.exit(1);
}

// ── Remote Debugger (apenas em desenvolvimento local) ────────────────────────

let debuggerServer = null;
if (process.env.NODE_ENV !== "production") {
  debuggerServer = startDebuggerServer({
    port: 21888,
    dynamicGraphRun: async ({ inputs, graphId }) => {
      const project = await loadProjectFromFile(PROJECT_PATH);
      return await runGraph(project, {
        graph: graphId,
        openAiKey: OPENAI_API_KEY,
        inputs,
        remoteDebugger: debuggerServer,
      });
    },
    allowGraphUpload: true,
  });
  console.log("Remote Debugger listening on ws://localhost:21888");
}

// ── Load Rivet project ───────────────────────────────────────────────────────

const PROJECT_PATH = new URL("./Rivet.rivet-project", import.meta.url).pathname
  .replace(/^\/([A-Za-z]:)/, "$1");

let project;
try {
  project = await loadProjectFromFile(PROJECT_PATH);
  console.log("Rivet project loaded.");
} catch (err) {
  console.error("Failed to load Rivet project:", err.message);
  process.exit(1);
}

// ── Supabase helper ──────────────────────────────────────────────────────────

async function supabasePatch(table, filter, body) {
  const url = `${SUPABASE_URL}/rest/v1/${table}?${filter}`;
  const res = await fetch(url, {
    method: "PATCH",
    headers: {
      apikey: SUPABASE_SERVICE_ROLE_KEY,
      Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
      "Content-Type": "application/json",
      Prefer: "return=minimal",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Supabase PATCH failed: ${res.status} ${text}`);
  }
}


// ── Express server ───────────────────────────────────────────────────────────

const app = express();
app.use(express.json({ limit: "2mb" }));

app.post("/", async (req, res) => {
  const { job_id, cliente_id, mes_referencia } = req.body;

  if (!job_id || !cliente_id || !mes_referencia) {
    return res.status(400).json({ error: "Missing required fields" });
  }

  // Respond immediately — process in background
  res.status(202).json({ status: "processing", job_id });

  (async () => {
    try {
      console.log(`[${job_id}] running Rivet graph — cliente: ${cliente_id}, mes: ${mes_referencia}`);

      const outputs = await runGraph(project, {
        graph: "gerar_recomendacao",
        openAiKey: OPENAI_API_KEY,
        ...(debuggerServer ? { remoteDebugger: debuggerServer } : {}),
        contextValues: {
          supabase_url: SUPABASE_URL,
          supabase_key: SUPABASE_SERVICE_ROLE_KEY,
        },
        inputs: {
          job: { type: "object", value: { job_id, cliente_id, mes_referencia } },
        },
      });

      const resultado = outputs?.recomendacao?.value ?? "";
      console.log(`[${job_id}] resultado length: ${String(resultado).length}`);

      await supabasePatch(
        "recomendacoes",
        `job_id=eq.${job_id}`,
        { status: "done", resultado, concluido_em: new Date().toISOString() }
      );

      console.log(`[${job_id}] done.`);
    } catch (err) {
      console.error(`[${job_id}] error:`, err.message);
      console.error(`[${job_id}] cause:`, err.cause?.message ?? "(no cause)");
      await supabasePatch(
        "recomendacoes",
        `job_id=eq.${job_id}`,
        { status: "error", erro: err.message, concluido_em: new Date().toISOString() }
      ).catch(() => {});
    }
  })();
});

app.get("/health", (_req, res) => {
  res.json({ status: "ok" });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Rivet server listening on port ${PORT}`);
});
