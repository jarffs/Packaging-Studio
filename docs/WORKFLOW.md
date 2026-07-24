# Workflow Detalhado — Packaging Studio

Este documento detalha o workflow técnico completo do addon, desde a importação do arquivo até a animação final.

---

## Visão Geral do Pipeline

```
┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────────┐    ┌───────────┐
│  Arquivo │───▶│  Parser      │───▶│ Classificador│───▶│ Gerador 3D  │───▶│ Animador  │
│ SVG/PDF  │    │ svg/pdf→paths│    │ heurística   │    │ mesh+armature│   │ keyframes │
└──────────┘    └──────────────┘    └──────────────┘    └─────────────┘    └───────────┘
                      │                    │                   │                 │
                      ▼                    ▼                   ▼                 ▼
                 Estrutura de        Linhas rotuladas     Objetos Blender    Animação
                 paths interna      (corte/dobra/aba)    (mesh + bones)     pronta
```

---

## 1. Importação (Parser)

### 1.1 Entrada SVG
O SVG é processado com `xml.etree.ElementTree` (biblioteca padrão do Python, sem dependências externas). O parser extrai:
- Todos os elementos `<path>`, `<line>`, `<polyline>`, `<polygon>`, `<rect>`, `<circle>`, `<ellipse>`
- Atributos de transformação (`transform`) acumulados hierarquicamente
- Metadados de layer/grupo (`<g>`) e IDs
- Estilos inline e CSS (cor, stroke, dash-array)

```python
# Estrutura interna gerada pelo parser (core/types.py)
DielinePath:
    points: list[tuple[float, float]]  # Coordenadas 2D dos pontos
    is_closed: bool                    # Se o path forma um polígono fechado
    stroke: StrokeStyle                # Cor, largura, dashed
    element_id: str                    # ID do elemento SVG
    group: str | None                  # Nome do grupo/layer pai
    source_index: int                  # Ordem no documento
```

### 1.2 Entrada PDF
Arquivos PDF passam por uma conversão prévia:
1. `pymupdf` abre o PDF e extrai a primeira página (ou página selecionável pelo usuário)
2. Cada path vetorial é convertido para o equivalente SVG
3. O resultado entra no mesmo pipeline do parser SVG

---

## 2. Classificação (Line Classifier)

A heurística de classificação opera em 3 passes:

### Pass 1 — Análise Topológica
Identifica o **contorno externo** da faca:
- Calcula o convex hull de todos os pontos
- Encontra o polígono fechado com maior área → contorno de corte principal
- Linhas que fazem parte desse contorno são marcadas como **CORTE**

### Pass 2 — Classificação de Linhas Internas
Para cada linha que não faz parte do contorno:
- **É segmento reto e conecta dois pontos do contorno?** → Linha de **DOBRA**
- **É paralela a uma aresta do contorno e está próxima?** → Possível **VINCO** ou aba
- **Forma um path fechado pequeno interno?** → **CORTE ESPECIAL** (janela/furo)
- **Está em um trecho estreito e trapezoidal?** → Aba de **COLAGEM**

### Pass 3 — Refinamento
- Verifica consistência: uma linha de dobra deve ter painéis em ambos os lados
- Aplica regras de domínio: abas de colagem geralmente são mais estreitas que 15% da largura do painel adjacente
- Resolve ambiguidades usando proximidade e paralelismo

```python
# Resultado da classificação
ClassifiedLine:
    path: DielinePath
    line_type: LineType  # CUT | FOLD | SCORE | GLUE_FLAP | WINDOW
    confidence: float    # 0.0–1.0 (confiança da heurística)
    connected_panels: list[int]  # IDs dos painéis adjacentes
```

### Feedback Visual
Cada tipo de linha recebe uma cor no viewport para validação visual:
```
CUT        → (1.0, 0.0, 0.0, 1.0)  # Vermelho
FOLD       → (0.0, 0.4, 1.0, 1.0)  # Azul
SCORE      → (1.0, 0.8, 0.0, 1.0)  # Amarelo
GLUE_FLAP  → (0.0, 0.8, 0.2, 1.0)  # Verde
WINDOW     → (0.6, 0.0, 0.8, 1.0)  # Roxo
```

---

## 3. Detecção de Painéis e Topologia

### 3.1 Panel Detector
Usa `shapely` para encontrar todas as **regiões fechadas** formadas por linhas de corte + dobra:

1. Unir todas as linhas classificadas como CORTE ou DOBRA em uma coleção de geometrias
2. Aplicar `polygonize()` para encontrar todas as regiões fechadas
3. Cada polígono encontrado = um **painel** da embalagem

```python
Panel:
    id: int
    polygon: Polygon        # Geometria 2D (shapely)
    centroid: tuple[float]  # Centro do painel
    area: float             # Área em unidades SVG
    edges: list[Edge]       # Arestas com classificação
    neighbors: dict[int, FoldLine]  # Painéis adjacentes e a dobra que os conecta
```

### 3.2 Topology Graph
Constrói um **grafo de adjacência** onde:
- Cada nó = um painel
- Cada aresta = uma linha de dobra compartilhada entre dois painéis
- O grafo é usado pelo fold solver para determinar a sequência de dobra

```
Exemplo: Caixa tuck-end simples

     [Tampa Sup]
          │ (dobra)
    [Aba]─[Frente]─[Lado D]─[Trás]─[Lado E]─[Cola]
          │ (dobra)
     [Tampa Inf]
```

---

