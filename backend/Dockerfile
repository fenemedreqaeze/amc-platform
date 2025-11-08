FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    apache2 perl wget curl && apt-get clean
WORKDIR /var/www/html
EXPOSE 80
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
