namespace DocSage.Infrastructure.Services;

public sealed class DocumentObject
{
    public DocumentObject(IReadOnlyList<string> chunks, string filename, OnnxEmbeddingModel embeddingModel)
    {
        var cleanedChunks = chunks
            .Where(c => !string.IsNullOrWhiteSpace(c) && c.Trim().Length > 5)
            .Select(c => c.Trim())
            .ToList();

        if (cleanedChunks.Count == 0)
        {
            throw new InvalidOperationException(
                "Dokümandan anlamlı metin çıkarılamadı (Dosya boş veya okunamayan bir formatta olabilir).");
        }

        Chunks = cleanedChunks;
        Filename = filename;
        EmbeddingStore = new EmbeddingStore(embeddingModel);
        EmbeddingStore.BuildIndex(cleanedChunks);
    }

    public IReadOnlyList<string> Chunks { get; }
    public string Filename { get; }
    public EmbeddingStore EmbeddingStore { get; }
}
