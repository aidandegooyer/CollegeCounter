FROM node:24.6-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . ./
ARG REACT_APP_API_URL
ARG VITE_CURRENT_SEASON_ID
ENV REACT_APP_API_URL=$REACT_APP_API_URL
ENV VITE_CURRENT_SEASON_ID=$VITE_CURRENT_SEASON_ID
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf


EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
