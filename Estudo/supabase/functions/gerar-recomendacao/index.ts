import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function addMonths(mesStr: string, delta: number): string {
  const [y, m] = mesStr.split("-").map(Number);
  const d = new Date(y, m - 1 + delta);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function compound(rates: number[]): number {
  return rates.reduce((acc, r) => acc * (1 + (r ?? 0)), 1) - 1;
}

function irAliquota(dataInicio: string, mesAtual: string): number {
  const inicio = new Date(dataInicio + "-01");
  const atual  = new Date(mesAtual  + "-01");
  const dias   = (atual.getTime() - inicio.getTime()) / 86_400_000;
  if (dias <= 180) return 0.225;
  if (dias <= 360) return 0.200;
  if (dias <= 720) return 0.175;
  return 0.150;
}

// ── Main ──────────────────────────────────────────────────────────────────────

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const { cliente_id, mes } = await req.json();

    if (!cliente_id || !mes) {
      return new Response(
        JSON.stringify({ error: "Missing cliente_id or mes" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    const mes12m = addMonths(mes, -12);

    // ── 1. Client ─────────────────────────────────────────────────────────────
    const { data: cliente, error: errCliente } = await supabase
      .from("clientes")
      .select("nome, perfil_de_risco")
      .eq("id", cliente_id)
      .single();
    if (errCliente) throw new Error(`fetchCliente: ${errCliente.message}`);

    // ── 2. Positions (parallel) ───────────────────────────────────────────────
    const [acoesRes, fundosRes, rfRes] = await Promise.all([
      supabase
        .from("posicoes_acoes")
        .select(`ticker, quantidade, preco_medio_compra, data_compra,
                 ativos_acoes (nome, tipo, setor)`)
        .eq("cliente_id", cliente_id),
      supabase
        .from("posicoes_fundos")
        .select(`cnpj, numero_cotas, valor_aplicado, data_investimento,
                 ativos_fundos (nome, categoria, prazo_resgate_dias)`)
        .eq("cliente_id", cliente_id),
      supabase
        .from("posicoes_renda_fixa")
        .select(`ativo_id, taxa_contratada, unidade_taxa, valor_aplicado,
                 data_inicio, data_vencimento,
                 ativos_renda_fixa (nome, instrumento, indexacao, isento_ir)`)
        .eq("cliente_id", cliente_id),
    ]);

    if (acoesRes.error)  throw new Error(`fetchAcoes: ${acoesRes.error.message}`);
    if (fundosRes.error) throw new Error(`fetchFundos: ${fundosRes.error.message}`);
    if (rfRes.error)     throw new Error(`fetchRF: ${rfRes.error.message}`);

    // ── 3. Prices (parallel) ──────────────────────────────────────────────────
    const tickers = (acoesRes.data ?? []).map((p: any) => p.ticker);
    const cnpjs   = (fundosRes.data ?? []).map((p: any) => p.cnpj);

    const [precosRes, cotasRes] = await Promise.all([
      tickers.length
        ? supabase
            .from("precos_acoes")
            .select("ticker, mes, preco_fechamento")
            .in("ticker", tickers)
            .in("mes", [mes, mes12m])
        : Promise.resolve({ data: [], error: null }),
      cnpjs.length
        ? supabase
            .from("cotas_fundos")
            .select("cnpj, mes, cota_fechamento")
            .in("cnpj", cnpjs)
            .in("mes", [mes, mes12m])
        : Promise.resolve({ data: [], error: null }),
    ]);

    if (precosRes.error) throw new Error(`fetchPrecos: ${precosRes.error.message}`);
    if (cotasRes.error)  throw new Error(`fetchCotas: ${cotasRes.error.message}`);

    // ── 4. Macro (13 months) ──────────────────────────────────────────────────
    const { data: macroRows, error: errMacro } = await supabase
      .from("dados_mercado")
      .select("mes, cdi_mensal, selic_mensal, ipca_mensal, ibovespa_retorno_mensal, ima_b_retorno_mensal, usd_brl_fechamento, pib_crescimento_anual")
      .lte("mes", mes)
      .gte("mes", mes12m)
      .order("mes", { ascending: true });
    if (errMacro) throw new Error(`fetchMacro: ${errMacro.message}`);

    // ── 5. XP Report ──────────────────────────────────────────────────────────
    const { data: rel, error: errRel } = await supabase
      .from("relatorios")
      .select("mes, conteudo_txt")
      .eq("fonte", "XP")
      .eq("tipo", "macro_mensal")
      .lte("mes", mes)
      .order("mes", { ascending: false })
      .limit(1)
      .single();
    if (errRel) throw new Error(`fetchRelatorio: ${errRel.message}`);

    // ── 6. Macro aggregates ───────────────────────────────────────────────────
    const rows     = macroRows ?? [];
    const rows12m  = rows.slice(-12);
    const macroAtual = rows.find((r: any) => r.mes === mes) ?? rows.at(-1) ?? {};

    const cdi_acumulado_12m   = compound(rows12m.map((r: any) => r.cdi_mensal));
    const ibov_acumulado_12m  = compound(rows12m.map((r: any) => r.ibovespa_retorno_mensal));
    const ipca_acumulado_12m  = compound(rows12m.map((r: any) => r.ipca_mensal));
    const ima_b_acumulado_12m = compound(rows12m.map((r: any) => r.ima_b_retorno_mensal));

    const last3 = rows.slice(-3).map((r: any) => r.selic_mensal ?? 0);
    const prev3 = rows.slice(-6, -3).map((r: any) => r.selic_mensal ?? 0);
    const avg  = (arr: number[]) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;
    const selic_tendencia =
      avg(last3) > avg(prev3) * 1.001 ? "alta" :
      avg(last3) < avg(prev3) * 0.999 ? "queda" : "estavel";

    // ── 7. Price maps ─────────────────────────────────────────────────────────
    const precoMap: Record<string, Record<string, number>> = {};
    for (const p of (precosRes.data ?? []) as any[]) {
      (precoMap[p.ticker] ??= {})[p.mes] = p.preco_fechamento;
    }

    const cotaMap: Record<string, Record<string, number>> = {};
    for (const c of (cotasRes.data ?? []) as any[]) {
      (cotaMap[c.cnpj] ??= {})[c.mes] = c.cota_fechamento;
    }

    // ── 8. Compute positions ──────────────────────────────────────────────────
    let valor_total = 0;
    const acoes:      any[] = [];
    const fundos:     any[] = [];
    const renda_fixa: any[] = [];

    for (const p of (acoesRes.data ?? []) as any[]) {
      const meta        = (p.ativos_acoes as any) ?? {};
      const preco_atual = precoMap[p.ticker]?.[mes]    ?? p.preco_medio_compra;
      const preco_12m   = precoMap[p.ticker]?.[mes12m] ?? null;
      const valor_atual = p.quantidade * preco_atual;
      const drawdown    = (preco_atual - p.preco_medio_compra) / p.preco_medio_compra;
      const retorno_12m = preco_12m != null ? (preco_atual - preco_12m) / preco_12m : null;

      valor_total += valor_atual;
      acoes.push({
        ticker: p.ticker,
        nome: meta.nome ?? p.ticker,
        tipo: meta.tipo ?? "Ação",
        setor: meta.setor ?? null,
        quantidade: p.quantidade,
        preco_medio_compra: p.preco_medio_compra,
        preco_atual,
        valor_atual,
        data_compra: p.data_compra,
        drawdown,
        retorno_12m,
        tem_preco_atual: !!precoMap[p.ticker]?.[mes],
      });
    }

    for (const p of (fundosRes.data ?? []) as any[]) {
      const meta        = (p.ativos_fundos as any) ?? {};
      const cota_atual  = cotaMap[p.cnpj]?.[mes]    ?? null;
      const cota_12m    = cotaMap[p.cnpj]?.[mes12m] ?? null;
      const valor_atual = cota_atual ? p.numero_cotas * cota_atual : p.valor_aplicado;
      const retorno_12m = (cota_atual && cota_12m) ? (cota_atual - cota_12m) / cota_12m : null;
      const retorno_aplicado = cota_atual
        ? (valor_atual - p.valor_aplicado) / p.valor_aplicado
        : null;

      const cat = meta.categoria ?? "";
      let benchmark_12m: number | null = null;
      if (cat === "RF DI" || cat === "RF Simples") benchmark_12m = cdi_acumulado_12m;
      else if (cat === "Multimercado" || cat === "Long Biased") benchmark_12m = cdi_acumulado_12m;
      else if (cat === "FIA") benchmark_12m = ibov_acumulado_12m;

      valor_total += valor_atual;
      fundos.push({
        cnpj: p.cnpj,
        nome: meta.nome ?? p.cnpj,
        categoria: cat,
        prazo_resgate_dias: meta.prazo_resgate_dias ?? null,
        numero_cotas: p.numero_cotas,
        valor_aplicado: p.valor_aplicado,
        cota_atual,
        valor_atual,
        data_investimento: p.data_investimento,
        retorno_aplicado,
        retorno_12m,
        benchmark_12m,
        tem_cota_atual: !!cota_atual,
      });
    }

    for (const p of (rfRes.data ?? []) as any[]) {
      const meta = (p.ativos_renda_fixa as any) ?? {};
      const valor_atual    = p.valor_aplicado;
      const ir_aliquota    = meta.isento_ir ? 0 : irAliquota(p.data_inicio, mes);

      valor_total += valor_atual;
      renda_fixa.push({
        nome: meta.nome ?? `RF-${p.ativo_id}`,
        instrumento: meta.instrumento ?? null,
        indexacao: meta.indexacao ?? null,
        isento_ir: meta.isento_ir ?? false,
        taxa_contratada: p.taxa_contratada,
        unidade_taxa: p.unidade_taxa,
        valor_aplicado: p.valor_aplicado,
        valor_atual,
        data_inicio: p.data_inicio,
        data_vencimento: p.data_vencimento,
        ir_aliquota_pct: ir_aliquota,
      });
    }

    // ── 9. Weights & allocation breakdown ────────────────────────────────────
    const vt = valor_total || 1;

    for (const a of acoes)      a.peso = a.valor_atual / vt;
    for (const f of fundos)     f.peso = f.valor_atual / vt;
    for (const r of renda_fixa) r.peso = r.valor_atual / vt;

    const sum = (arr: any[], fn: (x: any) => number) =>
      arr.reduce((s, x) => s + fn(x), 0);

    const alocacao = {
      acoes_pct:         sum(acoes,      a => a.tipo === "Ação" ? a.peso : 0),
      fii_pct:           sum(acoes,      a => a.tipo === "FII"  ? a.peso : 0),
      fia_longbiased_pct:sum(fundos,     f => (f.categoria === "FIA" || f.categoria === "Long Biased") ? f.peso : 0),
      multimercado_pct:  sum(fundos,     f => f.categoria === "Multimercado" ? f.peso : 0),
      rf_fundos_pct:     sum(fundos,     f => (f.categoria === "RF DI" || f.categoria === "RF Simples") ? f.peso : 0),
      rf_direta_pct:     sum(renda_fixa, r => r.peso),
    };
    (alocacao as any).risco_equity_total_pct =
      alocacao.acoes_pct + alocacao.fii_pct + alocacao.fia_longbiased_pct;
    (alocacao as any).renda_fixa_total_pct =
      alocacao.rf_fundos_pct + alocacao.rf_direta_pct;

    // ── 10. Assemble payload ──────────────────────────────────────────────────
    const payload = {
      cliente: {
        nome: cliente.nome,
        perfil_de_risco: cliente.perfil_de_risco,
      },
      portfolio: {
        valor_total,
        mes_referencia: mes,
        alocacao,
        acoes,
        fundos,
        renda_fixa,
      },
      macro: {
        mes_referencia: macroAtual.mes ?? mes,
        cdi_mensal:              macroAtual.cdi_mensal,
        selic_mensal:            macroAtual.selic_mensal,
        ipca_mensal:             macroAtual.ipca_mensal,
        ibovespa_retorno_mensal: macroAtual.ibovespa_retorno_mensal,
        ima_b_retorno_mensal:    macroAtual.ima_b_retorno_mensal,
        usd_brl:                 macroAtual.usd_brl_fechamento,
        pib_crescimento_anual:   macroAtual.pib_crescimento_anual,
        cdi_acumulado_12m,
        ibov_acumulado_12m,
        ipca_acumulado_12m,
        ima_b_acumulado_12m,
        selic_tendencia,
      },
      relatorio: {
        mes: rel.mes,
        aviso: rel.mes !== mes ? `[Relatório de ${rel.mes} — mais recente disponível]` : null,
        conteudo: rel.conteudo_txt,
      },
    };

    // ── 11. Insert job ────────────────────────────────────────────────────────
    const { data: rec, error: errRec } = await supabase
      .from("recomendacoes")
      .insert({ cliente_id, mes, status: "processing" })
      .select("job_id")
      .single();
    if (errRec) throw new Error(`insertJob: ${errRec.message}`);

    const job_id = rec.job_id;

    // ── 12. Fire Railway ──────────────────────────────────────────────────────
    const rivetUrl = Deno.env.get("RIVET_SERVER_URL")!;
    await fetch(rivetUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, job_id }),
    });

    return new Response(
      JSON.stringify({ job_id }),
      { status: 202, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (err) {
    return new Response(
      JSON.stringify({ error: (err as Error).message }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
