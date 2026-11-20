# LegacyCore: Compact Java 17 Monolith
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY legacy_core.jar /app/legacy_core.jar
EXPOSE 8081
# Planted ~200MB memory cap with -Xmx256m
ENTRYPOINT ["java", "-Xms128m", "-Xmx256m", "-jar", "/app/legacy_core.jar", "8081"]
