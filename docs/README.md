<p align="center">
  <img src="docs/assets/logo_placeholder.png" alt="Packaging Studio" width="200"/>
</p>

<h1 align="center">Packaging Studio</h1>

<p align="center">
  <strong>Blender addon que transforma facas de embalagens (dielines) em modelos 3D prontos para renderização e animação.</strong>
</p>

<p align="center">
  <a href="#instalação">Instalação</a> •
  <a href="#workflow">Workflow</a> •
  <a href="#funcionalidades">Funcionalidades</a> •
  <a href="#roadmap">Roadmap</a> •
  <a href="#arquitetura">Arquitetura</a> •
  <a href="#desenvolvimento">Desenvolvimento</a>
</p>

---

## O que é

**Packaging Studio** é um addon para Blender 4.2+ que automatiza o processo de transformar facas de embalagens (dielines) — os gabaritos 2D usados na indústria gráfica para produção de caixas e embalagens — em modelos 3D completos com:

- **Detecção automática** de linhas de corte, dobra, vinco e abas de colagem via heurística geométrica
- **Geração 3D** com espessura de material realista (cartão, papelão ondulado, micro-ondulado)
- **Animação de montagem** — da faca plana até a embalagem montada
- **Animação de tampa** — abertura e fechamento com easing configurável

Suporta importação de arquivos **SVG** e **PDF**, os formatos mais usados na indústria de embalagens.

---

## Workflow

O Packaging Studio segue um pipeline de 4 etapas, projetado para ser o mais automático possível, com opção de ajuste manual em cada passo.

### Etapa 1 — Importação

```
File > Import > Dieline (SVG/PDF)   ou   arrastar e soltar no viewport
```

O addon lê o arquivo da faca e extrai todas as curvas e paths. Arquivos PDF são convertidos internamente para SVG antes do processamento, garantindo um pipeline único.

**Formatos suportados:**
| Formato | Método |
|---------|--------|
| SVG     | Parsing direto com `xml.etree` (stdlib, sem dependências) |
| PDF     | Conversão interna via `pymupdf` → SVG |

### Etapa 2 — Classificação e Revisão

Após a importação, o addon aplica uma **heurística geométrica** para classificar automaticamente cada linha da faca:

| Tipo | Cor no Viewport | Critério |
|------|----------------|----------|
| **Corte** (cut) | 🔴 Vermelho | Contorno externo; linhas que formam o perímetro da faca |
| **Dobra** (fold/crease) | 🔵 Azul | Linhas internas que dividem painéis adjacentes |
| **Vinco** (score/half-cut) | 🟡 Amarelo | Linhas tracejadas ou parciais internas |
| **Aba de colagem** (glue flap) | 🟢 Verde | Painéis estreitos com geometria trapezoidal |
| **Corte especial** (window/cutout) | 🟣 Roxo | Paths fechados internos (janelas, furos) |

Um **painel lateral (N-panel)** exibe a classificação e permite ao usuário:
- Reclassificar linhas manualmente (selecionar + alterar tipo)
- Definir a espessura do material (presets: cartão 0.3mm, papelão ondulado 3mm, micro-ondulado 1.5mm)
- Visualizar estatísticas da faca (número de painéis, dimensões, área total)

### Etapa 3 — Geração do Modelo 3D

Com a classificação validada, o usuário clica em **"Generate 3D"** e o addon:

1. **Detecta painéis** — identifica todas as regiões fechadas formadas por linhas de corte + dobra
2. **Constrói o grafo de adjacência** — mapeia quais painéis se conectam por quais linhas de dobra
3. **Gera mesh com espessura** — cada painel vira um mesh 3D com a espessura do material configurado
4. **Cria armature** — posiciona bones exatamente nas linhas de dobra, com orientação correta
5. **Configura parenting** — cada mesh de painel é vinculado ao bone correspondente
6. **Aplica UV mapping** — mapeia as coordenadas 2D originais da faca como UVs, permitindo aplicar a arte da embalagem diretamente como textura