## 4. Geração 3D

### 4.1 Mesh dos Painéis
Para cada painel detectado:
1. Criar um mesh plano com os vértices do polígono 2D
2. Aplicar **extrude** com a espessura configurada (padrão: 0.3mm)
3. Posicionar na cena com as coordenadas do SVG (convertidas para unidades Blender)

### 4.2 Armature
1. Criar um **armature** (esqueleto) único para toda a embalagem
2. Para cada linha de dobra:
   - Criar um **bone** posicionado exatamente na linha de dobra
   - Head do bone = início da linha, Tail = fim da linha
   - O eixo de rotação do bone é a própria linha de dobra
3. Configurar hierarquia de bones baseada no grafo de adjacência:
   - Escolher um painel "raiz" (geralmente o maior painel, como a frente ou a base)
   - Todos os outros bones são filhos na árvore, seguindo a topologia do grafo

### 4.3 Parenting
- Cada mesh de painel é vinculado ao bone correspondente via **Armature modifier**
- Vertex groups são configurados para que cada painel se mova inteiramente com seu bone

### 4.4 UV Mapping
- As coordenadas 2D originais da faca são mapeadas diretamente como UVs
- Isso permite que o usuário aplique a arte da embalagem como textura e ela já esteja corretamente posicionada
- Normalização das UVs para o espaço [0,1] com base no bounding box da faca completa

---

## 5. Animação

### 5.1 Fold Solver
O solver calcula os **ângulos finais** de cada dobra para montar a embalagem:

1. Começando pelo painel raiz (fixo), percorre o grafo em BFS
2. Para cada dobra:
   - **Ângulo padrão**: 90° (a maioria das caixas tem ângulos retos)
   - **Abas de colagem**: mesmo ângulo do painel que estão colando
   - **Tampas**: 90° para posição fechada
3. Verifica auto-interseção (painéis não devem atravessar uns aos outros)
4. Permite override manual de ângulos via painel lateral

### 5.2 Fold Animation
Gera keyframes para cada bone:

```
Frame 1 (flat):
  Todos os bones: rotation = 0°

Frame 60 (folded):
  Bone_frente_lado_d: rotation_x = 90°
  Bone_lado_d_tras:   rotation_x = 90°
  Bone_tras_lado_e:   rotation_x = 90°
  Bone_lado_e_cola:   rotation_x = 90°
  Bone_frente_tampa_s: rotation_x = 90°
  Bone_frente_tampa_i: rotation_x = -90°
  ...
```

- Interpolação padrão: **Bezier** (ease-in-out)
- Sequência: painéis são dobrados na ordem do BFS, com offsets de frames para efeito cascata

### 5.3 Lid Animation
Adiciona keyframes adicionais após a dobra completa:

```
Frame 60 (folded, tampa fechada):
  Bone_tampa: rotation_x = 90°

Frame 90 (tampa aberta):
  Bone_tampa: rotation_x = 0°

Frame 120 (tampa fechada novamente):
  Bone_tampa: rotation_x = 90°
```

### 5.4 Preview Slider
Uma **custom property** no painel lateral controla um driver que interpola todos os ângulos de dobra:
- Valor 0.0 → faca plana
- Valor 1.0 → embalagem montada
- Qualquer valor intermediário → estado parcial da dobra
- Independente da timeline (para visualização rápida)

---

## 6. Interação do Usuário (UI)

### N-Panel (Sidebar)
```
┌─────────────────────────────┐
│ 📦 PACKAGING STUDIO         │
├─────────────────────────────┤
│                             │
│ ▼ Importação                │
│   [Import Dieline]          │
│   Arquivo: caixa.svg        │
│   Painéis: 8                │
│   Dimensões: 200×150mm      │
│                             │
│ ▼ Material                  │
│   Tipo: [Cartão ▾]          │
│   Espessura: [0.30] mm      │
│                             │
│ ▼ Classificação             │
│   ● Corte:    12 linhas     │
│   ● Dobra:     7 linhas     │
│   ● Vinco:     2 linhas     │
│   ● Aba:       3 linhas     │
│   Confiança média: 87%      │
│   [Reclassificar Manual]    │
│                             │
│ ▼ Geração 3D                │
│   [Generate 3D Model]       │
│                             │
│ ▼ Animação                  │
│   [Animate Fold]            │
│   [Animate Lid]             │
│   Preview: ═══════○── 0.65  │
│   Duração: [60] frames      │
│   Easing: [Bezier ▾]        │
│                             │
└─────────────────────────────┘
```

### Modos de Operação
1. **Import Mode**: ativo após importar uma faca; permite reclassificação
2. **Edit Mode**: ativo após gerar 3D; permite ajustar espessura, ângulos
3. **Animation Mode**: ativo após gerar animação; controla preview e exportação

---

## 7. Tratamento de Erros

| Cenário | Comportamento |
|---------|--------------|
| SVG sem paths vetoriais | Reporta warning, sugere verificar se é imagem rasterizada |
| PDF com múltiplas páginas | Pergunta qual página usar |
| Heurística com baixa confiança (< 60%) | Destaca linhas ambíguas em laranja, solicita revisão manual |
| Grafo desconectado (painéis soltos) | Reporta quais painéis não estão conectados, permite continuar parcialmente |
| Auto-interseção na dobra | Ajusta ângulos automaticamente ou reporta para ajuste manual |
| Arquivo corrompido/inválido | Rollback completo (padrão snapshot/rollback do blender_enhanced_svg) |
