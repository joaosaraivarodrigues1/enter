import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

// =============================================================================
// IMA-B — DOCUMENTAÇÃO (não implementado, requer acesso manual)
// =============================================================================
//
// O IMA-B é um índice da ANBIMA que não possui API pública.
//
// Como obter:
//   1. Acesse data.anbima.com.br e crie uma conta gratuita.
//   2. Vá em "Índices de Mercado" → "IMA" → "IMA-B".
//   3. Selecione o período desejado e exporte o CSV.
//   4. O CSV contém colunas: Data, Número Índice, Retorno Diário, Retorno Mês, Retorno Ano.
//   5. Use a coluna "Retorno Mês" — já é o retorno percentual mensal acumulado.
//   6. Faça upload do CSV via Streamlit (futura aba na página "Índice Mercado")
//      e insira em dados_mercado.ima_b_retorno_mensal via upsert por mês.
//
// Enquanto não carregado, ima_b_retorno_mensal permanece null.
// Isso não impede o cálculo dos demais índices.
// =============================================================================

const BRAPI_TOKEN      = Deno.env.get("BRAPI_TOKEN") ?? "";
const SUPABASE_URL     = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

// "DD/MM/AAAA" → "YYYY-MM"
function bcbParaMes(data: string): string {
  const [, m, y] = data.split("/");
  return `${y}-${m}`;
}

// Date → "DD/MM/AAAA" para a BCB API
function formatBCB(date: Date): string {
  const d = String(date.getDate()).padStart(2, "0");
  const m = String(date.getMonth() + 1).padStart(2, "0");
  return `${d}/${m}/${date.getFullYear()}`;
}

// Unix timestamp (segundos) → "YYYY-MM"
function unixParaMes(ts: number): string {
  const d = new Date(ts * 1000);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

// Busca uma série do BCB e retorna mapa { "YYYY-MM": valor }
async function fetchBCB(
  serie: number,
  dataInicial: string,
  dataFinal: string,
): Promise<Record<string, number>> {
  const url =
    `https://api.bcb.gov.br/dados/serie/bcdata.sgs.${serie}/dados` +
    `?dataInicial=${dataInicial}&dataFinal=${dataFinal}&formato=json`;

  const res = await fetch(url);
  if (!res.ok) throw new Error(`BCB série ${serie} retornou ${res.status}`);

  const dados: Array<{ data: string; valor: string }> = await res.json();

  return Object.fromEntries(
    dados.map((item) => [
      bcbParaMes(item.data),
      parseFloat(item.valor.replace(",", ".")),
    ]),
  );
}

Deno.serve(async (_req: Request) => {
  try {
    // Intervalo: últimos 5 anos até hoje
    const hoje   = new Date();
    const inicio = new Date(hoje);
    inicio.setFullYear(inicio.getFullYear() - 5);

    const dataInicial = formatBCB(inicio);
    const dataFinal   = formatBCB(hoje);

    // ── Chamadas em paralelo ─────────────────────────────────────────────────
    // IBOVESPA via Yahoo Finance — brapi.dev restringe índices a 3mo no plano free
    const [cdiMap, ipcaMap, selicMap, resIbov] = await Promise.all([
      fetchBCB(4391, dataInicial, dataFinal),   // CDI acumulado no mês
      fetchBCB(433,  dataInicial, dataFinal),   // IPCA mensal
      fetchBCB(4390, dataInicial, dataFinal),   // Selic acumulada no mês
      fetch(
        "https://query1.finance.yahoo.com/v8/finance/chart/%5EBVSP?interval=1mo&range=5y",
        { headers: { "User-Agent": "Mozilla/5.0" } },
      ),
    ]);

    if (!resIbov.ok) {
      return json({ error: `Yahoo Finance IBOVESPA ${resIbov.status}` }, 502);
    }

    // ── IBOVESPA: calcula retorno mensal a partir dos pontos ─────────────────
    // retorno_mes_N = (close_N - close_N-1) / close_N-1 × 100
    // Yahoo Finance response: chart.result[0].timestamp[] + indicators.quote[0].close[]
    const ibovDados = await resIbov.json();
    const ibovResult = ibovDados.chart?.result?.[0];
    const timestamps: number[]  = ibovResult?.timestamp ?? [];
    const closes: number[]      = ibovResult?.indicators?.quote?.[0]?.close ?? [];

    const ibovHistorico = timestamps.map((ts, i) => ({
      date: ts,
      close: closes[i],
    })).filter((h) => h.close != null);

    const ibovMap: Record<string, number> = {};
    for (let i = 1; i < ibovHistorico.length; i++) {
      const prev = ibovHistorico[i - 1].close;
      const curr = ibovHistorico[i].close;
      const mes  = unixParaMes(ibovHistorico[i].date);
      ibovMap[mes] = ((curr - prev) / prev) * 100;
    }

    // ── Monta registros — um por mês presente em qualquer série ─────────────
    const todosMeses = new Set([
      ...Object.keys(cdiMap),
      ...Object.keys(ipcaMap),
      ...Object.keys(selicMap),
      ...Object.keys(ibovMap),
    ]);

    const registros = Array.from(todosMeses).map((mes) => ({
      mes,
      cdi_mensal:               cdiMap[mes]  ?? null,
      ipca_mensal:              ipcaMap[mes] ?? null,
      selic_mensal:             selicMap[mes] ?? null,
      ibovespa_retorno_mensal:  ibovMap[mes]  ?? null,
      ima_b_retorno_mensal:     null,  // carregado manualmente — ver docs no topo
    }));

    // ── Upsert em dados_mercado ──────────────────────────────────────────────
    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);
    const { error } = await supabase
      .from("dados_mercado")
      .upsert(registros, { onConflict: "mes" });

    if (error) return json({ error: error.message }, 500);

    return json({ ok: true, meses_inseridos: registros.length });

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