```
┌─────────────────────────────────────────────┐
│              Faca 2D (SVG/PDF)              │
│  ┌───────┬───────┬───────┬───────┬──────┐  │
│  │ Aba   │ Lado  │ Frente│ Lado  │ Cola │  │
│  │       │       │       │       │      │  │
│  └───────┴───────┴───────┴───────┴──────┘  │
│           │  Tampa │       │ Fundo │        │
│           └───────┘       └───────┘        │
└─────────────────────────────────────────────┘
                    ▼
            "Generate 3D"
                    ▼
              ┌─────────┐
             ╱│        ╱│
            ╱ │       ╱ │    Modelo 3D com
           ┌─────────┐  │    espessura e
           │  │      │  │    armature pronto
           │  └──────│──┘    para animação
           │ ╱       │ ╱
           │╱        │╱
           └─────────┘
```

### Etapa 4 — Animação

O addon oferece dois tipos de animação automática:

#### Animação de Dobra (Fold Animation)
Gera keyframes que transformam a faca plana na embalagem montada.

- **Frame 1**: faca totalmente plana (todos os ângulos de dobra = 0°)
- **Frame N**: embalagem completamente montada (ângulos finais calculados pelo fold solver)
- **Easing**: curvas de aceleração configuráveis (ease-in-out por padrão)

Um **slider de preview** no painel lateral permite visualizar qualquer estado intermediário da dobra (0.0 = plano → 1.0 = montado) sem precisar reproduzir a animação.

#### Animação de Tampa (Lid Animation)
Após a animação de dobra, adiciona keyframes para abrir e fechar a tampa:

- **Abrir**: tampa vai de fechada (90°) para aberta (0° ou 180°)
- **Fechar**: movimento inverso
- Pode ser combinada com a animação de dobra para uma sequência completa

```
Timeline:
├─── Dobra (flat → folded) ───┤── Tampa abre ──┤── Tampa fecha ──┤
F1                           F60              F90              F120
```

---

## Funcionalidades

### Core
- [x] Importação de SVG (paths, grupos, layers)
- [x] Importação de PDF (conversão interna via pymupdf)
- [x] Classificação heurística automática de linhas (corte/dobra/vinco/aba)
- [ ] Reclassificação manual de linhas no viewport
- [x] Detecção automática de painéis (regiões fechadas)
- [x] Grafo de adjacência entre painéis
- [x] Geração de mesh 3D com espessura parametrizável (quads/n-gon)
- [x] Armature com bones nas linhas de dobra
- [x] UV mapping automático (coordenadas 2D da faca → UVs)
- [ ] Animação de dobra automática (flat → folded)
- [ ] Animação de abertura/fechamento de tampa
- [ ] Slider de preview de dobra

### Tipos de Embalagem
- [ ] Caixa tuck-end (abas de encaixe superior e inferior)
- [ ] Caixa com fundo automático (auto-bottom/auto-lock)
- [ ] Sleeve / Luva
- [ ] Caixa display
- [ ] Caixa com janela (window box)
- [ ] Embalagens com encaixe (crash-lock)
- [ ] Formatos customizados

### UX
- [ ] Drag-and-drop de arquivos SVG/PDF
- [ ] Painel lateral (N-panel) com controles completos
- [ ] Presets de espessura de material
- [ ] Presets de tipos de embalagem
- [ ] Materiais PBR para papelão/cartão
- [ ] Preferências configuráveis do addon

### Avançado
- [ ] Detecção automática de janelas (window cutouts)
- [ ] Exportação para glTF (web/AR)
- [ ] Batch processing de múltiplas facas
- [ ] Compatibilidade com padrões ECMA de embalagens

---

## Requisitos

### Sistema
- **Blender 4.2+** (LTS)
- Windows, macOS ou Linux

### Dependências Python (empacotadas como wheels)
| Pacote | Uso | Status |
|--------|-----|--------|
| `xml.etree` (stdlib) | Parsing SVG (sem dependência externa) | ✅ Fase 1 |
| `pymupdf` | Conversão de PDF para SVG (opcional, lazy import) | ✅ Fase 1 |
| `shapely` | ~~Operações geométricas 2D~~ substituído por polygonize puro-Python | ✅ Fase 2 |
| `numpy` | ~~Cálculos vetoriais~~ substituído por geometria própria | ✅ Fase 2 |
| `lxml` | Parsing SVG mais robusto (opcional/futuro) | Futuro |

> **Nota:** A Fase 1 usa apenas a biblioteca padrão do Python para o parsing SVG,
> mantendo `core/` e `utils/` totalmente testáveis fora do Blender. O `pymupdf`
> é importado de forma preguiçosa apenas quando um PDF é aberto.

---

