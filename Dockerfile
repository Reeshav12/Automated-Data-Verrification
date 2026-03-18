FROM node:20-alpine

ENV PORT=3000

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY . .
RUN npm run build && npm install -g serve

EXPOSE 3000

CMD ["sh", "-c", "serve -s dist -l ${PORT}"]
