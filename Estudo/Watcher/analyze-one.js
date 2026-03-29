const { createClient } = require("@supabase/supabase-js");
const Anthropic = require("@anthropic-ai/sdk").default;
require("dotenv").config();

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);
const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const BUCKET = "documents-incoming";

const args = process.argv.slice(2);
const FLAG_REANALYZE = args.includes("--reanalyze");
const idArg = args.find((a) => a.startsWith("--id="));
const TARGET_ID = idArg ? idArg.split("=")[1] : null;

const SYSTEM_PROMPT = `Você é um assistente jurídico especializado em contratos brasileiros. Recebe um documento em PDF e deve devolver APENAS um objeto JSON válido (sem markdown, sem backticks, sem texto fora do JSON).

Use null quando a informação não existir no documento. Extraia tudo do CORPO do documento, não do nome do arquivo.

ONDE ENCONTRAR CADA INFORMAÇÃO:
- O TIPO do documento está no título/cabeçalho (ex: "CONTRATO DE PRESTAÇÃO DE SERVIÇOS", "TERMO DE CONFIDENCIALIDADE", "TERMO DE RECEBIMENTO").
- As PARTES estão no parágrafo de qualificação logo após o título, iniciando com "Pelo presente instrumento particular" ou similar. Cada parte traz: razão social ou nome completo, endereço com CEP, CNPJ ou CPF, representante legal (nome, RG, CPF, endereço, email). Atenção: "doravante denominada CONTRATADA/CONTRATANTE/DIVULGADORA/RECEPTORA" indica o papel.
- O QUADRO RESUMO (em contratos de prestação de serviço) contém: objeto, vigência, valor, prazo de pagamento, reajuste, multa de mora, multa penal, comunicação, anexos.
- VALORES aparecem no quadro resumo e na cláusula de pagamento (ex: "R$3.000,00").
- DATAS: a data de assinatura aparece no final do documento ou no log de assinatura eletrônica (Clicksign/D4Sign). A vigência/prazo aparece no quadro resumo ou cláusula de prazo.
- ASSINATURA ELETRÔNICA: no final do PDF há um bloco Clicksign ou D4Sign com hash SHA256, nomes dos signatários, datas e IPs.
- No TERMO DE RECEBIMENTO: o declarante aparece na primeira linha ("Eu, [nome] declaro..."), com CPF e data de recebimento.
- CONFIDENCIALIDADE: prazo em anos aparece na cláusula de vigência do NDA (ex: "5 (cinco) anos").

{
  "instrument_type": "prestacao_servico | termo_confidencialidade | termo_recebimento | parceria | terceirizacao | outro",
  "title_or_heading": "título exato do documento",
  "is_signed": true | false | null,
  "signature_date": "YYYY-MM-DD",
  "effective_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",

  "parties": [
    {
      "name": "razão social ou nome completo",
      "role": "contratante | contratado | confidenciante | confidenciado | divulgador | receptor | parceiro | terceirizado | outro",
      "cpf_cnpj": "apenas dígitos",
      "address_street": "logradouro com número",
      "address_complement": "complemento se houver",
      "address_neighborhood": "bairro",
      "address_city": "cidade",
      "address_state": "UF (2 letras)",
      "address_cep": "apenas 8 dígitos",
      "email": "email institucional da parte",
      "phone": "telefone se constar",
      "representative_name": "nome do representante legal",
      "representative_cpf": "apenas dígitos",
      "representative_rg": "número do RG",
      "representative_email": "email do representante se diferente"
    }
  ],

  "object_summary": "resumo do objeto",
  "contract_value": 3000.00,
  "payment_terms": "forma e prazo de pagamento",
  "late_fee_percent": 2.0,
  "penalty_percent": 20.0,
  "price_index": "índice de reajuste (ex: IGP-M)",

  "obligations_highlights": ["obrigação 1"],
  "confidentiality": true | false,
  "confidentiality_years": 5,
  "termination_clause": true | false,
  "governing_law_or_forum": "foro",

  "signing_city": "cidade de assinatura",
  "signing_platform": "clicksign | d4sign | fisico | outro",
  "signing_platform_id": "hash ou código do documento na plataforma",

  "project_coordinator": "nome do coordenador do projeto se constar",

  "delivery_description": "o que foi entregue (só para termo de recebimento)",
  "delivery_date": "YYYY-MM-DD (só para termo de recebimento)",
  "receipt_declarant": "nome de quem declara recebimento",

  "annexes_referenced": [],
  "comparison_tags": [],
  "notes": null
}

REGRAS OBRIGATÓRIAS:
- instrument_type: exatamente um dos valores listados.
- parties.role: exatamente um dos valores listados. Sempre no masculino. "DIVULGADORA" = "divulgador". "RECEPTORA" = "receptor".
- Todos os CPF, CNPJ e CEP: APENAS dígitos (remova pontos, traços e barras).
- contract_value e service_value: numérico com ponto decimal, sem R$, sem pontos de milhar.
- Datas em ISO YYYY-MM-DD.
- signing_platform: identifique pelo bloco de log no final do PDF (Clicksign ou D4Sign).
- Responda APENAS com o JSON.`;

