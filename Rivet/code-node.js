const cliente = (inputs.r_cliente?.value ?? [])[0] ?? {};
const posicoes_acoes = inputs.r_posicoes_acoes?.value ?? [];
const ativos_acoes = inputs.r_ativos_acoes?.value ?? [];
const precos_acoes = inputs.r_precos_acoes?.value ?? [];
const posicoes_fundos = inputs.r_posicoes_fundos?.value ?? [];
const ativos_fundos = inputs.r_ativos_fundos?.value ?? [];
const cotas_fundos = inputs.r_cotas_fundos?.value ?? [];
const posicoes_rf = inputs.r_posicoes_rf?.value ?? [];
const ativos_rf = inputs.r_ativos_rf?.value ?? [];
const macro_raw = (inputs.r_macro?.value ?? [])[0] ?? {};
const relatorio_raw = (inputs.r_relatorio?.value ?? [])[0] ?? {};
const mes_referencia = inputs.mes_referencia?.value ?? '';

const ativos_acoes_map = {};
for (const a of ativos_acoes) ativos_acoes_map[a.ticker] = a;
const precos_map = {};
for (const p of precos_acoes) precos_map[p.ticker] = p.preco_fechamento;
const ativos_fundos_map = {};
for (const f of ativos_fundos) ativos_fundos_map[f.cnpj] = f;
const cotas_map = {};
for (const c of cotas_fundos) cotas_map[c.cnpj] = c.cota_fechamento;
const ativos_rf_map = {};
for (const a of ativos_rf) ativos_rf_map[a.id] = a;

const acoes = posicoes_acoes.map(function(p) {
  const ativo = ativos_acoes_map[p.ticker] || {};
  const preco_atual = precos_map[p.ticker] != null ? precos_map[p.ticker] : null;
  const valor_atual = preco_atual != null ? p.quantidade * preco_atual : null;
  const drawdown = preco_atual != null ? (preco_atual - p.preco_medio_compra) / p.preco_medio_compra : null;
  return { ticker: p.ticker, nome: ativo.nome || p.ticker, tipo: ativo.tipo || null, setor: ativo.setor || null, quantidade: p.quantidade, preco_medio_compra: p.preco_medio_compra, preco_atual: preco_atual, valor_atual: valor_atual, drawdown: drawdown, data_compra: p.data_compra };
});

const fundos = posicoes_fundos.map(function(p) {
  const ativo = ativos_fundos_map[p.cnpj] || {};
  const cota_atual = cotas_map[p.cnpj] != null ? cotas_map[p.cnpj] : null;
  const valor_atual = cota_atual != null ? p.numero_cotas * cota_atual : null;
  const retorno_aplicado = valor_atual != null && p.valor_aplicado ? (valor_atual - p.valor_aplicado) / p.valor_aplicado : null;
  return { cnpj: p.cnpj, nome: ativo.nome || p.cnpj, categoria: ativo.categoria || null, prazo_resgate_dias: ativo.prazo_resgate_dias || null, numero_cotas: p.numero_cotas, cota_atual: cota_atual, valor_atual: valor_atual, valor_aplicado: p.valor_aplicado, retorno_aplicado: retorno_aplicado, data_investimento: p.data_investimento };
});

const renda_fixa = posicoes_rf.map(function(p) {
  const ativo = ativos_rf_map[p.ativo_id] || {};
  var ir = null;
  if (!ativo.isento_ir && p.data_inicio) {
    const dias = (new Date() - new Date(p.data_inicio)) / (1000 * 60 * 60 * 24);
    if (dias <= 180) ir = 0.225;
    else if (dias <= 360) ir = 0.20;
    else if (dias <= 720) ir = 0.175;
    else ir = 0.15;
  }
  return { nome: ativo.nome || p.ativo_id, instrumento: ativo.instrumento || null, indexacao: ativo.indexacao || null, isento_ir: ativo.isento_ir || false, taxa_contratada: p.taxa_contratada, valor_atual: p.valor_aplicado, data_inicio: p.data_inicio, data_vencimento: p.data_vencimento, ir_aliquota_pct: ir };
});

const valor_total =
  acoes.reduce(function(s, a) { return s + (a.valor_atual || 0); }, 0) +
  fundos.reduce(function(s, f) { return s + (f.valor_atual || 0); }, 0) +
  renda_fixa.reduce(function(s, r) { return s + (r.valor_atual || 0); }, 0);

