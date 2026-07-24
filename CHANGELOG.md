# Changelog

Todas as mudanças notáveis deste projeto são documentadas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/)
e o projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [0.3.0] - 2026-07-24

### Added
- **Fase 3 (início) — Animação de dobra**:
  - Fold solver puro-Python (`core/fold_solver.py`): converte a topologia de dobra
    num cronograma ordenado de dobras (`FoldPlan`/`FoldStep`) com ângulo alvo e
    janela de frames por charneira.
  - Sequenciamento em cascata por profundidade BFS: painéis mais profundos dobram
    depois, montando a caixa do centro para fora.
  - Baker de animação (`mesh/fold_anim.py`): insere keyframes por bone (plano →
    dobrado) rotacionando no eixo X local, com suporte à API de *slotted actions*
    do Blender 4.4+/5.x.
  - Easing configurável: Linear, Smooth, Ease In, Ease Out, Ease In-Out, Bounce.
  - Operador "Animate Fold" e controles no N-panel (ângulo, frames/dobra, cascata,
    easing).
  - Testes puro-Python do solver (cascata, profundidade, ângulo, casos-limite).

### Notes
- Deferido para próximas iterações: animação de tampa (3.4/3.8) e slider de preview
  por driver (3.5).

## [0.2.3] - 2026-07-24

### Changed
- Parentesco dos bones agora é visível no viewport: nomes dos ossos ativados,
  exibição `OCTAHEDRAL`, armature desenhada à frente (`show_in_front`).
- Ao gerar o modelo 3D, as linhas de relacionamento (parent) são ligadas
  automaticamente em todas as viewports 3D, tornando a hierarquia de dobras clara.

### Notes
- O parentesco dos bones sempre esteve correto nos dados (hierarquia BFS a partir
  do painel raiz). A mudança é puramente de visualização.

## [0.2.2] - 2026-07-24

### Changed
- Convenção da armature reescrita para um rig de dobra padrão: cabeça do bone no
  **meio do vinco**, cauda apontando **para dentro do painel** e `align_roll` de
  modo que o eixo X local corra ao longo do vinco.
- Dobrar um painel passa a ser uma rotação limpa no **eixo X local** do bone.

### Fixed
- Bones que antes ficavam deitados sobre a linha de vinco (exigindo rotação
  contra-intuitiva no eixo de roll) agora seguem a convenção correta de charneira.

## [0.2.1] - 2026-07-24

### Fixed
- Facas reais do Illustrator geravam apenas 1 painel. Causas corrigidas:
  - Linhas de vinco tracejadas (`SCORE`) agora contam como fronteira de painel.
  - Formas preenchidas (fundo `<rect>` e ilustração de preview 3D) são ignoradas
    no parser (`fill != none`) e no detector (faces fora do contorno principal).
  - Formas fechadas fora do contorno externo são reclassificadas como `UNKNOWN`.
- `KeyError` na geração do rig quando havia componentes desconexos: painéis não
  alcançados pelo BFS agora recebem um bone de fallback.

## [0.2.0] - 2026-07-24

### Added
- **Fase 2 — Geração 3D**:
  - Detector de painéis: polygonize planar puro-Python (noding + travessia de
    faces) para encontrar regiões fechadas a partir das linhas classificadas.
  - Grafo de adjacência e resolução de topologia de dobra (BFS a partir do painel
    de maior área).
  - Geração de mesh por painel com espessura via n-gon + `bmesh.ops.solidify`,
    garantindo malha **100% quad/n-gon (nunca triângulos)**.
  - Armature com um bone por painel e hierarquia de dobra parent/child.
  - Parenting mesh→bone (Armature modifier + vertex group peso 1).
  - UV mapping normalizado pela bounding box da faca.
  - Operador "Generate 3D Box" e controles no N-panel (espessura, contagem de
    painéis).
  - Testes de detecção de painéis e de integração 3D headless.

## [0.1.2] - 2026-07-24

### Added
- **Fase 1 — MVP (importação + classificação)**:
  - Parser SVG com `xml.etree` (stdlib), aplicação de transformações e estrutura
    interna `DielinePath`.
  - Conversor PDF→SVG via PyMuPDF (empacotado como wheel).
  - Operador de importação (`PACKAGING_OT_import_dieline`) em File > Import.
  - Heurística de classificação de linhas (corte, dobra, vinco, glue flap).
  - Visualização 2D colorida por tipo de linha e painel lateral (N-panel) com
    contadores e confiança.
  - Suite de testes para parser e classificador.

## [0.1.1] - 2026-07-24

### Added
- Scaffolding inicial do addon: `__init__.py`, `blender_manifest.toml`,
  estrutura de diretórios e `build.py`.

[0.3.0]: https://github.com/jarffs/Packaging-Studio/releases/tag/v0.3.0
[0.2.3]: https://github.com/jarffs/Packaging-Studio/releases/tag/v0.2.3
[0.2.2]: https://github.com/jarffs/Packaging-Studio/releases/tag/v0.2.2
[0.2.1]: https://github.com/jarffs/Packaging-Studio/releases/tag/v0.2.1
[0.2.0]: https://github.com/jarffs/Packaging-Studio/releases/tag/v0.2.0
[0.1.2]: https://github.com/jarffs/Packaging-Studio/releases/tag/v0.1.2
[0.1.1]: https://github.com/jarffs/Packaging-Studio/releases/tag/v0.1.1
