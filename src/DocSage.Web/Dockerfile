FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY DocSage.sln ./
COPY src/DocSage.Core/ src/DocSage.Core/
COPY src/DocSage.Web/ src/DocSage.Web/

RUN dotnet restore src/DocSage.Web/DocSage.Web.csproj
RUN dotnet publish src/DocSage.Web/DocSage.Web.csproj -c Release -o /app/publish --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app

ENV ASPNETCORE_URLS=http://+:8080
ENV Backend__Url=http://backend:8000

COPY --from=build /app/publish .

EXPOSE 8080
ENTRYPOINT ["dotnet", "DocSage.Web.dll"]
