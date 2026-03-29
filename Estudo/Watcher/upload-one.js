const fs = require("fs");
const path = require("path");
const { createClient } = require("@supabase/supabase-js");
require("dotenv").config();

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const BUCKET = "documents-incoming";
const INBOX = process.env.WATCH_DIR;
const UPLOADED = process.env.UPLOADED_DIR;

if (!SUPABASE_URL || !SUPABASE_KEY) {
  console.error("Preencha SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no .env");
  process.exit(1);
}

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

async function uploadOne() {
  const files = fs
    .readdirSync(INBOX)
    .filter((f) => f.toLowerCase().endsWith(".pdf"));

  if (files.length === 0) {
    console.log("Nenhum PDF encontrado em", INBOX);
    return;
  }

  const filename = files[0];
  const localPath = path.join(INBOX, filename);
  const fileBuffer = fs.readFileSync(localPath);
  const sizeBytes = fs.statSync(localPath).size;

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const safeName = filename.replace(/[^a-zA-Z0-9._-]/g, "_");
  const storagePath = `inbox/${timestamp}_${safeName}`;

  console.log(`Enviando "${filename}" (${(sizeBytes / 1024).toFixed(0)} KB)...`);

  const { error: uploadError } = await supabase.storage
    .from(BUCKET)
    .upload(storagePath, fileBuffer, {
      contentType: "application/pdf",
      upsert: false,
    });

  if (uploadError) {
    console.error("Erro no upload:", uploadError.message);
    process.exit(1);
  }

  console.log("Upload OK →", storagePath);

  const { data, error: insertError } = await supabase
    .from("documents")
    .insert({
      storage_bucket: BUCKET,
      storage_path: storagePath,
      original_filename: filename,
      mime_type: "application/pdf",
      size_bytes: sizeBytes,
      status: "uploaded",
    })
    .select("id")
    .single();

  if (insertError) {
    console.error("Erro no INSERT:", insertError.message);
    process.exit(1);
  }

  console.log("Registro criado → documents.id =", data.id);

  if (UPLOADED) {
    const dest = path.join(UPLOADED, filename);
    fs.renameSync(localPath, dest);
    console.log("Movido para", dest);
  }

  console.log("Concluído.");
}

uploadOne().catch((err) => {
  console.error(err);
  process.exit(1);
});
