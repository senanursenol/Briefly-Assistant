namespace DocSage.Infrastructure.Options;

public sealed class DocSageOptions
{
    public const string SectionName = "DocSage";

    public string EmbeddingModelId { get; set; } = "Xenova/paraphrase-multilingual-MiniLM-L12-v2";
    public string? ModelCacheDirectory { get; set; }
    public string? GroqApiKey { get; set; }
    public string GroqModel { get; set; } = "llama-3.3-70b-versatile";
    public bool UseLocalLlm { get; set; }
    public string LocalModelPath { get; set; } = "";
    public string NoAnswerMessage { get; set; } = "Üzgünüm, bu sorunun cevabını dökümanlarda bulamadım.";
}
