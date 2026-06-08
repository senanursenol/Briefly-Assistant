namespace DocSage.Infrastructure.Services;

public sealed class DocumentUploadService
{
    private readonly InMemoryDocumentStore _store;
    private readonly OnnxEmbeddingModel _embeddingModel;

    public DocumentUploadService(InMemoryDocumentStore store, OnnxEmbeddingModel embeddingModel)
    {
        _store = store;
        _embeddingModel = embeddingModel;
    }

    public async Task<(string DocId, string Filename, int NumChunks)> UploadAsync(
        Stream fileStream,
        string filename,
        CancellationToken cancellationToken = default)
    {
        var parts = filename.Split('.');
        var ext = parts.Length > 1 ? parts[^1].ToLowerInvariant() : string.Empty;

        if (ext is not ("pdf" or "doc" or "docx" or "txt"))
        {
            throw new ArgumentException("Sadece PDF, DOC, DOCX ve TXT dosyaları destekleniyor.");
        }

        await using var ms = new MemoryStream();
        await fileStream.CopyToAsync(ms, cancellationToken);
        var content = ms.ToArray();

        var text = DocumentTextExtractor.ExtractText(content, ext);
        var chunks = TextChunker.SplitIntoChunks(text);
        var docObj = new DocumentObject(chunks, filename, _embeddingModel);

        var docId = Guid.NewGuid().ToString();
        _store.Register(docId, docObj);

        return (docId, filename, docObj.Chunks.Count);
    }
}
