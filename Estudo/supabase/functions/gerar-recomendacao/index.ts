import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

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

    // Inserir job na tabela
    const { data: rec, error: errRec } = await supabase
      .from("recomendacoes")
      .insert({ cliente_id, mes, status: "processing" })
      .select("job_id")
      .single();
    if (errRec) throw new Error(`insertJob: ${errRec.message}`);

    const job_id = rec.job_id;

    // Disparar Railway com payload minimo
    const rivetUrl = Deno.env.get("RIVET_SERVER_URL")!;
    await fetch(rivetUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id, cliente_id, mes_referencia: mes }),
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
