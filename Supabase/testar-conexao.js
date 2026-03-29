const { supabase } = require("./client");

async function testar() {
  const { data, error } = await supabase.from("clientes").select("*").limit(1);

  if (error) {
    console.error("Erro:", error.message);
  } else {
    console.log("Conexão OK. Resposta:", data);
  }
}

testar();
