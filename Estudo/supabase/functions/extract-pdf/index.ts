import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

const SYSTEM_PROMPT = `Voce e um assistente juridico especializado em contratos brasileiros.

ONDE ENCONTRAR CADA INFORMACAO:
- O TIPO do documento esta no titulo/cabecalho (ex: "CONTRATO DE PRESTACAO DE SERVICOS", "TERMO DE CONFIDENCIALIDADE", "TERMO DE RECEBIMENTO").
- As PARTES estao no paragrafo de qualificacao logo apos o titulo, iniciando com "Pelo presente instrumento particular" ou similar. Cada parte traz: razao social ou nome completo, endereco com CEP, CNPJ ou CPF, representante legal (nome, RG, CPF, endereco, email). Atencao: "doravante denominada CONTRATADA/CONTRATANTE/DIVULGADORA/RECEPTORA" indica o papel.
- O QUADRO RESUMO (em contratos de prestacao de servico) contem: objeto, vigencia, valor, prazo de pagamento, reajuste, multa de mora, multa penal, comunicacao, anexos.
- VALORES aparecem no quadro resumo e na clausula de pagamento (ex: "R$3.000,00").
- DATAS: a data de assinatura aparece no final do documento ou no log de assinatura eletronica (Clicksign/D4Sign). A vigencia/prazo aparece no quadro resumo ou clausula de prazo.
- ASSINATURA ELETRONICA: no final do PDF ha um bloco Clicksign ou D4Sign com hash SHA256, nomes dos signatarios, datas e IPs.
- No TERMO DE RECEBIMENTO: o declarante aparece na primeira linha ("Eu, [nome] declaro..."), com CPF e data de recebimento.
- CONFIDENCIALIDADE: prazo em anos aparece na clausula de vigencia do NDA (ex: "5 (cinco) anos").

REGRAS OBRIGATORIAS:
- parties.role: exatamente um dos valores permitidos. Sempre no masculino.
- Todos os CPF, CNPJ e CEP: APENAS digitos, sem pontuacao.
- contract_value: numerico com ponto decimal, sem R$, sem pontos de milhar.
- Datas em ISO YYYY-MM-DD.
- signing_platform: identifique pelo bloco de log no final do PDF (Clicksign ou D4Sign).
- Use null para campos ausentes no documento.`;

const CONTRACT_TOOL = {
  name: "salvar_contrato",
  description: "Salva os dados extraidos do documento juridico brasileiro.",
  input_schema: {
    type: "object",
    properties: {
      instrument_type: {
        type: "string",
        enum: ["prestacao_servico", "termo_confidencialidade", "termo_recebimento", "parceria", "terceirizacao", "outro"],
      },
      title_or_heading:  { type: ["string", "null"] },
      is_signed:         { type: ["boolean", "null"] },
      signature_date:    { type: ["string", "null"], description: "YYYY-MM-DD" },
      effective_date:    { type: ["string", "null"], description: "YYYY-MM-DD" },
      end_date:          { type: ["string", "null"], description: "YYYY-MM-DD" },
      parties: {
        type: "array",
        items: {
          type: "object",
          properties: {
            name:                 { type: "string" },
            role:                 { type: "string", enum: ["contratante", "contratado", "confidenciante", "confidenciado", "divulgador", "receptor", "parceiro", "terceirizado", "outro"] },
            cpf_cnpj:             { type: ["string", "null"] },
            address_street:       { type: ["string", "null"] },
            address_complement:   { type: ["string", "null"] },
            address_neighborhood: { type: ["string", "null"] },
            address_city:         { type: ["string", "null"] },
            address_state:        { type: ["string", "null"] },
            address_cep:          { type: ["string", "null"] },
            email:                { type: ["string", "null"] },
            phone:                { type: ["string", "null"] },
            representative_name:  { type: ["string", "null"] },
            representative_cpf:   { type: ["string", "null"] },
            representative_rg:    { type: ["string", "null"] },
            representative_email: { type: ["string", "null"] },
          },
          required: ["name", "role"],
        },
      },
      object_summary:          { type: ["string", "null"] },
      contract_value:          { type: ["number", "null"] },
      payment_terms:           { type: ["string", "null"] },
      late_fee_percent:        { type: ["number", "null"] },
      penalty_percent:         { type: ["number", "null"] },
      price_index:             { type: ["string", "null"] },
      confidentiality:         { type: ["boolean", "null"] },
      confidentiality_years:   { type: ["number", "null"] },
      termination_clause:      { type: ["boolean", "null"] },
      governing_law_or_forum:  { type: ["string", "null"] },
      signing_city:            { type: ["string", "null"] },
      signing_platform:        { type: ["string", "null"], enum: ["clicksign", "d4sign", "fisico", "outro"] },
      signing_platform_id:     { type: ["string", "null"] },
      project_coordinator:     { type: ["string", "null"] },
      delivery_description:    { type: ["string", "null"] },
      delivery_date:           { type: ["string", "null"], description: "YYYY-MM-DD" },
      receipt_declarant:       { type: ["string", "null"] },
      annexes_referenced:      { type: "array", items: { type: "string" } },
      notes:                   { type: ["string", "null"] },
    },
    required: ["instrument_type", "parties"],
  },
};

