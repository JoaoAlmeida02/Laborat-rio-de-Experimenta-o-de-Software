# Imagem PHP-FPM instrumentada para o experimento fatorial 2x2 (LAB05)
# Tags oficiais verificadas no Docker Hub: php:8.4.26-fpm e php:8.4.27-fpm
ARG PHP_VERSION=8.4.27
FROM php:${PHP_VERSION}-fpm

ARG PHP_VERSION=8.4.27
ARG MITIGACAO=0
ARG WP_CLI_VERSION=2.11.0

ENV PHP_VERSION=${PHP_VERSION} \
    MITIGACAO=${MITIGACAO}

# Dependências de sistema para extensões do WordPress, WP-CLI e healthcheck FastCGI
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6-dev \
    libjpeg62-turbo-dev \
    libpng-dev \
    libwebp-dev \
    libzip-dev \
    libicu-dev \
    libxml2-dev \
    libonig-dev \
    libfcgi-bin \
    default-mysql-client \
    unzip \
    less \
    && docker-php-ext-configure gd --with-freetype --with-jpeg --with-webp \
    && docker-php-ext-install -j"$(nproc)" \
        mysqli \
        pdo_mysql \
        gd \
        zip \
        intl \
        opcache \
        exif \
        mbstring \
    && rm -rf /var/lib/apt/lists/*

# Instala WP-CLI em versão fixada para provisionamento automático do WordPress
RUN curl -fsSL "https://github.com/wp-cli/wp-cli/releases/download/v${WP_CLI_VERSION}/wp-cli-${WP_CLI_VERSION}.phar" \
    -o /usr/local/bin/wp \
    && chmod +x /usr/local/bin/wp \
    && wp --info --allow-root

# Configurações idênticas em todos os tratamentos (T1..T4)
COPY php.ini /usr/local/etc/php/conf.d/90-lab05-base.ini
COPY www.conf /usr/local/etc/php-fpm.d/zz-lab05-pool.conf
COPY entrypoint.sh /usr/local/bin/lab05-entrypoint.sh

# Garante quebras de linha LF (importante em builds no Windows) e permissão de execução
RUN sed -i 's/\r$//' /usr/local/bin/lab05-entrypoint.sh \
    && chmod +x /usr/local/bin/lab05-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/lab05-entrypoint.sh"]
CMD ["php-fpm"]
