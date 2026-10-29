# Frontend do SIMPA

Interface web do SIMPA em **React + Vite + TypeScript** ([D12](../docs/decisoes.md#d12--interface-frontend)).

| Tela | Rota | O que mostra | Dados |
|---|---|---|---|
| Login | — | Entrada com e-mail e senha | `POST /api/auth/login` |
| Visão geral | `/` | Indicadores, distribuição das médias, frequência × média, alunos prioritários, situação por disciplina | `GET /api/analitico/painel` |
| Alunos | `/alunos` | Lista com busca e filtro; gaveta com notas, justificativas e histórico de risco | `/painel` e `/riscos/inscricoes/{id}/historico` |
| Análises | `/analises` | Estatística descritiva, ranking, evolução N1 → acumulado, janela parcial | `GET /api/analitico/indicadores/...` |
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
```

O frontend **não calcula** média, frequência nem risco: só exibe o que o serviço analítico devolve. As regras ficam num lugar só, no backend.

## Regras visuais

- **Cores de situação:** coral = Em risco, amarelo = Atenção, verde = Sem risco, azul = Indeterminado. Nunca use essas cores para outra coisa.
- **Situação sempre escrita junto da cor** (componente `Selo`), nunca só a cor (RNF12).
- **Títulos são o nome da tela**, sem slogans. Explicação longa vai para a documentação, não para a tela.
- **Números** usam a classe `num` (algarismos de largura fixa) e a formatação de `dados/formato.ts`. Decimais chegam da API como texto (`"7.50"`) e só viram número para desenhar gráficos.
- **Ícones** só do Lucide (`lucide-react`), com o mesmo traço.
- Toda tela que busca dados usa o componente `Conteudo`, que já trata carregamento e erro.
