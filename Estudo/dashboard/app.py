import os
import streamlit as st
import requests
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "Watcher", ".env"))

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_failed_documents():
    res = (
        get_supabase()
        .table("documents")
        .select("id, original_filename, error_message, updated_at")
        .eq("status", "failed")
        .order("updated_at", desc=True)
        .execute()
    )
    return res.data or []


def reanalyze_document(doc_id: str) -> tuple[bool, str]:
    url = f"{SUPABASE_URL}/functions/v1/extract-pdf"
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, json={"document_id": doc_id}, headers=headers, timeout=180)
        if resp.ok:
            return True, "Reanálise concluída com sucesso."
        return False, f"Erro {resp.status_code}: {resp.text[:200]}"
    except requests.exceptions.Timeout:
        return False, "Timeout: a reanálise demorou mais de 3 minutos."
    except Exception as e:
        return False, str(e)


# ── Page setup ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Dashboard de Documentos", layout="wide")
st.title("Documentos com Erro")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Configure SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no arquivo Watcher/.env")
    st.stop()

# ── Refresh button ───────────────────────────────────────────────────────────
col_title, col_refresh = st.columns([8, 1])
with col_refresh:
    if st.button("Atualizar"):
        st.cache_data.clear()
        st.rerun()

# ── Load documents ───────────────────────────────────────────────────────────
with st.spinner("Carregando documentos com falha..."):
    docs = fetch_failed_documents()

if not docs:
    st.success("Nenhum documento com erro encontrado.")
    st.stop()

st.caption(f"{len(docs)} documento(s) com status **failed**")

# ── Document list ─────────────────────────────────────────────────────────────
for doc in docs:
    doc_id = doc["id"]
    filename = doc.get("original_filename") or doc_id
    error_msg = doc.get("error_message") or "Erro desconhecido"
    updated = doc.get("updated_at", "")[:19].replace("T", " ") if doc.get("updated_at") else ""

    with st.container(border=True):
        col_info, col_btn = st.columns([5, 1])

        with col_info:
            st.markdown(f"**{filename}**")
            st.caption(f"ID: `{doc_id}`  •  Atualizado: {updated}")
            st.error(error_msg, icon="🔴")

        with col_btn:
            st.write("")  # vertical alignment spacer
            if st.button("Reanalisar", key=f"reanalyze_{doc_id}", use_container_width=True):
                with st.spinner(f"Reanalysando {filename}..."):
                    ok, message = reanalyze_document(doc_id)
                if ok:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
