# Grafos, Subgrafos e Projetos

> Fonte: https://rivet.ironcladapp.com/docs/user-guide/subgraphs

## Conceito

Em Rivet, um **projeto** contém múltiplos **grafos**. Cada grafo é como uma função:

| Conceito Rivet | Analogia em Código |
|----------------|--------------------|
| Grafo | Função |
| Subgrafo | Chamada de função |
| Graph Input Node | Parâmetros da função |
| Graph Output Node | Valor de retorno |

Um grafo pode retornar múltiplos valores (múltiplos Graph Output Nodes).

## Projetos

- Um projeto é um arquivo `.rivet-project` que contém todos os grafos
- O projeto armazena nome, descrição e configurações de plugins
- **Recomendação:** armazenar projetos em controle de versão (Git)
- Um grafo pode ser marcado como "Main Graph" (grafo principal para execução)

## Grafos

### Criar um Novo Grafo

1. Na aba **Graphs** da sidebar, clique direito em espaço vazio
2. Selecione "New Graph"
3. Configure nome e descrição na aba **Graph Info**

### Deletar um Grafo

- Clique direito no grafo > "Delete Graph"
- **Não há undo!** A exclusão é permanente

### Duplicar um Grafo

- Clique direito no grafo > "Duplicate Graph"
- Cria uma cópia com os mesmos nodes e conexões

## Subgrafos

Subgrafos permitem compor grafos juntos, criando componentes reutilizáveis e grafos mais fáceis de entender.

### Criar um Subgrafo

1. Criar um novo grafo no projeto
2. Adicionar **Graph Input Nodes** para definir as entradas
3. Adicionar **Graph Output Nodes** para definir as saídas
4. Construir a lógica interna com outros nodes

### Criar Subgrafo a partir de Seleção

1. Selecionar múltiplos nodes (Shift + clique)
2. Clique direito > "Create Subgraph"
3. Um novo grafo é criado com os nodes selecionados + nodes de Input/Output
4. Os nodes originais não são removidos do grafo pai

### Chamar um Subgrafo

1. Adicionar um **Subgraph Node** ao grafo
2. Selecionar o grafo alvo no editor do node
3. As portas de entrada/saída são atualizadas automaticamente para corresponder ao subgrafo selecionado
4. Conectar os dados necessários às portas de entrada
5. Usar as portas de saída para continuar o fluxo

### Hierarquia de Subgrafos

- Subgrafos podem chamar outros subgrafos (hierarquia de profundidade qualquer)
- Um grafo pode chamar a si mesmo como subgrafo (recursão)
- **Cuidado:** evitar loops infinitos em chamadas recursivas!

## Graph Input Node

Define uma entrada para um grafo:

- Quando chamado via SDK: corresponde a um valor de input passado programaticamente
- Quando usado como subgrafo: torna-se uma porta de entrada no Subgraph Node

**Configurações:**
- `ID` — identificador único da entrada
- `Data Type` — tipo de dado esperado

## Graph Output Node

Define uma saída do grafo:

- Cada instância representa uma saída individual
- Quando usado como subgrafo: torna-se uma porta de saída no Subgraph Node
- O valor passado para o Graph Output torna-se parte do output geral do grafo

**Configurações:**
- `ID` — identificador único da saída
- `Data Type` — tipo de dado da saída
