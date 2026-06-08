using LLama;
using LLama.Common;
using LLama.Sampling;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using DocSage.Infrastructure.Options;

namespace DocSage.Infrastructure.Services;

public sealed class LocalLlmService : IDisposable
{
    private readonly DocSageOptions _options;
    private readonly ILogger<LocalLlmService> _logger;
    private readonly SemaphoreSlim _loadLock = new(1, 1);
    private LLamaWeights? _weights;
    private ModelParams? _modelParams;
    private bool _disposed;

    public LocalLlmService(IOptions<DocSageOptions> options, ILogger<LocalLlmService> logger)
    {
        _options = options.Value;
        _logger = logger;
    }

    public bool IsEnabled => _options.UseLocalLlm || string.IsNullOrWhiteSpace(_options.GroqApiKey);

    private async Task EnsureLoadedAsync(CancellationToken cancellationToken)
    {
        if (_weights is not null)
        {
            return;
        }

        await _loadLock.WaitAsync(cancellationToken);
        try
        {
            if (_weights is not null)
            {
                return;
            }

            var modelPath = ResolveModelPath();
            if (!File.Exists(modelPath))
            {
                throw new FileNotFoundException(
                    $"Yerel LLM modeli bulunamadı: {modelPath}. GGUF dosyasını indirin veya GROQ_API_KEY tanımlayın.",
                    modelPath);
            }

            _logger.LogInformation("Yerel LLM yükleniyor: {Path}", modelPath);
            _modelParams = new ModelParams(modelPath)
            {
                ContextSize = 2048,
                GpuLayerCount = 0
            };
            _weights = await LLamaWeights.LoadFromFileAsync(_modelParams, cancellationToken);
        }
        finally
        {
            _loadLock.Release();
        }
    }

    private string ResolveModelPath()
    {
        if (!string.IsNullOrWhiteSpace(_options.LocalModelPath) && File.Exists(_options.LocalModelPath))
        {
            return _options.LocalModelPath;
        }

        var defaultDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "DocSage",
            "models",
            "llm");

        if (!Directory.Exists(defaultDir))
        {
            return Path.Combine(defaultDir, "qwen2.5-1.5b-instruct-q4_k_m.gguf");
        }

        var gguf = Directory.GetFiles(defaultDir, "*.gguf").FirstOrDefault();
        return gguf ?? Path.Combine(defaultDir, "qwen2.5-1.5b-instruct-q4_k_m.gguf");
    }

    public async Task<string> GenerateChatAsync(string systemPrompt, string userPrompt, CancellationToken cancellationToken = default)
    {
        await EnsureLoadedAsync(cancellationToken);

        var executor = new StatelessExecutor(_weights!, _modelParams!);
        var inferenceParams = new InferenceParams
        {
            MaxTokens = 512,
            AntiPrompts = ["<|endoftext|>", ""],
            SamplingPipeline = new DefaultSamplingPipeline
            {
                Temperature = 0f,
                RepeatPenalty = 1.1f
            }
        };

        var prompt = $"""
            <|im_start|>system
            {systemPrompt}
            
            <|im_start|>user
            {userPrompt}
            
            <|im_start|>assistant
            """;

        var response = new System.Text.StringBuilder();
        await foreach (var token in executor.InferAsync(prompt, inferenceParams, cancellationToken))
        {
            response.Append(token);
        }

        return response.ToString().Trim();
    }

    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }

        _weights?.Dispose();
        _loadLock.Dispose();
        _disposed = true;
    }
}
