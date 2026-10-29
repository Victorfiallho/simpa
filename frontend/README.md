# Frontend do SIMPA

Interface web do SIMPA em **React + Vite + TypeScript** ([D12](../docs/decisoes.md#d12--interface-frontend)).

| Tela | Rota | Situação |
|---|---|---|
| Visão geral | `/` | Pronta, com dados de demonstração |
| Alunos (lista, busca, filtros e detalhe do aluno) | `/alunos` | Pronta, com dados de demonstração |
| Análises | `/analises` | Fase 2 |
| Relatórios | `/relatorios` | Fase 2 |

## Rodar

Com o Docker, o front já sobe junto com o resto: `docker compose up --build` e acesse http://localhost.

Para desenvolver com recarga instantânea (precisa do [Node.js](https://nodejs.org/) 20.19 ou mais novo):

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

O `npm run dev` repassa as chamadas `/api` para o gateway em `http://localhost`, então deixe o Docker rodando se a tela usar a API.

Antes de commitar, confira se o TypeScript e o build passam:

```bash
npm run build
```

## Organização

```
src/
  main.tsx               ponto de entrada
  App.tsx                rotas e filtro de turma
  estilos/global.css     cores, tipografia e estilos de todas as telas
  componentes/           barra lateral, cabeçalho, selo de status, gráficos auxiliares
  paginas/               uma tela por arquivo
  dados/
    tipos.ts             tipos que espelham o DER
    calculos.ts          média, frequência e classificação de risco (D04–D09)
    painel.ts            monta os números e séries que as telas exibem
    demonstracao.ts      base sintética usada até a API existir
    formato.ts           formatação pt-BR, rótulos e cores dos status
```

## Regras visuais

- **Cores de status:** coral = Em risco, amarelo = Atenção, verde = Sem risco, azul = Indeterminado. Nunca use essas cores para outra coisa.
- **Status sempre escrito junto da cor** (componente `Selo`), nunca só a cor (RNF12).
- **Títulos são o nome da tela**, sem slogans. Explicação longa vai para a documentação, não para a tela.
- **Números** usam a classe `num` (algarismos de largura fixa) e a formatação de `dados/formato.ts`.
- **Ícones** só do Lucide (`lucide-react`), com o mesmo traço.

## Ligar à API

Hoje `App.tsx` usa `gerarBaseDemonstracao()`. Quando as rotas de indicadores do analítico existirem (ROADMAP 2.3), troque essa base por chamadas a `/api/analitico/...` e `/api/academico/...`, mantendo o formato de `Painel` (`dados/painel.ts`) para as telas não mudarem.
