using System.Text.Json.Serialization;

namespace DocSage.Core.Models;

public sealed class UploadDocumentResponse
{
    [JsonPropertyName("doc_id")]
    public required string DocId { get; init; }

    [JsonPropertyName("filename")]
    public required string Filename { get; init; }

    [JsonPropertyName("num_chars")]
    public int NumChars { get; init; }
}

public sealed class QuestionRequest
{
    [JsonPropertyName("doc_ids")]
    public required List<string> DocIds { get; init; }

    [JsonPropertyName("question")]
    public required string Question { get; init; }
}

public sealed class ContextChunkDto
{
    [JsonPropertyName("text")]
    public required string Text { get; init; }

    [JsonPropertyName("source")]
    public required string Source { get; init; }
}

public sealed class QaResponse
{
    [JsonPropertyName("answer")]
    public required string Answer { get; init; }

    [JsonPropertyName("context_chunks")]
    public required List<ContextChunkDto> ContextChunks { get; init; }
}

public sealed class SummarizeRequest
{
    [JsonPropertyName("doc_id")]
    public required string DocId { get; init; }
}

public sealed class SummarizeResponse
{
    [JsonPropertyName("summary")]
    public required string Summary { get; init; }
}

public sealed class ChatHistoryItem
{
    public required string Question { get; init; }
    public required string Answer { get; init; }
}

public sealed class LoadedDocumentInfo
{
    public required string Id { get; init; }
    public required string Name { get; init; }
}