## Instalação

### Via Blender Extensions (recomendado)
1. Abra o Blender 4.2+
2. Vá em `Edit > Preferences > Extensions`
3. Pesquise por **"Packaging Studio"**
4. Clique em **Install**

### Manual
1. Baixe o release mais recente (`.zip`) da [página de releases](../../releases)
2. No Blender, vá em `Edit > Preferences > Add-ons`
3. Clique em **Install from Disk** e selecione o arquivo `.zip`
4. Ative o addon na lista

---

## Roadmap

### Fase 1 — MVP: Importação + Classificação
> Objetivo: importar uma faca SVG/PDF, classificar linhas automaticamente e exibir no viewport com cores.

| # | Tarefa | Status |
|---|--------|--------|
| 1 | Scaffolding do addon (manifest, `__init__`, register/unregister) | ✅ |
| 2 | Importador SVG básico (parse paths com `xml.etree`) | ✅ |
| 3 | Conversor PDF → SVG (`pymupdf`) | ✅ |
| 4 | Heurística de classificação v1 (contorno externo vs linhas internas) | ✅ |
| 5 | Visualização 2D no viewport com cores por tipo de linha | ✅ |
| 6 | Painel lateral (N-panel) com informações da faca importada | ✅ |

### Fase 2 — Geração 3D
> Objetivo: transformar a faca classificada em um modelo 3D com espessura, armature e UV mapping.

| # | Tarefa | Status |
|---|--------|--------|
| 7 | Detector de painéis (encontrar regiões fechadas) | ✅ |
| 8 | Construção do grafo de adjacência entre painéis | ✅ |
| 9 | Geração de mesh com espessura (n-gon + solidify, sempre quads) | ✅ |
| 10 | Criação de armature + bones nas linhas de dobra | ✅ |
| 11 | Parenting correto (cada painel mesh → bone correspondente) | ✅ |
| 12 | UV mapping automático | ✅ |

### Fase 3 — Animação
> Objetivo: animar automaticamente a montagem da embalagem e a abertura/fechamento da tampa.

| # | Tarefa | Status |
|---|--------|--------|
| 13 | Fold solver (calcular ângulos finais para cada dobra) | 🔲 |
| 14 | Geração de keyframes de dobra (flat → folded) | 🔲 |
| 15 | Animação de tampa (abrir/fechar) | 🔲 |
| 16 | Slider de preview no painel lateral | 🔲 |
| 17 | Easing curves configuráveis | 🔲 |

### Fase 4 — Polish & UX
> Objetivo: tornar a experiência do usuário fluida e profissional.

| # | Tarefa | Status |
|---|--------|--------|
| 18 | Drag-and-drop via FileHandlers | 🔲 |
| 19 | Preferências do addon (espessura padrão, FPS, etc.) | 🔲 |
| 20 | Reclassificação manual de linhas (click-to-reclassify) | 🔲 |
| 21 | Presets de tipos de embalagem | 🔲 |
| 22 | Materiais PBR realistas para papelão/cartão | 🔲 |
| 23 | Documentação completa e arquivos de exemplo | 🔲 |

### Fase 5 — Avançado
> Objetivo: funcionalidades avançadas para uso profissional.

| # | Tarefa | Status |
|---|--------|--------|
| 24 | Detecção automática de janelas (window patching) | 🔲 |
| 25 | Suporte a embalagens com encaixe (crash-lock) | 🔲 |
| 26 | Exportação de animação para glTF (web/AR) | 🔲 |
| 27 | Batch processing de múltiplas facas | 🔲 |
| 28 | Integração com padrões ECMA de embalagens | 🔲 |

---

## Arquitetura

