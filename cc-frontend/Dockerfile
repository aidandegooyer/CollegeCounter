# Stage 1: Build the app using Node
FROM node:22-alpine AS builder

WORKDIR /cc-frontend

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of your source code and build the project
COPY . .
RUN npm run build

# Stage 2: Serve the built app with Nginx
FROM nginx:stable-alpine

# Remove default Nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy built files from the builder stage
COPY --from=builder /cc-frontend/dist /usr/share/nginx/html

# Copy custom nginx configuration (overrides default)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]