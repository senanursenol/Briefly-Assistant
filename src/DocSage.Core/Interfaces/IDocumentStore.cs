using DocSage.Core.Models;

namespace DocSage.Core.Interfaces;

public interface IDocumentStore
{
    string AddDocument(string filename, IReadOnlyList<string> chunks);
    bool TryGet(string docId, out StoredDocument? document);
    IReadOnlyList<StoredDocument> GetMany(IEnumerable<string> docIds);
}

public sealed class StoredDocument
{
    public required string Id { get; init; }
    public required string Filename { get; init; }
    public required IReadOnlyList<string> Chunks { get; init; }
    public required object EmbeddingStore { get; init; }
}
