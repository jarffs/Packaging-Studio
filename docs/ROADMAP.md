# Roadmap — Packaging Studio

> Documento vivo que acompanha o progresso de implementação do addon.
> Última atualização: 2026-07-24 — Fase 2 concluída.

---

## Resumo por Fase

| Fase | Nome | Objetivo | Status |
|------|------|----------|--------|
| 1 | MVP | Importação de facas SVG/PDF + classificação automática de linhas | ✅ Concluído |
| 2 | Geração 3D | Modelo 3D com espessura, armature e UV mapping | ✅ Concluído |
| 3 | Animação | Dobra automática + animação de tampa | � Em progresso |
| 4 | Polish & UX | Drag-and-drop, presets, materiais PBR, preferências | 🔲 Não iniciado |
| 5 | Avançado | Janelas, crash-lock, glTF, batch, ECMA | 🔲 Não iniciado |

---

## Fase 1 — MVP: Importação + Classificação

**Objetivo**: Importar uma faca SVG/PDF, classificar linhas automaticamente por heurística geométrica e exibir o resultado no viewport com cores distintas por tipo.

**Critério de "done"**: O usuário importa um SVG de uma caixa tuck-end simples e vê as linhas coloridas corretamente por tipo (corte, dobra, aba) no viewport, com informações no painel lateral.

### Tarefas

| # | Tarefa | Descrição | Deps | Status |
|---|--------|-----------|------|--------|
| 1.1 | Scaffolding do addon | `__init__.py`, `blender_manifest.toml`, estrutura de diretórios, `build.py` | — | ✅ |
| 1.2 | Parser SVG | Extrair todos os paths do SVG com `xml.etree` (stdlib), aplicar transformações, gerar estrutura interna `DielinePath` | 1.1 | ✅ |
| 1.3 | Conversor PDF→SVG | Usar `pymupdf` para converter a primeira página de um PDF em paths SVG | 1.2 | ✅ |
| 1.4 | Operador de importação | `PACKAGING_OT_import_dieline` com `ImportHelper`, menu em File > Import, validação de formato | 1.2, 1.3 | ✅ |
| 1.5 | Heurística de classificação v1 | Pass 1: contorno externo = corte. Pass 2: linhas internas = dobra/vinco/aba. Pass 3: refinamento (glue flap) | 1.2 | ✅ |
| 1.6 | Visualização 2D colorida | Criar curvas Blender com materiais coloridos por tipo de linha | 1.5 | ✅ |
| 1.7 | Painel lateral (N-panel) | Mostrar info da faca importada, contadores por tipo de linha, confiança | 1.6 | ✅ |
| 1.8 | Testes unitários do parser | Testes com SVGs de exemplo para validar extração de paths | 1.2 | ✅ |
| 1.9 | Testes do classificador | Testes com facas conhecidas para validar heurística | 1.5 | ✅ |

### Entregáveis
- Addon instalável que importa SVG/PDF de facas
- Linhas classificadas e coloridas no viewport
- Painel lateral com informações básicas
- Suite de testes para parser e classificador

---

## Fase 2 — Geração 3D

**Objetivo**: Transformar a faca classificada em um modelo 3D com mesh com espessura, armature com bones nas dobras, e UV mapping correto.

**Critério de "done"**: A partir de uma faca classificada, o usuário clica em "Generate 3D" e obtém uma caixa 3D com painéis separados, conectados por bones, com UVs prontas para receber textura.

### Tarefas

| # | Tarefa | Descrição | Deps | Status |
|---|--------|-----------|------|--------|
| 2.1 | Detector de painéis | Polygonize planar puro-Python (noding + travessia de faces) para achar regiões fechadas | Fase 1 | ✅ |
| 2.2 | Grafo de adjacência | Construir grafo de nós (painéis) e arestas (dobras compartilhadas) | 2.1 | ✅ |
| 2.3 | Geração de mesh | Criar mesh de cada painel: n-gon + solidify → **quads (nunca triângulos)** | 2.1 | ✅ |
| 2.4 | Criação de armature | Bone por painel: head no meio do vinco, tail para dentro do painel (`align_roll` → dobra no eixo X local) | 2.2 | ✅ |
| 2.5 | Hierarquia de bones | Definir parent/child baseado no BFS a partir do painel raiz (maior área) | 2.4 | ✅ |
| 2.6 | Parenting mesh→bone | Vincular cada mesh ao bone via Armature modifier + vertex group (peso 1) | 2.3, 2.5 | ✅ |
| 2.7 | UV mapping | Mapear coordenadas 2D da faca como UVs normalizadas pela bbox | 2.3 | ✅ |
| 2.8 | Operador "Generate 3D" | Botão no N-panel que executa toda a pipeline de geração | 2.1–2.7 | ✅ |
| 2.9 | Testes de detecção de painéis | Validar com facas de complexidade variada (retângulo, split, strip) | 2.1 | ✅ |
| 2.10 | Testes de integração 3D | Verificar geometria gerada headless (0 triângulos, rig completo) | 2.8 | ✅ |

> **Nota de implementação**: `shapely`/`numpy` foram substituídos por um polygonize
> planar puro-Python (`core/panel_detector.py`) e por geometria própria em
> `utils/geometry.py`, mantendo `core/` e `utils/` livres de dependências e do `bpy`.
> A geração 3D usa n-gon + `bmesh.ops.solidify` para garantir malha **100% quad/n-gon**.