for (var i = 0; i < acoes.length; i++) acoes[i].peso = valor_total > 0 ? (acoes[i].valor_atual || 0) / valor_total : 0;
for (var j = 0; j < fundos.length; j++) fundos[j].peso = valor_total > 0 ? (fundos[j].valor_atual || 0) / valor_total : 0;
for (var k = 0; k < renda_fixa.length; k++) renda_fixa[k].peso = valor_total > 0 ? (renda_fixa[k].valor_atual || 0) / valor_total : 0;

const acoes_pct = acoes.reduce(function(s, a) { return s + a.peso; }, 0);
const mm_pct = fundos.filter(function(f) { return f.categoria === 'Multimercado'; }).reduce(function(s, f) { return s + f.peso; }, 0);
const fia_lb_pct = fundos.filter(function(f) { return f.categoria === 'Long Biased' || f.categoria === 'FIA'; }).reduce(function(s, f) { return s + f.peso; }, 0);
const rf_fundos_pct = fundos.filter(function(f) { return f.categoria === 'RF DI' || f.categoria === 'Simples'; }).reduce(function(s, f) { return s + f.peso; }, 0);
const rf_direta_pct = renda_fixa.reduce(function(s, r) { return s + r.peso; }, 0);
const risco_equity_total_pct = acoes_pct + fia_lb_pct;
const renda_fixa_total_pct = rf_fundos_pct + rf_direta_pct;

const macro = {
  cdi_mensal: macro_raw.cdi_mensal != null ? macro_raw.cdi_mensal / 100 : null,
  selic_mensal: macro_raw.selic_mensal != null ? macro_raw.selic_mensal / 100 : null,
  ipca_mensal: macro_raw.ipca_mensal != null ? macro_raw.ipca_mensal / 100 : null,
  ibovespa_retorno_mensal: macro_raw.ibovespa_retorno_mensal != null ? macro_raw.ibovespa_retorno_mensal / 100 : null,
  usd_brl: macro_raw.usd_brl_fechamento != null ? macro_raw.usd_brl_fechamento : null,
  pib_crescimento_anual: macro_raw.pib_crescimento_anual != null ? macro_raw.pib_crescimento_anual / 100 : null,
};

const nome = cliente.nome || 'N/D';
const perfil_de_risco = cliente.perfil_de_risco || 'moderado';

function pct(v) { if (v == null) return 'N/D'; return (v * 100).toFixed(1) + '%'; }
function brl(v) {
  if (v == null) return 'N/D';
  const n = Math.round(Number(v) * 100);
  const neg = n < 0;
  const abs = Math.abs(n);
  const s = String(abs).padStart(3, '0');
  const cents = s.slice(-2);
  const intPart = s.slice(0, -2);
  var result = '';
  var count = 0;
  for (var x = intPart.length - 1; x >= 0; x--) {
    if (count > 0 && count % 3 === 0) result = '.' + result;
    result = intPart[x] + result;
    count++;
  }
  return (neg ? '-' : '') + 'R$' + result + ',' + cents;
}

const TARGETS = {
  conservador: { equity: 0.025, multimercado: 0.10, rf: 0.875 },
  moderado:    { equity: 0.225, multimercado: 0.225, rf: 0.55 },
  arrojado:    { equity: 0.50,  multimercado: 0.325, rf: 0.175 },
  agressivo:   { equity: 0.60,  multimercado: 0.35,  rf: 0.05 },
};
const target = TARGETS[perfil_de_risco.toLowerCase()] || TARGETS['moderado'];

