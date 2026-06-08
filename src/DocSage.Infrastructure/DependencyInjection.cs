using DocSage.Core.Interfaces;
using DocSage.Infrastructure.Options;
using DocSage.Infrastructure.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace DocSage.Infrastructure;

public static class DependencyInjection
{
    public static IServiceCollection AddDocSageInfrastructure(this IServiceCollection services, IConfiguration configuration)
    {
        services.Configure<DocSageOptions>(configuration.GetSection(DocSageOptions.SectionName));
        services.Configure<DocSageOptions>(options =>
        {
            options.GroqApiKey ??= Environment.GetEnvironmentVariable("GROQ_API_KEY");
            options.GroqModel = Environment.GetEnvironmentVariable("GROQ_MODEL") ?? options.GroqModel;
            if (bool.TryParse(Environment.GetEnvironmentVariable("USE_LOCAL_LLM"), out var useLocal))
            {
                options.UseLocalLlm = useLocal;
            }

            options.LocalModelPath = Environment.GetEnvironmentVariable("LOCAL_MODEL_PATH") ?? options.LocalModelPath;
            options.ModelCacheDirectory = Environment.GetEnvironmentVariable("MODEL_CACHE_DIR") ?? options.ModelCacheDirectory;
        });

        services.AddHttpClient("HuggingFace", client =>
        {
            client.Timeout = TimeSpan.FromMinutes(30);
            client.DefaultRequestHeaders.UserAgent.ParseAdd("DocSage/1.0");
        });

        services.AddHttpClient("Groq", client =>
        {
            client.Timeout = TimeSpan.FromMinutes(2);
        });

        services.AddSingleton<InMemoryDocumentStore>();
        services.AddSingleton<IDocumentStore>(sp => sp.GetRequiredService<InMemoryDocumentStore>());
        services.AddSingleton<HybridRetrievalService>();
        services.AddSingleton<GroqLlmService>();
        services.AddSingleton<LocalLlmService>();
        services.AddSingleton<QaService>();
        services.AddSingleton<DocumentUploadService>();

        services.AddSingleton<OnnxEmbeddingModel>(sp =>
        {
            var factory = sp.GetRequiredService<IHttpClientFactory>();
            var options = sp.GetRequiredService<Microsoft.Extensions.Options.IOptions<DocSageOptions>>();
            var logger = sp.GetRequiredService<Microsoft.Extensions.Logging.ILogger<OnnxEmbeddingModel>>();
            return OnnxEmbeddingModel.GetOrCreateAsync(options, factory, logger).GetAwaiter().GetResult();
        });

        return services;
    }
}
