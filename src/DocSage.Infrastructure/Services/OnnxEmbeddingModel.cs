using System.Collections.Concurrent;
using System.Net.Http.Headers;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Microsoft.ML.OnnxRuntime;
using Microsoft.ML.OnnxRuntime.Tensors;
using Microsoft.ML.Tokenizers;
using DocSage.Infrastructure.Options;

namespace DocSage.Infrastructure.Services;

public sealed class OnnxEmbeddingModel : IDisposable
{
    private static readonly ConcurrentDictionary<string, OnnxEmbeddingModel> SharedModels = new();
    private readonly InferenceSession _session;
    private readonly BertTokenizer _tokenizer;
    private readonly int _maxSequenceLength;
    private readonly ILogger<OnnxEmbeddingModel> _logger;

    private OnnxEmbeddingModel(
        InferenceSession session,
        BertTokenizer tokenizer,
        int maxSequenceLength,
        ILogger<OnnxEmbeddingModel> logger)
    {
        _session = session;
        _tokenizer = tokenizer;
        _maxSequenceLength = maxSequenceLength;
        _logger = logger;
    }

    public static async Task<OnnxEmbeddingModel> GetOrCreateAsync(
        IOptions<DocSageOptions> options,
        IHttpClientFactory httpClientFactory,
        ILogger<OnnxEmbeddingModel> logger,
        CancellationToken cancellationToken = default)
    {
        var modelId = options.Value.EmbeddingModelId;
        if (SharedModels.TryGetValue(modelId, out var existing))
        {
            return existing;
        }

        var created = await LoadAsync(options.Value, httpClientFactory, logger, cancellationToken);
        return SharedModels.GetOrAdd(modelId, created);
    }

    private static async Task<OnnxEmbeddingModel> LoadAsync(
        DocSageOptions options,
        IHttpClientFactory httpClientFactory,
        ILogger<OnnxEmbeddingModel> logger,
        CancellationToken cancellationToken)
    {
        var cacheDir = options.ModelCacheDirectory
            ?? Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "DocSage",
                "models",
                options.EmbeddingModelId.Replace('/', '_'));

        Directory.CreateDirectory(cacheDir);

        var modelPath = Path.Combine(cacheDir, "model.onnx");
        var tokenizerPath = Path.Combine(cacheDir, "tokenizer.json");

        if (!File.Exists(modelPath) || !File.Exists(tokenizerPath))
        {
            logger.LogInformation("Embedding modeli indiriliyor: {ModelId}", options.EmbeddingModelId);
            await DownloadModelFilesAsync(options.EmbeddingModelId, cacheDir, httpClientFactory, cancellationToken);
        }

        var session = new InferenceSession(modelPath);
        var tokenizer = await BertTokenizer.CreateAsync(tokenizerPath, cancellationToken: cancellationToken);
        return new OnnxEmbeddingModel(session, tokenizer, 512, logger);
    }

    private static async Task DownloadModelFilesAsync(
        string modelId,
        string cacheDir,
        IHttpClientFactory httpClientFactory,
        CancellationToken cancellationToken)
    {
        var client = httpClientFactory.CreateClient("HuggingFace");
        var baseUrl = $"https://huggingface.co/{modelId}/resolve/main";

        var files = new Dictionary<string, string>
        {
            ["onnx/model.onnx"] = Path.Combine(cacheDir, "model.onnx"),
            ["tokenizer.json"] = Path.Combine(cacheDir, "tokenizer.json"),
            ["config.json"] = Path.Combine(cacheDir, "config.json")
        };

        foreach (var (remoteName, localPath) in files)
        {
            if (File.Exists(localPath))
            {
                continue;
            }

            var url = $"{baseUrl}/{remoteName}";
            using var request = new HttpRequestMessage(HttpMethod.Get, url);
            request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/octet-stream"));

            using var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
            response.EnsureSuccessStatusCode();

            await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
            await using var file = File.Create(localPath);
            await stream.CopyToAsync(file, cancellationToken);
        }
    }

    public float[] Encode(string text)
    {
        return EncodeBatch([text])[0];
    }

    public float[][] EncodeBatch(IReadOnlyList<string> texts)
    {
        var results = new float[texts.Count][];
        for (var i = 0; i < texts.Count; i++)
        {
            results[i] = EncodeSingle(texts[i]);
        }

        return results;
    }

    private float[] EncodeSingle(string text)
    {
        var ids = _tokenizer.EncodeToIds(text, considerPreTokenization: true, considerNormalization: true);
        var length = Math.Min(ids.Count, _maxSequenceLength);

        var inputIds = new long[_maxSequenceLength];
        var attentionMask = new long[_maxSequenceLength];
        var tokenTypeIds = new long[_maxSequenceLength];

        for (var i = 0; i < length; i++)
        {
            inputIds[i] = ids[i];
            attentionMask[i] = 1;
            tokenTypeIds[i] = 0;
        }

        var inputs = new List<NamedOnnxValue>
        {
            NamedOnnxValue.CreateFromTensor("input_ids",
                new DenseTensor<long>(inputIds, [1, _maxSequenceLength])),
            NamedOnnxValue.CreateFromTensor("attention_mask",
                new DenseTensor<long>(attentionMask, [1, _maxSequenceLength])),
            NamedOnnxValue.CreateFromTensor("token_type_ids",
                new DenseTensor<long>(tokenTypeIds, [1, _maxSequenceLength]))
        };

        using var output = _session.Run(inputs);
        var tensor = output.First().AsTensor<float>();
        return MeanPooling(tensor, attentionMask, length);
    }

    private static float[] MeanPooling(Microsoft.ML.OnnxRuntime.Tensors.Tensor<float> hiddenStates, long[] attentionMask, int length)
    {
        var hiddenSize = hiddenStates.Dimensions[^1];
        var pooled = new float[hiddenSize];
        var tokenCount = 0f;

        for (var token = 0; token < length; token++)
        {
            if (attentionMask[token] == 0)
            {
                continue;
            }

            tokenCount += 1f;
            for (var dim = 0; dim < hiddenSize; dim++)
            {
                pooled[dim] += hiddenStates[0, token, dim];
            }
        }

        if (tokenCount <= 0)
        {
            return pooled;
        }

        for (var dim = 0; dim < hiddenSize; dim++)
        {
            pooled[dim] /= tokenCount;
        }

        L2NormalizeInPlace(pooled);
        return pooled;
    }

    private static void L2NormalizeInPlace(float[] vector)
    {
        var norm = 0f;
        foreach (var v in vector)
        {
            norm += v * v;
        }

        norm = MathF.Sqrt(norm);
        if (norm <= 0)
        {
            return;
        }

        for (var i = 0; i < vector.Length; i++)
        {
            vector[i] /= norm;
        }
    }

    public void Dispose()
    {
        _session.Dispose();
    }
}
