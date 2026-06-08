namespace DocSage.Infrastructure.Services;

public sealed class EmbeddingStore
{
    private readonly OnnxEmbeddingModel _model;
    private float[][] _embeddings = [];
    private List<string> _texts = [];

    public EmbeddingStore(OnnxEmbeddingModel model)
    {
        _model = model;
    }

    public OnnxEmbeddingModel Model => _model;

    public void BuildIndex(IReadOnlyList<string> texts)
    {
        if (texts.Count == 0)
        {
            throw new ArgumentException("Index oluşturmak için metin yok.");
        }

        _texts = texts.ToList();
        _embeddings = _model.EncodeBatch(_texts);

        if (_embeddings.Length == 0 || _embeddings[0].Length == 0)
        {
            throw new InvalidOperationException("Geçerli embedding üretilemedi.");
        }
    }

    public List<EmbeddingSearchResult> Search(string query, int k = 5)
    {
        if (_embeddings.Length == 0)
        {
            return [];
        }

        var queryEmbedding = _model.Encode(query);
        var distances = new List<(int Index, float Distance)>();

        for (var i = 0; i < _embeddings.Length; i++)
        {
            distances.Add((i, L2Distance(queryEmbedding, _embeddings[i])));
        }

        return distances
            .OrderBy(d => d.Distance)
            .Take(k)
            .Where(d => d.Index >= 0 && d.Index < _texts.Count)
            .Select(d => new EmbeddingSearchResult { Text = _texts[d.Index] })
            .ToList();
    }

    private static float L2Distance(float[] a, float[] b)
    {
        var sum = 0f;
        for (var i = 0; i < a.Length; i++)
        {
            var diff = a[i] - b[i];
            sum += diff * diff;
        }

        return sum;
    }
}

public sealed class EmbeddingSearchResult
{
    public required string Text { get; init; }
}