const VALID_ROLES = ["contratante", "contratado", "confidenciante", "confidenciado", "divulgador", "receptor", "parceiro", "terceirizado", "outro"];
const ROLE_ALIASES: Record<string, string> = {
  divulgadora: "divulgador",
  receptora: "receptor",
  confidenciada: "confidenciado",
  contratada: "contratado",
};

function normalizeRole(raw: string | null): string {
  if (!raw) return "outro";
  const lower = raw.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();
  if (ROLE_ALIASES[lower]) return ROLE_ALIASES[lower];
  if (lower.endsWith("a") && VALID_ROLES.includes(lower.slice(0, -1) + "o")) {
    return lower.slice(0, -1) + "o";
  }
  return VALID_ROLES.includes(lower) ? lower : "outro";
}

function normalizeCpfCnpj(raw: string | null): string | null {
  if (!raw) return null;
  const digits = raw.replace(/\D/g, "");
  return digits.length >= 11 ? digits : null;
}

function buildClientPatch(party: Record<string, unknown>): Record<string, unknown> | null {
  const cleanCep = party.address_cep ? String(party.address_cep).replace(/\D/g, "") : null;
  const patch: Record<string, unknown> = {};
  const fields: Record<string, unknown> = {
    address_street: party.address_street,
    address_complement: party.address_complement,
    address_neighborhood: party.address_neighborhood,
    address_city: party.address_city,
    address_state: party.address_state,
    address_cep: cleanCep,
    email: party.email,
    phone: party.phone,
    representative_name: party.representative_name,
    representative_cpf: normalizeCpfCnpj(party.representative_cpf as string),
    representative_rg: party.representative_rg,
    representative_email: party.representative_email,
  };
  for (const [k, v] of Object.entries(fields)) {
    if (v) patch[k] = v;
  }
  return Object.keys(patch).length ? patch : null;
}

async function resolveClient(
  supabase: ReturnType<typeof createClient>,
  party: Record<string, unknown>
): Promise<string | null> {
  if (!party.name) return null;

  const normalized = String(party.name)
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim();

  const cleanDoc = normalizeCpfCnpj(party.cpf_cnpj as string);

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
  const cleanCep = party.address_cep ? String(party.address_cep).replace(/\D/g, "") : null;

  const { data: created, error } = await supabase
    .from("clients")
    .insert({
      legal_name: party.name,
      name_normalized: normalized,
      cpf_cnpj: cleanDoc,
      client_type: clientType,
      address_street: party.address_street ?? null,
      address_complement: party.address_complement ?? null,
      address_neighborhood: party.address_neighborhood ?? null,
      address_city: party.address_city ?? null,
      address_state: party.address_state ?? null,
      address_cep: cleanCep,
      email: party.email ?? null,
      phone: party.phone ?? null,
      representative_name: party.representative_name ?? null,
      representative_cpf: normalizeCpfCnpj(party.representative_cpf as string),
      representative_rg: party.representative_rg ?? null,
      representative_email: party.representative_email ?? null,
    })
    .select("id")
    .single();

  if (error) {
    console.error(`Erro ao criar client "${party.name}":`, error.message);
    return null;
  }
  console.log(`Cliente criado: "${party.name}" -> ${created.id}`);
  return created.id;
}