var promptText = 'INSTRUCAO: Voce e um sistema de validacao de dados. Sua UNICA tarefa e copiar e colar o conteudo abaixo EXATAMENTE como esta, sem alterar nenhum caractere, sem adicionar texto, sem analisar, sem recomendar, sem escrever carta. Apenas reproduza o bloco de dados abaixo integralmente.';
promptText += '\n\n## DADOS ESTRUTURADOS COMPLETOS';
promptText += '\n\n### CLIENTE';
promptText += '\nNome: ' + nome;
promptText += '\nPerfil de Risco: ' + perfil_de_risco;
promptText += '\n\n### MACRO - MES ' + mes_referencia;
promptText += '\nCDI mensal: ' + pct(macro.cdi_mensal);
promptText += '\nSELIC mensal: ' + pct(macro.selic_mensal);
promptText += '\nIPCA mensal: ' + pct(macro.ipca_mensal);
promptText += '\nIBOVESPA mensal: ' + pct(macro.ibovespa_retorno_mensal);
promptText += '\nUSD/BRL: ' + (macro.usd_brl != null ? macro.usd_brl : 'N/D');
promptText += '\nPIB crescimento anual: ' + pct(macro.pib_crescimento_anual);
promptText += '\n\n### PORTFOLIO - VALOR TOTAL: ' + brl(valor_total);
promptText += '\nMes de referencia: ' + mes_referencia;
promptText += '\n\nAlocacao atual:';
promptText += '\n  Acoes: ' + pct(acoes_pct);
promptText += '\n  FIA + Long Biased: ' + pct(fia_lb_pct);
promptText += '\n  Multimercado: ' + pct(mm_pct);
promptText += '\n  RF Fundos DI: ' + pct(rf_fundos_pct);
promptText += '\n  RF Direta: ' + pct(rf_direta_pct);
promptText += '\n  [Risco Equity Total]: ' + pct(risco_equity_total_pct);
promptText += '\n  [Renda Fixa Total]: ' + pct(renda_fixa_total_pct);
promptText += '\n\n### ALOCACAO vs ALVO (perfil ' + perfil_de_risco + ')';
promptText += '\nRisco equity:  atual ' + pct(risco_equity_total_pct) + ' | alvo ' + pct(target.equity) + ' | desvio ' + pct(risco_equity_total_pct - target.equity);
promptText += '\nMultimercado:  atual ' + pct(mm_pct) + ' | alvo ' + pct(target.multimercado) + ' | desvio ' + pct(mm_pct - target.multimercado);
promptText += '\nRenda fixa:    atual ' + pct(renda_fixa_total_pct) + ' | alvo ' + pct(target.rf) + ' | desvio ' + pct(renda_fixa_total_pct - target.rf);
promptText += '\n\n### ACOES - POSICOES DETALHADAS';
for (var i = 0; i < acoes.length; i++) {
  var a = acoes[i];
  promptText += '\nTicker: ' + a.ticker + ' | Nome: ' + a.nome + ' | Tipo: ' + (a.tipo || 'N/D') + ' | Setor: ' + (a.setor || 'N/D');
  promptText += '\n  Quantidade: ' + a.quantidade + ' | PM compra: ' + brl(a.preco_medio_compra) + ' | Preco atual: ' + brl(a.preco_atual);
  promptText += '\n  Valor atual: ' + brl(a.valor_atual) + ' | Peso: ' + pct(a.peso);
  promptText += '\n  Drawdown vs PM: ' + pct(a.drawdown) + ' | Data compra: ' + (a.data_compra || 'N/D');
}
promptText += '\n\n### FUNDOS - POSICOES DETALHADAS';
for (var j = 0; j < fundos.length; j++) {
  var f = fundos[j];
  promptText += '\nNome: ' + f.nome + ' | CNPJ: ' + f.cnpj + ' | Categoria: ' + f.categoria;
  promptText += '\n  Valor atual: ' + brl(f.valor_atual) + ' | Peso: ' + pct(f.peso) + ' | Liquidez: D+' + (f.prazo_resgate_dias || 'N/D');
  promptText += '\n  Cotas: ' + f.numero_cotas + ' | Cota atual: ' + brl(f.cota_atual) + ' | Valor aplicado: ' + brl(f.valor_aplicado);
  promptText += '\n  Retorno s/ aplicado: ' + (f.retorno_aplicado != null ? pct(f.retorno_aplicado) : 'sem dado');
  promptText += '\n  Data investimento: ' + (f.data_investimento || 'N/D');
}
promptText += '\n\n### RENDA FIXA - POSICOES DETALHADAS';
for (var k = 0; k < renda_fixa.length; k++) {
  var r = renda_fixa[k];
  promptText += '\nNome: ' + r.nome + ' | Instrumento: ' + (r.instrumento || 'N/D') + ' | Indexacao: ' + (r.indexacao || 'N/D');
  promptText += '\n  Valor atual: ' + brl(r.valor_atual) + ' | Peso: ' + pct(r.peso);
  promptText += '\n  Taxa: ' + r.taxa_contratada + ' | Vencimento: ' + r.data_vencimento + ' | Inicio: ' + r.data_inicio;
  promptText += '\n  IR: ' + (r.isento_ir ? 'ISENTO' : 'Aliquota ' + pct(r.ir_aliquota_pct));
}
promptText += '\n\n### RELATORIO XP\n' + (relatorio_raw.conteudo_txt || 'N/D');

return { prompt: { type: 'string', value: promptText } };
