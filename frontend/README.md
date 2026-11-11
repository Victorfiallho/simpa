# Frontend do SIMPA

Interface web do SIMPA em **React + Vite + TypeScript** ([D12](../docs/decisoes.md#d12--interface-frontend)).

| Tela | Rota | O que mostra | Dados |
|---|---|---|---|
| Login | — | Entrada com e-mail e senha | `POST /api/auth/login` |
| Visão geral | `/` | Indicadores, distribuição das médias, frequência × média, alunos prioritários, situação por disciplina | `GET /api/analitico/painel` |
| Alunos | `/alunos` | Lista com busca e filtro; gaveta com notas, justificativas e histórico de risco | `/painel` e `/riscos/inscricoes/{id}/historico` |
| Análises | `/analises` | Estatística descritiva, achados, ranking, evolução N1 → acumulado, janela parcial, predição por regressão | `GET /api/analitico/indicadores/...` e `/predicao` |
| Relatórios | `/relatorios` | Download em CSV, XLSX e PDF com filtros | `GET /api/analitico/relatorios/inscricoes` |

Os filtros de período e turma, no topo, valem para todas as telas.

## Rodar

Com o Docker, o front já sobe junto com o resto: `docker compose up --build -d`, depois o seed (ver README da raiz) e acesse http://localhost.

Para desenvolver com recarga instantânea (precisa do [Node.js](https://nodejs.org/) 20.19 ou mais novo e do Docker rodando, porque a tela usa a API):

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

O `npm run dev` repassa as chamadas `/api` para o gateway em `http://localhost`.

Antes de commitar, confira se o TypeScript e o build passam:

```bash
npm run build
```

## Organização

```
src/
  main.tsx               ponto de entrada
  App.tsx                login, rotas, filtros e carregamento do painel
  sessao.tsx             sessão do usuário (token no sessionStorage)
  api/
    cliente.ts           chamadas ao gateway com o token; download de relatórios
    tipos.ts             tipos das respostas da API
    useDados.ts          carregamento com estados de espera e erro
  estilos/global.css     cores, tipografia e estilos de todas as telas
  componentes/           barra lateral, cabeçalho, selo de situação, gaveta do aluno, gráficos auxiliares
  paginas/               uma tela por arquivo
  dados/formato.ts       formatação pt-BR, rótulos e cores das situações
  movimento.ts           durações, curvas e hooks de animação (gaveta, entrada de tela, números)
```

O frontend **não calcula** média, frequência nem risco: só exibe o que o serviço analítico devolve. As regras ficam num lugar só, no backend.

## Regras visuais

- **Cores de situação:** coral = Em risco, amarelo = Atenção, verde = Sem risco, azul = Indeterminado. Nunca use essas cores para outra coisa.
- **Situação sempre escrita junto da cor** (componente `Selo`), nunca só a cor (RNF12).
- **Títulos são o nome da tela**, sem slogans. Explicação longa vai para a documentação, não para a tela.
- **Números** usam a classe `num` (algarismos de largura fixa) e a formatação de `dados/formato.ts`. Decimais chegam da API como texto (`"7.50"`) e só viram número para desenhar gráficos.
- **Ícones** só do Lucide (`lucide-react`), com o mesmo traço.
- Toda tela que busca dados usa o componente `Conteudo`, que já trata carregamento e erro.
- **Cor de status não é cor de texto.** O coral, o amarelo, o verde e o azul de situação marcam pontos, barras e fundos; texto em cima de fundo claro usa as variantes escuras (`--coral-escuro` e as demais), que têm contraste de 4,5:1.

## Movimento

O movimento é discreto e tem função: mostra de onde algo veio, para onde foi e o que mudou.

- **O que se move:** a tela nova entra com um leve deslocamento, e os cartões dela entram em sequência quando os dados chegam. Os números dos indicadores contam até o valor. Os anéis e as barras se preenchem. O indicador do menu desliza até o item escolhido. As gavetas entram e saem pela direita, com o fundo esmaecendo. O carregamento mostra um esqueleto com brilho. Botões, linhas e campos respondem ao passar o mouse e ao clicar.
- **Tokens:** as durações (`rapida` 140 ms, `media` 240 ms, `lenta` 420 ms) e a curva de saída (ease-out-quint) estão em `src/movimento.ts` e, iguais, nas variáveis `--mov-*` de `global.css`. Use esses valores, não números soltos.
- **CSS primeiro.** Entradas, hovers, esqueleto e barras são CSS. O [motion](https://motion.dev) (`motion/react`) só entra no que o CSS não faz bem: a saída das gavetas (`AnimatePresence`), o indicador do menu (`layoutId`) e as molas. Ele usa componentes `m` com `LazyMotion`: os recursos de animação chegam num arquivo à parte (`recursosDeMovimento.ts`), fora da primeira carga.
- **Menos movimento:** com `prefers-reduced-motion: reduce` no sistema, tudo aparece direto no estado final (`MotionConfig reducedMotion="user"` e o bloco no fim de `global.css`). Os testes de navegador rodam assim, e `tests/e2e/movimento.spec.ts` confere os dois modos.
- **Gavetas num portal.** A camada que anima a entrada da tela usa `transform`, que mudaria a referência de um `position: fixed`. Por isso as gavetas são renderizadas em `document.body` (`createPortal`).
