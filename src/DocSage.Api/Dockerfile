FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY DocSage.sln ./
COPY src/DocSage.Core/ src/DocSage.Core/
COPY src/DocSage.Infrastructure/ src/DocSage.Infrastructure/
COPY src/DocSage.Api/ src/DocSage.Api/

RUN dotnet restore src/DocSage.Api/DocSage.Api.csproj
RUN dotnet publish src/DocSage.Api/DocSage.Api.csproj -c Release -o /app/publish --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    antiword \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV ASPNETCORE_URLS=http://+:8000
ENV MODEL_CACHE_DIR=/root/.cache/docsage/models

COPY --from=build /app/publish .

EXPOSE 8000
ENTRYPOINT ["dotnet", "DocSage.Api.dll"]
