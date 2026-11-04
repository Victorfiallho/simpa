# Roteiro da apresentação — Entrega 2

Slides: "SIMPA — Entrega 2" (17 slides, compartilhados pelo Victor; cada slide tem a fala completa nas notas do apresentador).

**Tempo total:** cerca de 23 minutos, sendo 19 de slides e 4 de demonstração. Se o tempo for de 15 minutos, use a versão curta no fim deste documento.

## Quem fala o quê

| Ordem | Integrante | Slides | Assunto | Tempo |
|---|---|---|---|---|
| 1 | Rafael | 1–2 | Abertura e o que a entrega mostra | 1 min 30 s |
| 2 | Breno | 3 | A reforma do sistema | 1 min 30 s |
| 3 | Victor | 4–5 | Arquitetura e organização dos dados | 3 min |
| 4 | Mario Jorge | 6–7 | Indicadores e cálculos estatísticos | 3 min 30 s |
| 5 | Samuel | 8–9 | Classificação de risco e painel | 2 min 30 s |
| 6 | Wellington | 10–11 | Gráficos e interpretação automática | 3 min 30 s |
| 7 | Fernando | 12–14 | Predição e recomendações | 4 min 30 s |
| 8 | Felipe | 15–16 | Integração e qualidade | 2 min 30 s |
| — | Victor (no computador) e Felipe (narra) | 17 | Demonstração ao vivo | 4 min |
| — | Rafael | — | Fechamento e perguntas | 30 s |

A divisão é uma sugestão: troquem à vontade, mas mantenham cada bloco com uma pessoa só, para não haver troca no meio de um assunto.

**Passagem de vez:** cada um termina com a frase de ponte indicada no seu bloco e chama o próximo pelo nome.

---

## 1. Rafael — Abertura (slides 1 e 2)

**Slide 1 · Capa**

> Boa noite. Nós somos o grupo do SIMPA, o Sistema Inteligente de Monitoramento e Predição Acadêmica. Na primeira entrega mostramos a estrutura do sistema. Hoje vamos mostrar que ele deixou de só guardar notas e frequência: agora ele calcula indicadores, interpreta os dados e até prevê risco.

**Slide 2 · O que esta entrega mostra**

> A apresentação segue os quatro pontos que o enunciado pede: os cálculos estatísticos, os indicadores escolhidos, como o sistema interpreta os dados e como tudo isso se integra à arquitetura. No fim, mostramos o sistema funcionando ao vivo.

**Ponte:** "Mas antes da análise, o Breno vai contar o que mudou na base do sistema."

## 2. Breno — A reforma do sistema (slide 3)

> Da Entrega 1 para cá, o SIMPA foi reconstruído.
>
> - **Arquitetura:** era só a estrutura de pastas de um monolito. Virou três serviços independentes, autenticação, acadêmico e analítico, atrás de um gateway.
> - **Banco:** saímos do SQLite para o PostgreSQL, com um banco para cada serviço.
> - **Comunicação:** os serviços conversam por eventos, numa fila do RabbitMQ.
> - **Interface:** o protótipo de tela com dados fixos foi refeito em React, ligado à API de verdade, com login e uma identidade visual própria. Cada cor do sistema significa uma situação de risco.
> - **Qualidade:** saímos de um teste de sanidade para 111 testes, que rodam sozinhos no GitHub a cada envio.
>
> Tudo sobe com um único comando no Docker. Essa base é o que permite a análise que vem a seguir.

**Ponte:** "O Victor vai mostrar como essa arquitetura funciona por dentro."

## 3. Victor — Arquitetura e dados (slides 4 e 5)

**Slide 4 · Arquitetura**

> O navegador só fala com o gateway, que é a porta única. O serviço acadêmico guarda cadastros, notas e frequência. O serviço analítico, em destaque, é onde mora toda a análise desta entrega.
>
> Quando uma nota é lançada, o acadêmico publica um evento na fila (a seta laranja). O worker do analítico recebe, busca os dados da inscrição numa rota interna e recalcula o risco (as setas verdes). Assim o lançamento não precisa esperar o cálculo, e a análise faz parte do sistema, não é uma planilha à parte.

**Slide 5 · Organização dos dados**

> - **Unidade de análise:** a inscrição, que é um aluno em uma disciplina. É por isso que o risco é calculado por disciplina, e uma reprovação isolada não some na média geral.
> - **Notas:** N1 vale peso 4 e N2 peso 6.
> - **Frequência:** nunca é digitada; o sistema calcula a partir das aulas e faltas.
> - **Arredondamento:** usamos números decimais exatos e arredondamos antes de classificar. 5,994 vira 5,99 e o aluno fica em risco; 5,995 vira 6,00 e ele não fica.
> - **Dados:** são sintéticos, por causa da LGPD, e incluem de propósito alunos exatamente na fronteira.

