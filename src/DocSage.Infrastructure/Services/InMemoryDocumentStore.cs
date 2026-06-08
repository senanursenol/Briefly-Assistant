using System.Collections.Concurrent;
using DocSage.Core.Interfaces;

namespace DocSage.Infrastructure.Services;

public sealed class InMemoryDocumentStore : IDocumentStore
{
    private readonly ConcurrentDictionary<string, DocumentObject> _store = new();

    public InMemoryDocumentStore()
    {
    }

    public void Register(string docId, DocumentObject document)
    {
        _store[docId] = document;
    }

    public string AddDocument(string filename, IReadOnlyList<string> chunks)
    {
        throw new NotSupportedException("Use DocumentUploadService to add documents.");
    }

    public bool TryGet(string docId, out StoredDocument? document)
    {
        if (_store.TryGetValue(docId, out var doc))
        {
            document = new StoredDocument
            {
                Id = docId,
                Filename = doc.Filename,
                Chunks = doc.Chunks,
                EmbeddingStore = doc.EmbeddingStore
            };
            return true;
        }

        document = null;
        return false;
    }

    public IReadOnlyList<StoredDocument> GetMany(IEnumerable<string> docIds)
    {
        var result = new List<StoredDocument>();
        foreach (var docId in docIds)
        {
            if (TryGet(docId, out var doc) && doc is not null)
            {
                result.Add(doc);
            }
        }

        return result;
    }

    public DocumentObject? GetDocumentObject(string docId)
    {
        return _store.TryGetValue(docId, out var doc) ? doc : null;
    }
}
