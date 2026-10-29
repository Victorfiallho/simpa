# Roteiro de demonstração — Marco 2

Tempo estimado: 12 minutos. Agora a demonstração é pela interface, em http://localhost.

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
- Troque a turma no topo: tudo é recalculado para o recorte.

## 3. Risco explicado (3 min)

Em **Alunos**, filtre por **Atenção** e abra a matrícula `20260005`:

- Estatística Aplicada com média **6,00** e frequência **75,00%**: está exatamente no mínimo, então fica **Sem risco**, mas com o sinal de **Atenção** (D08).
- A justificativa cita disciplina, média e frequência (RNF09).
- O histórico de risco mostra quando a classificação foi gravada (D11).

Depois abra a matrícula `20260009`: Álgebra Linear com média **5,99** (5,992 arredondado) fica **Em risco**. É o arredondamento antes de classificar (D06).

## 4. Recálculo ao vivo (2 min)

1. Na lista de Alunos, escolha alguém **Sem risco** e anote uma disciplina.
2. No Swagger do acadêmico, entre como `admin` e lance em `POST /avaliacoes` uma nota `0.00` com peso `10` para essa inscrição. Use o `inscricao_id` mostrado em `GET /alunos/{id}`.
3. No terminal, o worker registra "classificacao alterada".
4. Recarregue a interface: o aluno aparece **Em risco**, com a justificativa nova e mais uma linha no histórico.

## 5. Análises (2 min)

- Estatística descritiva: média, mediana, desvio padrão, variância (populacional), menor e maior média.
- Troque para **Parcial (só N1)**: a variância passa a ser **amostral**, porque N1 é um recorte do semestre (D07).
- Ranking e evolução por disciplina: onde a turma está melhor e onde caiu da N1 para o acumulado.

## 6. Relatórios (1 min)

Filtre por **Em risco** e baixe os três formatos. Mostre no arquivo:

- o cabeçalho com data, hora e o usuário que gerou;
- os e-mails mascarados e a ausência do CPF (RNF04);
- a vírgula decimal no CSV, que abre direto no Excel em português.

## Se perguntarem

- **Onde estão as regras?** Em `services/analitico/app/services/regras.py` e `estatistica.py`, funções puras testadas com valores calculados à mão (`tests/test_regras.py`, `tests/test_estatistica.py`), incluindo RF07 CA01 a CA03 e as fronteiras 5,994 e 5,995.
- **O frontend calcula alguma coisa?** Não. Ele só exibe o que o analítico devolve.
- **Por que não guardar os indicadores no banco?** Ficariam desatualizados a cada nota lançada. Só o histórico de risco é guardado (D11, D20).
