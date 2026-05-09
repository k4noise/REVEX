FROM nginx:alpine

COPY nginx.conf /etc/nginx/nginx.conf
RUN mkdir -p /var/cache/nginx
COPY --from=labstructanalyzer_frontend /app/dist /usr/share/nginx/html

EXPOSE 80
ENTRYPOINT ["nginx", "-g", "daemon off;"]
