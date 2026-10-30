# Roteiro de demonstração — Marco 2

Tempo estimado: 15 minutos. A demonstração é pela interface, em http://localhost.

## O que a entrega pede e onde mostrar

| Pedido da entrega | Onde está no SIMPA | Passo do roteiro |
|---|---|---|
| Indicadores estatísticos (médias, dispersão, variações) | Análises: média, mediana, desvio padrão, variância populacional/amostral, mínimo, máximo, variação N1 → acumulado | 5 |
| Visualizações / dashboard | Visão geral e Análises | 2 e 5 |
| Integração à API e à arquitetura | Serviço analítico, rotas `/painel`, `/indicadores`, `/predicao`, worker via RabbitMQ | 4 |
| Organização dos dados | DER, um banco por serviço, `Decimal` e arredondamento (D06), seed sintético | 1 |
| Identificar padrões e tendências | "O que os dados mostram" (interpretação automática) e a predição | 2 e 6 |
| Correlação, regressão, análise matricial, recomendação | Pearson, regressão com `β = (XᵀX)⁻¹Xᵀy`, recomendações por aluno | 6 |

## Antes de começar

```bash
docker compose up --build -d
docker compose exec academico python -m app.comandos.seed
```

Deixe abertas:

- http://localhost (a interface)
- http://localhost/api/academico/docs (para lançar uma nota ao vivo)
- `docker compose logs -f analitico-worker` num terminal

## 1. Entrada (1 min)

Entre como `coordenacao@simpa.dev` com a `DEMO_SENHA` do `.env`. Tente antes uma senha errada: a mensagem não diz se o erro foi no e-mail ou na senha (RF09 CA01).

## 2. Visão geral (3 min)

- **Indicadores:** alunos acompanhados, média geral e frequência média, cada um comparado com a N1.
- **Distribuição das médias:** quantas inscrições caem em cada faixa de nota.
- **Frequência × média:** cada ponto é uma inscrição, colorida pela situação. As linhas tracejadas (75% e 6,00) dividem o gráfico nas regiões de risco. Mostre a correlação de Pearson e diga que ela descreve associação, não causa.
- **Situação acadêmica:** inscrições por disciplina e turma, e o percentual de alunos em cada situação. Cada cor vem sempre com o nome escrito (RNF12).
- **O que os dados mostram:** o sistema descreve sozinho os padrões que encontrou, como quantos alunos estão em risco, se o risco vem de nota ou de falta, qual disciplina é a mais crítica, onde a média subiu ou caiu da N1 para o acumulado e a força da correlação. Aqui está a resposta a "como o sistema interpreta os dados".
- Troque a turma no topo: tudo é recalculado para o recorte, inclusive as frases.

## 3. Risco explicado (3 min)

Em **Alunos**, filtre por **Atenção** e abra a matrícula `20260005`:

- Estatística Aplicada com média **6,00** e frequência **75,00%**: está exatamente no mínimo, então fica **Sem risco**, mas com o sinal de **Atenção** (D08).
- A justificativa cita disciplina, média e frequência (RNF09).
- O histórico de risco mostra quando a classificação foi gravada (D11).

Depois abra a matrícula `20260009`: Álgebra Linear com média **5,99** (5,992 arredondado) fica **Em risco**. É o arredondamento antes de classificar (D06).

Mostre também o bloco **Recomendações** da gaveta: cada critério violado vira uma ação sugerida, com prioridade (média baixa → monitoria; falta → contato da coordenação; risco em duas disciplinas → conversa sobre a carga do semestre).

## 4. Recálculo ao vivo (2 min)

1. Na lista de Alunos, escolha alguém **Sem risco** e anote uma disciplina.
2. No Swagger do acadêmico, entre como `admin` e lance em `POST /avaliacoes` uma nota `0.00` com peso `10` para essa inscrição. Use o `inscricao_id` mostrado em `GET /alunos/{id}`.
3. No terminal, o worker registra "classificacao alterada".
4. Recarregue a interface: o aluno aparece **Em risco**, com a justificativa nova e mais uma linha no histórico.

## 5. Análises (2 min)

- Estatística descritiva: média, mediana, desvio padrão, variância (populacional), menor e maior média.
- Troque para **Parcial (só N1)**: a variância passa a ser **amostral**, porque N1 é um recorte do semestre (D07).
- Ranking e evolução por disciplina: onde a turma está melhor e onde caiu da N1 para o acumulado.

## 6. Predição (3 min)

Ainda em **Análises**, desça até **Predição**:

- **O modelo:** regressão linear múltipla `N2 = b0 + b1·N1 + b2·frequência N1`. Os coeficientes saem das equações normais em forma matricial, `β = (XᵀX)⁻¹Xᵀy`; é a ligação com Álgebra Linear (D21).
- **Leitura dos coeficientes:** cada ponto a mais na N1 está associado a cerca de +0,8 ponto na N2; a frequência pesa pouco nestes dados.
- **Qualidade:** o R² mostra quanto da variação da N2 o modelo explica. O erro médio e o acerto do risco foram medidos deixando cada inscrição de fora (validação cruzada pela matriz de projeção), então não são otimistas.
- **Previsto × real:** quanto mais perto da diagonal, melhor a previsão.
- **Risco projetado:** inscrições que, pela tendência da N1, devem terminar abaixo de 6,00. É assim que a coordenação age antes da N2.
- **Limites:** leia os quatro limites da tela. A banca valoriza saber onde o modelo não serve.

## 7. Relatórios (1 min)

Filtre por **Em risco** e baixe os três formatos. Mostre no arquivo:

- o cabeçalho com data, hora e o usuário que gerou;
- os e-mails mascarados e a ausência do CPF (RNF04);
- a vírgula decimal no CSV, que abre direto no Excel em português.

## Se perguntarem

- **Onde estão as regras?** Em `services/analitico/app/services/regras.py` e `estatistica.py`, funções puras testadas com valores calculados à mão (`tests/test_regras.py`, `tests/test_estatistica.py`), incluindo RF07 CA01 a CA03 e as fronteiras 5,994 e 5,995.
- **Onde estão a predição e as recomendações?** Em `predicao.py`, `recomendacoes.py` e `interpretacao.py`, testados em `tests/test_nivel2.py`. Um dos testes confirma que a regressão recupera exatamente coeficientes conhecidos.
- **Por que a regressão usa float e o risco usa Decimal?** A regressão é uma estimativa; a classificação oficial precisa bater exatamente na fronteira de 6,00 (D06, D21).
- **O frontend calcula alguma coisa?** Não. Ele só exibe o que o analítico devolve.
- **Por que não guardar os indicadores no banco?** Ficariam desatualizados a cada nota lançada. Só o histórico de risco é guardado (D11, D20).
