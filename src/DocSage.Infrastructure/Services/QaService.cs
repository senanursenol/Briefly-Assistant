using DocSage.Core.Models;
using Microsoft.Extensions.Options;
using DocSage.Infrastructure.Options;

namespace DocSage.Infrastructure.Services;

public sealed class QaService
{
    private readonly HybridRetrievalService _retrieval;
    private readonly GroqLlmService _groq;
    private readonly LocalLlmService _localLlm;
    private readonly DocSageOptions _options;

    public QaService(
        HybridRetrievalService retrieval,
        GroqLlmService groq,
        LocalLlmService localLlm,
        IOptions<DocSageOptions> options)
    {
        _retrieval = retrieval;
        _groq = groq;
        _localLlm = localLlm;
        _options = options.Value;
    }

    public async Task<QaResponse> AnswerAsync(
        string question,
        IReadOnlyList<DocumentObject> documents,
        CancellationToken cancellationToken = default)
    {
        var contexts = _retrieval.RetrieveGloballyRelevantChunks(question, documents);

        var contextLength = contexts.Sum(c => c.Text.Length);
        if (contexts.Count == 0 || contextLength < 50)
        {
            return new QaResponse
            {
                Answer = _options.NoAnswerMessage,
                ContextChunks = []
            };
        }

        var answer = await GenerateAnswerFromContextsAsync(question, contexts.Select(c => c.Text).ToList(), cancellationToken);
        return new QaResponse
        {
            Answer = answer,
            ContextChunks = contexts
        };
    }

    public async Task<string> SummarizeAsync(DocumentObject document, CancellationToken cancellationToken = default)
    {
        var summaryContexts = document.Chunks.Take(10).ToList();
        if (summaryContexts.Count == 0)
        {
            return "Özetlenecek içerik bulunamadı.";
        }

        var systemPrompt =
            "Sen profesyonel bir metin özetleme asistanısın. Görevin, sana verilen metin parçalarını " +
            "okumak ve içeriğin ana hatlarını kapsayan, kısa ve öz bir Türkçe özet oluşturmaktır.\n" +
            "Özet, dökümanın en önemli noktalarını içermeli ve madde işaretleri kullanılarak sunulmalıdır.";
        var userPrompt = $"Özetlenecek Metin:\n{string.Join("\n\n", summaryContexts)}";

        return await GenerateLlmResponseAsync(systemPrompt, userPrompt, cancellationToken);
    }

    private async Task<string> GenerateAnswerFromContextsAsync(
        string question,
        IReadOnlyList<string> contexts,
        CancellationToken cancellationToken)
    {
        if (contexts.Count == 0)
        {
            return _options.NoAnswerMessage;
        }

        var contextText = string.Join("\n\n", contexts);
        var systemPrompt =
            "Sen yardımcı bir yapay zeka asistanısın. Görevin, kullanıcının sorusunu sadece sağlanan bağlama (context) dayanarak cevaplamaktır.\n" +
            "İzlenecek adımlar:\n" +
            "1. Bağlamı dikkatlice oku.\n" +
            "2. Soruyu cevaplayan spesifik cümleleri bul.\n" +
            "3. Cevabı açık ve okunabilir bir formatta sentezle.\n" +
            "4. Cevabı dökümanın dili ne olursa olsun Türkçe olarak ver.\n" +
            $"Eğer bağlam cevabı içermiyorsa, tam olarak şu yanıtı ver: '{_options.NoAnswerMessage}'";
        var userPrompt = $"Bağlam:\n{contextText}\n\nSoru:\n{question}";

        return await GenerateLlmResponseAsync(systemPrompt, userPrompt, cancellationToken);
    }

    private async Task<string> GenerateLlmResponseAsync(
        string systemPrompt,
        string userPrompt,
        CancellationToken cancellationToken)
    {
        if (_groq.IsConfigured)
        {
            var groqAnswer = await _groq.GenerateChatAsync(systemPrompt, userPrompt, cancellationToken);
            if (!string.IsNullOrWhiteSpace(groqAnswer))
            {
                return groqAnswer;
            }
        }

        return await _localLlm.GenerateChatAsync(systemPrompt, userPrompt, cancellationToken);
    }
}
