# Estágio 1: compila o React (TypeScript + Vite) em arquivos estáticos.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY . .
RUN npm run build

# Estágio 2: serve só o resultado com nginx; o Node não vai para a imagem final.
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