O addon segue a mesma arquitetura do [`blender_enhanced_svg`](https://github.com/kolibril13/blender_enhanced_svg), adaptada para o domínio de embalagens.

> Legenda: ✅ implementado na Fase 1 · ⏳ planejado (fases futuras)

```
packaging_studio/
├── __init__.py                  # ✅ Registro de classes, menus, painéis (lazy bpy)
├── blender_manifest.toml        # ✅ Metadata da extensão Blender
├── build.py                     # ✅ Download de wheels + build da extensão
│
├── operators/                   # Operadores Blender (ações do usuário)
│   ├── import_dieline.py        # ✅ File > Import > Dieline (SVG/PDF)
│   ├── generate_3d.py           # ⏳ Gera modelo 3D a partir da classificação
│   ├── animate_fold.py          # ⏳ Gera animação de dobra
│   └── animate_lid.py           # ⏳ Gera animação de tampa
│
├── core/                        # Lógica de negócio (independente do Blender)
│   ├── types.py                 # ✅ Dataclasses: DielinePath, ClassifiedLine, StrokeStyle
│   ├── svg_path.py              # ✅ Parser do atributo "d" (M/L/H/V/C/S/Q/T/A/Z)
│   ├── svg_parser.py            # ✅ Parse SVG → estrutura interna (xml.etree)
│   ├── pdf_parser.py            # ✅ PDF → SVG (pymupdf, lazy import)
│   ├── line_classifier.py       # ✅ Heurística: corte / dobra / vinco / aba / janela
│   ├── panel_detector.py        # ⏳ Encontra regiões fechadas (faces da caixa)
│   ├── topology.py              # ⏳ Grafo de adjacência entre painéis
│   └── fold_solver.py           # ⏳ Calcula ângulos e sequência de dobra
│
├── mesh/                        # Geração de geometria 3D
│   ├── viewport.py              # ✅ Curvas coloridas por tipo de linha
│   ├── panel_mesh.py            # ⏳ Mesh com espessura para cada painel
│   ├── materials.py             # ⏳ Materiais + UV mapping
│   └── armature.py              # ⏳ Bones posicionados nas dobras
│
├── animation/                   # ⏳ Sistema de animação
│   ├── fold_animation.py        # ⏳ Keyframes flat → folded
│   └── lid_animation.py         # ⏳ Keyframes abrir / fechar tampa
│
├── ui/                          # Interface do usuário
│   ├── properties.py            # ✅ PropertyGroup com estatísticas da faca
│   ├── panels.py                # ✅ N-panel (sidebar) com controles
│   ├── preferences.py           # ⏳ Preferências do addon
│   └── file_handlers.py         # ⏳ FileHandlers para drag-and-drop
│
├── utils/                       # Utilitários compartilhados (sem bpy)
│   ├── geometry.py              # ✅ Funções geométricas 2D (transforms, bbox, área)
│   └── constants.py             # ✅ Espessuras padrão, cores, limites
│
├── wheels/                      # Dependências Python empacotadas (.whl)
├── tests/                       # ✅ Suite de testes (run.py, test_parser, test_classifier)
└── examples/                    # ✅ Arquivos de exemplo de facas (simple_tuck_end.svg)
```

### Princípios de Design

- **Separação `core/` vs `mesh/`**: A lógica de análise geométrica em `core/` é independente da API do Blender, facilitando testes unitários puros. O módulo `mesh/` contém o código que interage com `bpy`.
- **Transações seguras**: Seguindo o padrão snapshot/rollback do `blender_enhanced_svg`, toda operação de geração pode ser revertida em caso de erro.
- **Heurística extensível**: O classificador de linhas usa uma pipeline de regras que pode ser estendida sem alterar o código existente.

---

## Desenvolvimento

### Pré-requisitos
- Blender 4.2+ instalado
- Python 3.11+ (embutido no Blender)
- Git

### Executar testes
Os testes de `core/` e `utils/` não dependem do Blender e rodam com Python puro:
```sh
python packaging_studio/tests/run.py
```
Também é possível executá-los dentro do Python do Blender:
```sh
blender --background --factory-startup --python-exit-code 1 --python packaging_studio/tests/run.py
```

### Build da extensão
```sh
blender -b -P packaging_studio/build.py
```

### Estrutura de testes
Os testes são divididos em:
- **Testes unitários** (`test_parser.py`, `test_classifier.py`, `test_panel_detection.py`, `test_fold_solver.py`): testam a lógica em `core/` sem depender do Blender
- **Testes de integração** (`test_animation.py`): testam a geração de objetos Blender e animações dentro do runtime do Blender

---

## Referências

- [blender_enhanced_svg](https://github.com/kolibril13/blender_enhanced_svg) — Addon de referência para a arquitetura
- [ECMA-341](https://www.ecma-international.org/publications-and-standards/standards/ecma-341/) — Padrão de embalagens
- [Blender Extensions Platform](https://extensions.blender.org/) — Distribuição de addons

---

## Licença

GPL-3.0 — compatível com o Blender e com o addon de referência.
