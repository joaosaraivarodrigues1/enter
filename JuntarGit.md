# Plano — Consolidar 3 repos em 1 (enter)

## Situacao atual

| Pasta | GitHub | Servico |
|---|---|---|
| `Enter/` | `enter` | backup geral |
| `Enter/Rivet/` | `enter-rivet-server` | Railway (producao) |
| `Enter/Streamlit/Enter1/` | `Enter1` | Streamlit Cloud (producao) |

## Ordem de execucao

Streamlit primeiro (menos critico), Railway depois.

---

## PARTE 1 — Streamlit (Enter1)

### 1. Git: absorver Enter1 no repo enter

```bash
# Remover .git do Enter1 (perde historico, codigo preservado)
rm -rf "Streamlit/Enter1/.git"

# Atualizar .gitignore: remover linha Streamlit/Enter1/
# Adicionar e commitar
git add Streamlit/Enter1/
git commit -m "feat: absorver Streamlit/Enter1 no monorepo"
git push
```

### 2. Reconfigurar Streamlit Cloud (manual)

1. Acessar https://share.streamlit.io
2. Abrir o app do Enter1
3. Settings -> General
4. Trocar repositorio: `joaosaraivarodrigues1/Enter1` -> `joaosaraivarodrigues1/enter`
5. Branch: `main`
6. Main file path: `Streamlit/Enter1/streamlit_app.py`
7. Salvar e aguardar redeploy
8. Confirmar que o app esta funcionando

### 3. Arquivar repo antigo (manual)

1. Acessar https://github.com/joaosaraivarodrigues1/Enter1
2. Settings -> Danger Zone -> Archive repository

---

## PARTE 2 — Railway (Rivet)

### 1. Git: absorver Rivet no repo enter

```bash
# Remover .git do Rivet (perde historico, codigo preservado)
rm -rf "Rivet/.git"

# Atualizar .gitignore: remover linha Rivet/
git add Rivet/
git commit -m "feat: absorver Rivet no monorepo"
git push
```

### 2. Reconfigurar Railway (manual)

1. Acessar https://railway.app -> projeto enter-rivet-server
2. Service -> Settings -> Source
3. Trocar repo: `enter-rivet-server` -> `enter`
4. Configurar Root Directory: `Rivet`
5. Confirmar redeploy automatico
6. Testar: `GET https://enter-rivet-server-production.up.railway.app/health`

### 3. Arquivar repo antigo (manual)

1. Acessar https://github.com/joaosaraivarodrigues1/enter-rivet-server
2. Settings -> Danger Zone -> Archive repository

---

## Resultado final

- 1 repo: `enter`
- Railway faz deploy de `Rivet/` via Root Directory
- Streamlit faz deploy de `Streamlit/Enter1/` via main file path
- Qualquer mudanca em qualquer parte: 1 unico git push
