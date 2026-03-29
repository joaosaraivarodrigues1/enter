import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const SUPABASE_URL         = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const BRAPI_TOKEN          = Deno.env.get("BRAPI_TOKEN") ?? "";

// Unix timestamp (segundos) → "YYYY-MM"
function unixParaMes(ts: number): string {
  const d = new Date(ts * 1000);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

// "YYYY-MM-DD" → "YYYY-MM"
function dateStrParaMes(dateStr: string): string {
  return dateStr.slice(0, 7);
}

async function fetchComRetry(url: string): Promise<{ res: Response; body: string }> {
  const MAX = 6;
  let ultimoStatus = 0;
  let ultimoBody   = "";

  for (let i = 1; i <= MAX; i++) {
    const res = await fetch(url, { headers: { "User-Agent": "Mozilla/5.0" } });
    const body = await res.text();
    if (res.ok) return { res, body };
    ultimoStatus = res.status;
    ultimoBody   = body;
    if (i < MAX) await new Promise(r => setTimeout(r, 2000));
  }

  throw new Error(`brapi.dev status ${ultimoStatus} após 6 tentativas — ${ultimoBody}`);
}

Deno.serve(async (req: Request) => {
  try {
    const body = await req.json();

    // Aceita chamada via webhook  { record: { ticker } }
    // ou chamada manual          { ticker }
    const ticker: string | undefined = body.record?.ticker ?? body.ticker;

    if (!ticker) {
      return json({ error: "ticker obrigatório" }, 400);
    }

    const t = BRAPI_TOKEN ? `&token=${BRAPI_TOKEN}` : "";

    // ── Chamada 1: histórico de preços mensais ────────────────────────────────
    const urlPrecos = `https://brapi.dev/api/quote/${ticker}?range=5y&interval=1mo${t}`;
    let dadosPrecos: { historicalDataPrice?: { date: number; close: number | null }[] } = {};

    try {
      const { body: raw } = await fetchComRetry(urlPrecos);
      const parsed = JSON.parse(raw);
      dadosPrecos = parsed?.results?.[0] ?? {};
    } catch (e) {
      return json({ error: String(e) }, 502);
    }

    // ── Chamada 2: dividendos ─────────────────────────────────────────────────
    const urlDivs = `https://brapi.dev/api/quote/${ticker}?dividends=true${t}`;
    let cashDividends: { paymentDate: string; rate: number }[] = [];

    try {
      const { body: raw } = await fetchComRetry(urlDivs);
      const parsed = JSON.parse(raw);
      cashDividends = parsed?.results?.[0]?.dividendsData?.cashDividends ?? [];
    } catch {
      // dividendos opcionais — continua sem eles
    }

    // ── Processa dividendos por mês ───────────────────────────────────────────
    const dividendosPorMes: Record<string, number> = {};
    for (const div of cashDividends) {
      if (!div.paymentDate) continue;
      const mes = dateStrParaMes(div.paymentDate);
      dividendosPorMes[mes] = (dividendosPorMes[mes] ?? 0) + div.rate;
    }

    // ── Processa preços por mês ───────────────────────────────────────────────
    const historico = dadosPrecos.historicalDataPrice ?? [];

    if (historico.length === 0) {
      return json({ ok: true, ticker, meses_inseridos: 0, aviso: "sem dados históricos" });
    }

    const porMes = new Map<string, number>();
    for (const item of historico) {
      if (item.close == null) continue;
      const mes = unixParaMes(item.date);
      porMes.set(mes, item.close);
    }

    const registros = Array.from(porMes.entries()).map(([mes, preco]) => ({
      ticker,
      mes,
      preco_fechamento: preco,
      dividendos_pagos: dividendosPorMes[mes] ?? 0,
    }));

    if (registros.length === 0) {
      return json({ ok: true, ticker, meses_inseridos: 0, aviso: "sem dados históricos" });
    }

    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);
    const { error } = await supabase
      .from("precos_acoes")
      .upsert(registros, { onConflict: "ticker,mes" });

    if (error) return json({ error: error.message }, 500);

    return json({ ok: true, ticker, meses_inseridos: registros.length });

  } catch (err) {
    return json({ error: String(err) }, 500);
  }
});

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