async function analyzeOne() {
  let query = supabase
    .from("documents")
    .select("id, storage_bucket, storage_path, original_filename");

  if (TARGET_ID) {
    query = query.eq("id", TARGET_ID);
  } else if (FLAG_REANALYZE) {
    query = query.eq("status", "analyzed");
  } else {
    query = query.eq("status", "uploaded");
  }

  const { data: doc, error: fetchErr } = await query.limit(1).single();

  if (fetchErr || !doc) {
    console.log("Nenhum documento encontrado para processar.");
    return;
  }

  console.log(`Processando: ${doc.original_filename} (${doc.id})`);

  if (FLAG_REANALYZE || TARGET_ID) {
    await supabase.from("document_analysis").delete().eq("document_id", doc.id);
  }

  await supabase
    .from("documents")
    .update({ status: "processing", updated_at: new Date().toISOString() })
    .eq("id", doc.id);

  const { data: fileData, error: dlErr } = await supabase.storage
    .from(doc.storage_bucket)
    .download(doc.storage_path);

  if (dlErr || !fileData) {
    await markFailed(doc.id, `Download falhou: ${dlErr?.message}`);
    return;
  }

  const buffer = Buffer.from(await fileData.arrayBuffer());
  const pdfBase64 = buffer.toString("base64");
  const sizeMB = (buffer.length / 1024 / 1024).toFixed(1);
  console.log(`PDF baixado (${sizeMB} MB). Enviando para Claude...`);

  let message;
  try {
    message = await anthropic.messages.create({
      model: "claude-sonnet-4-20250514",
      max_tokens: 4096,
      system: SYSTEM_PROMPT,
      messages: [
        {
          role: "user",
          content: [
            {
              type: "document",
              source: {
                type: "base64",
                media_type: "application/pdf",
                data: pdfBase64,
              },
            },
            {
              type: "text",
              text: "Analise este documento jurídico e devolva o JSON conforme as instruções.",
            },
          ],
        },
      ],
    });
  } catch (apiErr) {
    await markFailed(doc.id, `Anthropic API: ${apiErr.message}`);
    return;
  }

  let rawText = message.content
    .filter((b) => b.type === "text")
    .map((b) => b.text)
    .join("");

  // Strip markdown fences (```json ... ```) if present
  rawText = rawText.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/i, "").trim();

  console.log("Resposta recebida. Parseando JSON...");

  let analysis;
  try {
    analysis = JSON.parse(rawText);
  } catch {
    await markFailed(doc.id, `JSON inválido: ${rawText.slice(0, 200)}`);
    return;
  }

  const { error: analysisErr } = await supabase
    .from("document_analysis")
    .insert({
      document_id: doc.id,
      instrument_type: analysis.instrument_type || null,
      is_signed: analysis.is_signed ?? null,
      signature_date: analysis.signature_date || null,
      effective_date: analysis.effective_date || null,
      end_date: analysis.end_date || null,
      service_value: analysis.contract_value ?? analysis.service_value ?? null,
      contract_value: analysis.contract_value ?? null,
      title_or_heading: analysis.title_or_heading || null,
      object_summary: analysis.object_summary || null,
      payment_terms: analysis.payment_terms || null,
      late_fee_percent: analysis.late_fee_percent ?? null,
      penalty_percent: analysis.penalty_percent ?? null,
      price_index: analysis.price_index || null,
      confidentiality_years: analysis.confidentiality_years ?? null,
      signing_city: analysis.signing_city || null,
      signing_platform: analysis.signing_platform || null,
      signing_platform_id: analysis.signing_platform_id || null,
      project_coordinator: analysis.project_coordinator || null,
      delivery_description: analysis.delivery_description || null,
      delivery_date: analysis.delivery_date || null,
      receipt_declarant: analysis.receipt_declarant || null,
      analysis_json: analysis,
      provider: "anthropic",
      model: message.model,
      prompt_version: "v3",
      raw_response: message,
    });

  if (analysisErr) {
    await markFailed(doc.id, `INSERT analysis: ${analysisErr.message}`);
    return;
  }

  console.log("document_analysis gravado.");

  if (Array.isArray(analysis.parties)) {
    for (const party of analysis.parties) {
      const clientId = await resolveClient(party);
      if (clientId) {
        await supabase.from("document_client_links").upsert(
          {
            document_id: doc.id,
            client_id: clientId,
            role_in_document: normalizeRole(party.role),
            source: "llm",
          },
          { onConflict: "document_id,client_id,role_in_document" }
        );
      }
    }
    console.log(`${analysis.parties.length} parte(s) vinculada(s).`);
  }

  await supabase
    .from("documents")
    .update({ status: "analyzed", updated_at: new Date().toISOString() })
    .eq("id", doc.id);

  console.log("Concluído. Status → analyzed.");
}