### Entregáveis
- Botão "Generate 3D" funcional
- Modelo 3D com painéis separados, espessura e armature
- UV mapping correto para aplicação de texturas
- Testes de detecção e geração

---

## Fase 3 — Animação

**Objetivo**: Gerar automaticamente animações de montagem (flat→folded) e abertura/fechamento de tampa.

**Critério de "done"**: O usuário clica em "Animate Fold" e vê a caixa se montando suavemente. Pode usar o slider para preview em qualquer ponto. Pode adicionar animação de tampa.

### Tarefas

| # | Tarefa | Descrição | Deps | Status |
|---|--------|-----------|------|--------|
| 3.1 | Fold solver | Calcular ângulos finais de cada dobra (default 90°) com detecção de auto-interseção | Fase 2 | � |
| 3.2 | Sequência de dobra | Determinar ordem de dobra via BFS com offsets de frames para efeito cascata | 3.1 | ✅ |
| 3.3 | Keyframes de dobra | Gerar keyframes para cada bone: frame 1 = flat, frame N = folded | 3.2 | ✅ |
| 3.4 | Animação de tampa | Keyframes adicionais para abrir/fechar tampa após dobra | 3.3 | 🔲 |
| 3.5 | Slider de preview | Custom property com driver que interpola todos os ângulos (0.0→1.0) | 3.3 | 🔲 |
| 3.6 | Easing configurável | Seletor de interpolação: Linear, Bezier, Ease-in, Ease-out, Bounce | 3.3 | ✅ |
| 3.7 | Operador "Animate Fold" | Botão no N-panel | 3.1–3.6 | ✅ |
| 3.8 | Operador "Animate Lid" | Botão no N-panel | 3.4 | 🔲 |
| 3.9 | Testes de animação | Verificar que os keyframes geram a dobra correta | 3.7 | ✅ |

### Entregáveis
- Animação automática de montagem
- Animação de tampa
- Slider de preview interativo
- Easing configurável

---

## Fase 4 — Polish & UX

**Objetivo**: Tornar a experiência do usuário fluida e profissional.

### Tarefas

| # | Tarefa | Descrição | Deps | Status |
|---|--------|-----------|------|--------|
| 4.1 | FileHandlers (drag-and-drop) | Arrastar SVG/PDF para o viewport para importar | Fase 1 | 🔲 |
| 4.2 | Preferências do addon | Espessura padrão, duração de animação, FPS, cores de classificação | Fase 1 | 🔲 |
| 4.3 | Reclassificação manual | Selecionar linha(s) no viewport e alterar tipo via dropdown | Fase 1 | 🔲 |
| 4.4 | Presets de embalagem | Templates pré-configurados (tuck-end, auto-bottom, sleeve, display) | Fase 2 | 🔲 |
| 4.5 | Materiais PBR | Shaders realistas para cartão (branco, kraft, reciclado), papelão ondulado | Fase 2 | 🔲 |
| 4.6 | Documentação de usuário | Guia de uso com screenshots, tutorial em vídeo | Fase 3 | 🔲 |
| 4.7 | Arquivos de exemplo | SVGs de facas de diferentes tipos de embalagem | — | 🔲 |

---

## Fase 5 — Avançado

**Objetivo**: Funcionalidades avançadas para uso profissional.

### Tarefas

| # | Tarefa | Descrição | Deps | Status |
|---|--------|-----------|------|--------|
| 5.1 | Detecção de janelas | Identificar paths fechados internos como janelas e gerar cutouts no mesh | Fase 2 | 🔲 |
| 5.2 | Crash-lock / encaixe | Suporte a embalagens com sistema de trava mecânica | Fase 3 | 🔲 |
| 5.3 | Exportação glTF | Exportar modelo animado para web/AR | Fase 3 | 🔲 |
| 5.4 | Batch processing | Importar e processar múltiplas facas de uma vez | Fase 1 | 🔲 |
| 5.5 | Padrões ECMA | Compatibilidade com especificações ECMA de embalagens | Fase 2 | 🔲 |
| 5.6 | Machine Learning | Classificador ML treinado para substituir/complementar heurística | Fase 1 | 🔲 |

---

## Decisões Técnicas

| Decisão | Justificativa |
|---------|--------------|
| Heurística geométrica (não por cor/layer) | Facas de diferentes fornecedores usam convenções diferentes; análise geométrica é agnóstica |
| PDF convertido internamente para SVG | Pipeline único simplifica manutenção e testes |
| Armature-based animation (bones) | Permite ao usuário ajustar manualmente, reutilizar com NLA, compatível com Blender nativo |
| Blender 4.2+ LTS | API estável, ampla base de usuários, suporte de longo prazo |
| Separação `core/` vs `mesh/` | Testes unitários puros para lógica geométrica sem depender do runtime do Blender |
| Padrão snapshot/rollback | Segurança: qualquer erro reverte todas as alterações feitas no .blend |

---

## Métricas de Sucesso por Fase

| Fase | Métrica |
|------|---------|
| 1 | Classificação correta ≥ 85% das linhas em 5 facas de teste diferentes |
| 2 | Modelo 3D geometricamente correto para caixas retangulares simples |
| 3 | Animação de dobra sem auto-interseção para caixas tuck-end |
| 4 | Tempo de importação+geração+animação < 10 segundos para facas típicas |
| 5 | Suporte a ≥ 5 tipos de embalagem diferentes com ≥ 90% de automação |