**Ponte:** "Com os dados organizados, o Mario Jorge mostra o que medimos e como."

## 4. Mario Jorge — Indicadores e cálculos (slides 6 e 7)

**Slide 6 · Indicadores escolhidos**

> Cada indicador responde a uma pergunta da coordenação.
>
> - **Média e mediana:** o nível típico da turma. Usamos as duas porque a mediana não se deixa levar por notas extremas.
> - **Desvio padrão:** se a turma é homogênea.
> - **Variação da N1 para o acumulado:** se a turma melhorou ou piorou.
> - **Correlação:** se presença e nota andam juntas.
> - **Situação de risco:** quem precisa de ajuda.
>
> Todos podem ser vistos por turma, disciplina, aluno ou período.

**Slide 7 · Cálculos estatísticos**

> Estas são as fórmulas implementadas no serviço analítico. Os exemplos em cinza são os mesmos valores dos testes automatizados, que conferimos à mão. Por exemplo, as notas 6, 7, 8 e 9 dão variância 1,25 e desvio padrão 1,12.
>
> Um detalhe importante é a variância:
> - no semestre inteiro de uma turma, dividimos por n, porque é o universo completo;
> - quando olhamos só a N1, que é um recorte, dividimos por n − 1, porque é uma amostra.

**Ponte:** "O Samuel mostra como esses números viram uma classificação de risco."

## 5. Samuel — Risco e painel (slides 8 e 9)

**Slide 8 · Classificação de risco**

> As quatro situações do sistema:
>
> - **Em risco:** média abaixo de 6 ou frequência abaixo de 75%, em qualquer disciplina.
> - **Atenção:** quem está acima do mínimo, mas perto dele.
> - **Indeterminado:** quem ainda não tem notas lançadas.
> - **Sem risco:** os demais.
>
> Toda classificação vem com uma justificativa escrita, que cita a disciplina, o valor e o critério. E a cor nunca aparece sozinha: o nome da situação está sempre junto.

**Slide 9 · Painel**

> Esta é a primeira tela depois do login:
> - os indicadores do recorte, comparados com a N1;
> - o cartão "O que os dados mostram", que o Wellington vai explicar;
> - à direita, a situação por disciplina e turma.
>
> Ao trocar a turma no topo, tudo é recalculado.

**Ponte:** "O Wellington mostra como ler os gráficos e o que o sistema conclui sozinho."

## 6. Wellington — Gráficos e interpretação (slides 10 e 11)

**Slide 10 · Gráficos**

> - **Histograma:** a maioria das médias fica entre 7 e 9; a cauda abaixo de 6 é o grupo em risco.
> - **Dispersão:** cada ponto é um aluno em uma disciplina, e as linhas tracejadas marcam 75% e média 6. Quase todos os pontos em risco estão à direita da linha de 75%. Ou seja: nestes dados, o problema é nota, não falta. A ação certa é monitoria, e não cobrança de presença.

**Slide 11 · Interpretação automática**

> Este é o ponto central da entrega: o sistema não só mostra números, ele escreve o que encontrou. Estas frases são geradas automaticamente e mudam quando trocamos o filtro. Ele diz:
> - o tamanho do problema;
> - de onde vem o risco;
> - qual disciplina concentra o risco;
> - a tendência da N1 para o acumulado;
> - a força da relação entre frequência e nota, lembrando que correlação não é causa.

**Ponte:** "E dá para ir além de descrever o passado: o Fernando mostra a predição."

## 7. Fernando — Predição e recomendações (slides 12, 13 e 14)

**Slide 12 · O modelo**

> Fizemos uma regressão linear múltipla que estima a nota da N2 a partir da nota e da frequência da N1. Os coeficientes saem da fórmula de mínimos quadrados em forma de matriz, beta igual a X transposta X inversa vezes X transposta y, calculada com o numpy. É a ligação direta com Álgebra Linear.
>
> **Leitura do modelo:** cada ponto a mais na N1 está associado a mais 0,80 na N2, e a frequência pesa pouco nestes dados.
>
> **Validação:** para o erro não sair otimista, medimos deixando cada inscrição de fora do ajuste. O modelo explica 71% da variação da N2, erra em média 0,77 ponto e acerta a situação final de risco em 94% dos casos.

**Slide 13 · Risco projetado**

> Com a N2 estimada, o sistema projeta a média final e mostra quem deve terminar em risco antes mesmo da N2: aqui são 15 inscrições. A própria tela mostra os limites do modelo, que vale ler em voz alta:
> - é associação, e não causa;
> - a amostra é pequena e sintética;
> - a classificação oficial continua sendo a regra do RF07.

**Slide 14 · Recomendações**