const VALID_ROLES = ["contratante", "contratado", "confidenciante", "confidenciado", "divulgador", "receptor", "parceiro", "terceirizado", "outro"];

const ROLE_ALIASES = {
  divulgadora: "divulgador",
  receptora: "receptor",
  confidenciada: "confidenciado",
  confidenciante: "confidenciante",
  contratada: "contratado",
};

function normalizeRole(raw) {
  if (!raw) return "outro";
  const lower = raw.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();
  if (ROLE_ALIASES[lower]) return ROLE_ALIASES[lower];
  if (lower.endsWith("a") && VALID_ROLES.includes(lower.slice(0, -1) + "o")) {
    return lower.slice(0, -1) + "o";
  }
  return VALID_ROLES.includes(lower) ? lower : "outro";
}

function normalizeCpfCnpj(raw) {
  if (!raw) return null;
  const digits = raw.replace(/\D/g, "");
  return digits.length >= 11 ? digits : null;
}

function buildClientPatch(party) {
  const cleanCep = party.address_cep ? party.address_cep.replace(/\D/g, "") : null;
  const patch = {};
  const fields = {
    address_street: party.address_street,
    address_number: party.address_number,
    address_complement: party.address_complement,
    address_neighborhood: party.address_neighborhood,
    address_city: party.address_city,
    address_state: party.address_state,
    address_cep: cleanCep,
    email: party.email,
    phone: party.phone,
    representative_name: party.representative_name,
    representative_cpf: normalizeCpfCnpj(party.representative_cpf),
    representative_rg: party.representative_rg,
    representative_email: party.representative_email,
  };
  for (const [k, v] of Object.entries(fields)) {
    if (v) patch[k] = v;
  }
  return Object.keys(patch).length ? patch : null;
}

async function resolveClient(party) {
  if (!party.name) return null;
  const normalized = party.name
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim();

  const cleanDoc = normalizeCpfCnpj(party.cpf_cnpj);

  if (cleanDoc) {
    const { data } = await supabase
      .from("clients")
      .select("id, address_street")
      .eq("cpf_cnpj", cleanDoc)
      .maybeSingle();
    if (data) {
      if (!data.address_street) {
        const patch = buildClientPatch(party);
        if (patch) await supabase.from("clients").update(patch).eq("id", data.id);
      }
      return data.id;
    }
  }

  const { data: byName } = await supabase
    .from("clients")
    .select("id, address_street")
    .eq("name_normalized", normalized)
    .maybeSingle();
  if (byName) {
    if (!byName.address_street) {
      const patch = buildClientPatch(party);
      if (patch) await supabase.from("clients").update(patch).eq("id", byName.id);
    }
    return byName.id;
  }

  const clientType = cleanDoc
    ? cleanDoc.length === 14 ? "pj" : cleanDoc.length === 11 ? "pf" : null
    : null;

  const cleanCep = party.address_cep ? party.address_cep.replace(/\D/g, "") : null;

  const { data: created, error } = await supabase
    .from("clients")
    .insert({
      legal_name: party.name,
      name_normalized: normalized,
      cpf_cnpj: cleanDoc,
      client_type: clientType,
      address_street: party.address_street || null,
      address_number: party.address_number || null,
      address_complement: party.address_complement || null,
      address_neighborhood: party.address_neighborhood || null,
      address_city: party.address_city || null,
      address_state: party.address_state || null,
      address_cep: cleanCep,
      email: party.email || null,
      phone: party.phone || null,
      representative_name: party.representative_name || null,
      representative_cpf: normalizeCpfCnpj(party.representative_cpf) || null,
      representative_rg: party.representative_rg || null,
      representative_email: party.representative_email || null,
    })
    .select("id")
    .single();

  if (error) {
    console.error(`Erro ao criar client "${party.name}":`, error.message);
    return null;
  }
  console.log(`Cliente criado: "${party.name}" → ${created.id}`);
  return created.id;
}

async function markFailed(docId, msg) {
  console.error("FALHA:", msg);
  await supabase
    .from("documents")
    .update({
      status: "failed",
      error_message: msg,
      updated_at: new Date().toISOString(),
    })
    .eq("id", docId);
}

analyzeOne().catch((err) => {
  console.error(err);
  process.exit(1);
});
