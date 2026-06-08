using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using DocSage.Infrastructure.Options;

namespace DocSage.Infrastructure.Services;

public sealed class GroqLlmService
{
    private readonly HttpClient _httpClient;
    private readonly DocSageOptions _options;
    private readonly ILogger<GroqLlmService> _logger;

    public GroqLlmService(IHttpClientFactory httpClientFactory, IOptions<DocSageOptions> options, ILogger<GroqLlmService> logger)
    {
        _httpClient = httpClientFactory.CreateClient("Groq");
        _options = options.Value;
        _logger = logger;
    }

    public bool IsConfigured =>
        !_options.UseLocalLlm && !string.IsNullOrWhiteSpace(_options.GroqApiKey);

    public async Task<string?> GenerateChatAsync(string systemPrompt, string userPrompt, CancellationToken cancellationToken = default)
    {
        if (!IsConfigured)
        {
            return null;
        }

        var request = new GroqChatRequest
        {
            Model = _options.GroqModel,
            Temperature = 0,
            Messages =
            [
                new GroqMessage { Role = "system", Content = systemPrompt },
                new GroqMessage { Role = "user", Content = userPrompt }
            ]
        };

        using var httpRequest = new HttpRequestMessage(HttpMethod.Post, "https://api.groq.com/openai/v1/chat/completions");
        httpRequest.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _options.GroqApiKey);
        httpRequest.Content = JsonContent.Create(request);

        try
        {
            using var response = await _httpClient.SendAsync(httpRequest, cancellationToken);
            if (!response.IsSuccessStatusCode)
            {
                var body = await response.Content.ReadAsStringAsync(cancellationToken);
                _logger.LogWarning("Groq API hatası: {Status} {Body}", response.StatusCode, body);
                return null;
            }

            var result = await response.Content.ReadFromJsonAsync<GroqChatResponse>(cancellationToken: cancellationToken);
            return result?.Choices?.FirstOrDefault()?.Message?.Content?.Trim();
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Groq isteği başarısız. Yerel modele geçiliyor...");
            return null;
        }
    }

    private sealed class GroqChatRequest
    {
        [JsonPropertyName("model")]
        public required string Model { get; init; }

        [JsonPropertyName("temperature")]
        public double Temperature { get; init; }

        [JsonPropertyName("messages")]
        public required List<GroqMessage> Messages { get; init; }
    }

    private sealed class GroqMessage
    {
        [JsonPropertyName("role")]
        public required string Role { get; init; }

        [JsonPropertyName("content")]
        public required string Content { get; init; }
    }

    private sealed class GroqChatResponse
    {
        [JsonPropertyName("choices")]
        public List<GroqChoice>? Choices { get; init; }
    }

    private sealed class GroqChoice
    {
        [JsonPropertyName("message")]
        public GroqMessage? Message { get; init; }
    }
}