async function markFailed(
  supabase: ReturnType<typeof createClient>,
  docId: string,
  msg: string
) {
  console.error("FALHA:", msg);
  await supabase
    .from("documents")
    .update({ status: "failed", error_message: msg, updated_at: new Date().toISOString() })
    .eq("id", docId);
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
  );
  const anthropicKey = Deno.env.get("ANTHROPIC_API_KEY")!;

  try {
    const body = await req.json();

    // Suporte a webhook (INSERT em documents) e chamada direta ({ document_id })
    let docId: string;
    let doc: Record<string, unknown>;

    if (body.type === "INSERT" && body.record) {
      // Disparado pelo Database Webhook
      if (body.record.status !== "uploaded") {
        return new Response(JSON.stringify({ skipped: true }), {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      doc = body.record;
      docId = doc.id as string;
    } else if (body.document_id || body.id) {
      // Chamada direta para reanalise
      docId = body.document_id ?? body.id;
      const { data, error } = await supabase
        .from("documents")
        .select("*")
        .eq("id", docId)
        .single();
      if (error || !data) {
        return new Response(JSON.stringify({ error: "Documento nao encontrado" }), {
          status: 404,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      doc = data;
      // Para reanalise, remove analise anterior
      await supabase.from("document_analysis").delete().eq("document_id", docId);
    } else {
      return new Response(JSON.stringify({ error: "Payload invalido" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    console.log(`Processando: ${doc.original_filename} (${docId})`);

    await supabase
      .from("documents")
      .update({ status: "processing", updated_at: new Date().toISOString() })
      .eq("id", docId);

    // Download do PDF
    const { data: fileData, error: dlErr } = await supabase.storage
      .from(doc.storage_bucket as string)
      .download(doc.storage_path as string);

    if (dlErr || !fileData) {
      await markFailed(supabase, docId, `Download falhou: ${dlErr?.message}`);
      return new Response(JSON.stringify({ error: "Download falhou" }), {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const buffer = await fileData.arrayBuffer();
    const uint8 = new Uint8Array(buffer);
    const pdfBase64 = btoa(uint8.reduce((d, b) => d + String.fromCharCode(b), ""));
    const sizeMB = (buffer.byteLength / 1024 / 1024).toFixed(1);
    console.log(`PDF baixado (${sizeMB} MB). Enviando para Claude...`);

    // Chamada ao Claude com Tool Use
    const claudeRes = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": anthropicKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: "claude-sonnet-4-20250514",
        max_tokens: 4096,
        system: SYSTEM_PROMPT,
        tools: [CONTRACT_TOOL],
        tool_choice: { type: "tool", name: "salvar_contrato" },
        messages: [
          {
            role: "user",
            content: [
              {
                type: "document",
                source: { type: "base64", media_type: "application/pdf", data: pdfBase64 },
              },
              {
                type: "text",
                text: "Analise este documento juridico e extraia os dados usando a ferramenta salvar_contrato.",
              },
            ],
          },
        ],
      }),
    });

    if (!claudeRes.ok) {
      const errText = await claudeRes.text();
      await markFailed(supabase, docId, `Anthropic API ${claudeRes.status}: ${errText.slice(0, 200)}`);
      return new Response(JSON.stringify({ error: "Erro na API Claude" }), {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const claudeBody = await claudeRes.json();
    console.log("Resposta recebida. Extraindo tool_use...");

    const toolUseBlock = claudeBody.content?.find(
      (b: { type: string }) => b.type === "tool_use"
    );

    if (!toolUseBlock) {
      await markFailed(supabase, docId, `Tool use ausente na resposta: ${JSON.stringify(claudeBody.content).slice(0, 200)}`);
      return new Response(JSON.stringify({ error: "Tool use ausente" }), {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const analysis: Record<string, unknown> = toolUseBlock.input;

    const { error: analysisErr } = await supabase.from("document_analysis").insert({
      document_id: docId,
      instrument_type: analysis.instrument_type ?? null,
      is_signed: analysis.is_signed ?? null,
      signature_date: analysis.signature_date ?? null,
      effective_date: analysis.effective_date ?? null,
      end_date: analysis.end_date ?? null,
      service_value: (analysis.contract_value ?? analysis.service_value) ?? null,
      contract_value: analysis.contract_value ?? null,
      title_or_heading: analysis.title_or_heading ?? null,
      object_summary: analysis.object_summary ?? null,
      payment_terms: analysis.payment_terms ?? null,
      late_fee_percent: analysis.late_fee_percent ?? null,
      penalty_percent: analysis.penalty_percent ?? null,
      price_index: analysis.price_index ?? null,
      confidentiality_years: analysis.confidentiality_years ?? null,
      signing_city: analysis.signing_city ?? null,
      signing_platform: analysis.signing_platform ?? null,
      signing_platform_id: analysis.signing_platform_id ?? null,
      project_coordinator: analysis.project_coordinator ?? null,
      delivery_description: analysis.delivery_description ?? null,
      delivery_date: analysis.delivery_date ?? null,
      receipt_declarant: analysis.receipt_declarant ?? null,
      analysis_json: analysis,
      provider: "anthropic",
      model: claudeBody.model,
      prompt_version: "v4",
      raw_response: claudeBody,
    });

    if (analysisErr) {
      await markFailed(supabase, docId, `INSERT analysis: ${analysisErr.message}`);
      return new Response(JSON.stringify({ error: analysisErr.message }), {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    console.log("document_analysis gravado.");

    if (Array.isArray(analysis.parties)) {
      for (const party of analysis.parties as Record<string, unknown>[]) {
        const clientId = await resolveClient(supabase, party);
        if (clientId) {
          await supabase.from("document_client_links").upsert(
            {
              document_id: docId,
              client_id: clientId,
              role_in_document: normalizeRole(party.role as string),
              source: "llm",
            },
            { onConflict: "document_id,client_id,role_in_document" }
          );
        }
      }
      console.log(`${(analysis.parties as unknown[]).length} parte(s) vinculada(s).`);
    }

    await supabase
      .from("documents")
      .update({ status: "analyzed", updated_at: new Date().toISOString() })
      .eq("id", docId);

    console.log("Concluido. Status -> analyzed.");

    return new Response(JSON.stringify({ id: docId, status: "analyzed" }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: String(err) }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
