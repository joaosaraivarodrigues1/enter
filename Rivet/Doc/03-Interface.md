# Overview da Interface

> Fonte: https://rivet.ironcladapp.com/docs/user-guide/overview-of-interface

## Sidebar (Painel Lateral)

### Aba Project Info

- Definir nome e descrição do projeto
- Dados salvos no arquivo `.rivet-project`
- Configurar plugins habilitados para o projeto

### Aba Graphs

- Navegar entre todos os grafos do projeto
- Adicionar novos grafos (clique direito > "New Graph")
- Deletar grafos (clique direito > "Delete Graph") — **não há undo!**
- Duplicar grafos (clique direito > "Duplicate Graph")
- Clicar num grafo abre-o na área principal

### Aba Graph Info

- Definir nome e descrição do grafo atual
- Usado para documentação e organização

## Área do Grafo (Canvas)

A área principal de trabalho contém todos os nodes e conexões do grafo atual.

### Navegação

- **Arrastar** no canvas para mover a visualização
- **Scroll** para zoom in/out
- **Clique direito** abre menu de contexto para adicionar nodes
- **Shift + arrastar** cria caixa de seleção para selecionar múltiplos nodes
- **Shift + clique** no título de um node para adicioná-lo à seleção

### Nodes no Canvas

Cada node exibe:
- Título
- Portas de entrada (esquerda)
- Portas de saída (direita)
- Dados de output após execução
- Ícone de engrenagem para editar

## Editor de Node

Visível ao clicar no ícone de edição (engrenagem) de um node. Permite editar os dados do node.

### Fechar o Editor

- Botão de fechar (X)
- Tecla Escape
- Clicar em espaço vazio no grafo

### Título e Descrição

Editar o título (mostrado no grafo) e a descrição do node (para documentação).

### Split Node

Toggle para ativar splitting (execução paralela). Quando ativado, aparece um campo numérico para o limite máximo de splits.

Ver [08-Splitting.md](./08-Splitting.md) para detalhes.

### Variantes

Variantes permitem criar múltiplas versões do mesmo node para testes A/B:

- **Salvar variante** — botão à direita salva a configuração atual como nova variante
- **Aplicar variante** — dropdown à esquerda aplica uma variante existente

Útil para testar diferentes mensagens/prompts e ver qual performa melhor.

### Editor de Dados do Node

Área que contém os editores específicos do tipo de node selecionado. Ex:
- Text Node → editor de texto
- Chat Node → editor de configuração de chat
- Code Node → editor de código JavaScript

## Overlays (Painéis Superiores)

### Prompt Designer

Permite ajustar um prompt individual para obter o output desejado.

### Trivet Tests

Configurar suítes de testes e casos de teste para o projeto.

### Chat Viewer

Visão em tela cheia de todos os Chat nodes executados ou em progresso. Útil para:
- Visão geral rápida do comportamento da IA
- Debug de problemas

## Barra de Ações (Action Bar)

Localizada no canto superior direito.

| Botão | Função |
|-------|--------|
| **Run** | Executa o grafo atual |
| **Abort** | Aborta a execução (visível durante execução) |
| **Pause/Resume** | Pausa/retoma a execução (visível durante execução) |
| **Menu (...)** | Acessa o menu principal do Rivet |

### Menu Principal

Contém opções como:
- Salvar/Abrir projeto
- Configurações
- Remote Debugger
- Seleção de Executor (Browser, Node, Remote)
- Load Recording