> Por fim, cada critério violado vira uma ação sugerida, com prioridade:
> - média baixa → monitoria;
> - falta → contato da coordenação;
> - risco em duas disciplinas → conversa sobre a carga do semestre;
> - projeção de queda → acompanhamento preventivo.
>
> Na imagem, a aluna está em risco em Álgebra Linear, e a recomendação de prioridade alta é monitoria. Quem decide é a coordenação; o sistema só sugere.

**Ponte:** "O Felipe fecha mostrando como tudo isso se encaixa e como garantimos que os números estão certos."

## 8. Felipe — Integração e qualidade (slides 15 e 16)

**Slide 15 · O caminho de uma nota**

> Este é o caminho real de um dado:
> 1. o professor lança a nota;
> 2. o acadêmico publica um evento;
> 3. o worker recalcula o risco;
> 4. o histórico só ganha uma linha nova se a situação mudou, para mostrar transições e não repetições;
> 5. o painel calcula indicadores e predição na hora.
>
> Embaixo estão as rotas que o serviço analítico expõe, todas protegidas por login.

**Slide 16 · Qualidade**

> São 111 testes automatizados, incluindo as duas fronteiras do arredondamento e uma regressão em dados onde sabemos a resposta certa. Eles rodam sozinhos no GitHub a cada envio.

**Ponte:** "Agora vamos mostrar tudo isso funcionando."

## 9. Demonstração ao vivo (slide 17)

O **Victor** opera o computador e o **Felipe** narra. Deixem tudo aberto antes de começar (ver "Antes da apresentação").

1. **Login** (30 s): entrar como `coordenacao@simpa.dev`. Se quiserem, mostrem antes uma senha errada e a mensagem genérica.
2. **Visão geral** (1 min): ler duas frases do cartão "O que os dados mostram", trocar a turma no topo e mostrar que as frases mudam.
3. **Aluno** (1 min): em Alunos, abrir a Alice Monteiro e mostrar a justificativa, as recomendações e o histórico.
4. **Recálculo ao vivo** (1 min):
   - escolher um aluno Sem risco;
   - no Swagger do acadêmico, lançar uma nota `0.00` com peso `10` para a inscrição dele;
   - recarregar a interface e mostrar o aluno Em risco, com uma linha nova no histórico.
5. **Análises e relatório** (30 s): descer até Predição e, em Relatórios, baixar o PDF.

## 10. Rafael — Fechamento

> O próximo marco é segurança: permissões por perfil, auditoria das requisições e proteção da API. Obrigado! Ficamos à disposição para perguntas.

---

## Antes da apresentação

- [ ] Docker Desktop aberto e o sistema no ar com os dados limpos do seed (assim os números batem com os slides):
  ```bash
  docker compose down -v
  docker compose up -d
  docker compose exec academico python -m app.comandos.seed
  ```
- [ ] Abas abertas: http://localhost (já logado), http://localhost/api/academico/docs (com o token do admin no Authorize) e os slides.
- [ ] `inscricao_id` do aluno da demonstração anotado, para não procurar ao vivo (aparece em `GET /alunos/{id}` no Swagger).
- [ ] Um ensaio cronometrado com todos, passando as pontes.
- [ ] Plano B: se a internet ou o Docker falharem, os slides 9, 10, 13 e 14 têm as telas reais do sistema.

## Perguntas prováveis

| Pergunta | Quem responde | Resposta curta |
|---|---|---|
| Por que separar em serviços? | Victor | Cada parte pode evoluir e cair sem derrubar o resto; o lançamento de nota não espera a análise. |
| Por que Decimal e não float? | Mario Jorge | Para o valor exibido ser exatamente o usado na decisão, sem erro de arredondamento na fronteira de 6,00. |
| Por que variância amostral só na N1? | Mario Jorge | A N1 é um recorte do semestre, então é amostra; o semestre completo da turma é o universo. |
| A predição é confiável? | Fernando | É um apoio: 94% de acerto medido deixando cada caso de fora, mas com amostra pequena e sintética. A regra oficial continua sendo o RF07. |
| Por que a frequência quase não pesa no modelo? | Fernando | Nestes dados a frequência é alta para quase todos; com pouca variação, ela explica pouco. Com dados reais isso pode mudar. |
| Os dados são reais? | Breno | Não. São sintéticos, por causa da LGPD, com casos de fronteira criados de propósito. |
| Onde estão os testes? | Felipe | Em `services/*/tests`, rodando no GitHub Actions a cada envio. |

## Versão curta (15 minutos)

- Juntar os slides 4 e 5 em 2 minutos e os slides 6 e 7 em 2 min 30 s.
- Pular a explicação detalhada do slide 13 e ir direto para as recomendações.
- Na demonstração, fazer só os passos 2, 3 e 4 (cerca de 3 minutos).
