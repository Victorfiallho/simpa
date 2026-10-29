# Frontend

Pasta reservada para a interface do SIMPA, que será construída a partir do protótipo do Figma.

Hoje o container serve só uma página estática (`public/index.html`) com links para o Swagger de cada serviço.

## Antes de começar

1. Registrar a decisão **D12** em `docs/decisoes.md`: qual stack será usada (ex.: React + Vite).
2. Mapear cada tela do Figma para as rotas da API que ela consome.
3. Trocar o `Dockerfile` por um build em dois estágios: compilar o projeto e servir os arquivos com nginx.

## Regras que valem para qualquer stack

- O front fala **só com o gateway**, por caminhos relativos (`/api/academico/...`). Nunca chama um serviço direto por porta.
- O token JWT vai no cabeçalho `Authorization: Bearer <token>`.
- Status de risco sempre escrito junto da cor, nunca só a cor (RNF12).
