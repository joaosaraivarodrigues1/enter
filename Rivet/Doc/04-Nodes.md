# Trabalhando com Nodes

> Fonte: https://rivet.ironcladapp.com/docs/user-guide/adding-connecting-nodes

## Adicionar Nodes

1. **Clique direito** em espaço vazio no grafo (ou pressione **Espaço**)
2. O menu "Add" será exibido
3. Digitar para buscar um node pelo nome
4. Nodes são agrupados por categoria
5. Selecionar um node adiciona-o ao grafo na posição do clique

Referência completa de todos os nodes disponíveis: [06-Referencia-Nodes.md](./06-Referencia-Nodes.md)

## Mover Nodes

- **Arrastar** na barra de título de um node para movê-lo
- **Shift + clique** nas barras de título de múltiplos nodes para selecioná-los
- Arrastar move todos os nodes selecionados como grupo

## Deletar Nodes

- **Clique direito** no node > "Delete"
- **Não há undo!** A exclusão é permanente

## Conectar Nodes

Nodes são conectados arrastando de uma porta (port) de um node para a porta de outro.

### Regras de Conexão

| Regra | Descrição |
|-------|-----------|
| **Portas de entrada** | Ficam no **lado esquerdo** do node |
| **Portas de saída** | Ficam no **lado direito** do node |
| **Output → múltiplos Inputs** | Uma porta de saída pode conectar a múltiplas portas de entrada |
| **Input ← único Output** | Uma porta de entrada só pode receber uma conexão |

### Tipos de Dados

Cada porta tem um tipo de dado esperado. Os tipos de dados disponíveis estão documentados em [10-DataTypes.md](./10-DataTypes.md).

## Desconectar Nodes

- **Arrastar** uma conexão existente para outra porta para mover a conexão
- **Arrastar** uma conexão para um espaço vazio para deletar a conexão

## Criar Subgrafo

1. Selecionar múltiplos nodes (Shift + clique nas barras de título)
2. Clique direito na seleção > "Create Subgraph"
3. Um novo grafo (não salvo!) será criado com:
   - Os nodes selecionados
   - Nodes de entrada/saída adicionais para conectar ao grafo pai
4. **Importante:** Dar nome e descrição ao subgrafo em Graph Info
5. **Importante:** Salvar o novo grafo (Ctrl+S / Cmd+S)
6. Os nodes originais **não** são removidos do grafo pai — é responsabilidade do usuário substituí-los pelo novo subgrafo

## Editar um Node

- Clicar no **ícone de engrenagem** no canto superior direito do node
- Abre o **Node Editor** (ver [03-Interface.md](./03-Interface.md))
- Cada tipo de node tem editores específicos para seus dados
