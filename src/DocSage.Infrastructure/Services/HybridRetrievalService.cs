using System.Text.RegularExpressions;
using DocSage.Core.Models;

namespace DocSage.Infrastructure.Services;

public sealed class HybridRetrievalService
{
    private static readonly HashSet<string> TurkishStops = new(StringComparer.OrdinalIgnoreCase)
    {
        "ne", "nasıl", "neden", "niçin", "ne zaman", "mı", "mi", "mu", "mü",
        "ve", "veya", "ama", "fakat", "lakin", "ancak", "ile", "için", "gibi",
        "bir", "bu", "şu", "o", "da", "de", "ki", "ise", "miyim", "misin",
        "mısınız", "misiniz", "mıdır", "midir", "olan", "olarak", "tarafından",
        "hakkında", "ilgili", "dair", "ait", "kendi", "hepsi", "her", "hiç",
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "with", "by", "of", "is", "are", "was", "were", "be", "been", "should"
    };

    public List<ContextChunkDto> RetrieveGloballyRelevantChunks(
        string question,
        IReadOnlyList<DocumentObject> documents,
        int kPerDoc = 5,
        int maxChunks = 5,
        float threshold = 0.25f,
        float vecWeight = 0.65f)
    {
        var allCandidates = new List<(string Text, string Source)>();

        foreach (var doc in documents)
        {
            var searchResults = doc.EmbeddingStore.Search(question, kPerDoc);
            foreach (var res in searchResults)
            {
                allCandidates.Add((res.Text, doc.Filename));
            }
        }

        if (allCandidates.Count == 0)
        {
            return [];
        }

        var seenTexts = new HashSet<string>();
        var uniqueCandidates = new List<(string Text, string Source)>();
        foreach (var cand in allCandidates)
        {
            if (seenTexts.Add(cand.Text))
            {
                uniqueCandidates.Add(cand);
            }
        }

        var embModel = documents[0].EmbeddingStore.Model;
        var candidateTexts = uniqueCandidates.Select(c => c.Text).ToArray();
        var qVec = embModel.Encode(question);
        var cVecs = embModel.EncodeBatch(candidateTexts);

        var finalResults = new List<(float Score, string Text, string Source)>();
        for (var i = 0; i < uniqueCandidates.Count; i++)
        {
            var vScore = CosineSimilarity(cVecs[i], qVec);
            var kScore = CalculateHybridMatch(question, uniqueCandidates[i].Text);
            var hScore = (vScore * vecWeight) + (kScore * (1 - vecWeight));
            if (hScore >= threshold)
            {
                finalResults.Add((hScore, uniqueCandidates[i].Text, uniqueCandidates[i].Source));
            }
        }

        return finalResults
            .OrderByDescending(r => r.Score)
            .Take(maxChunks)
            .Select(r => new ContextChunkDto { Text = r.Text, Source = r.Source })
            .ToList();
    }

    private static float CosineSimilarity(float[] a, float[] b)
    {
        var dot = 0f;
        var normA = 0f;
        var normB = 0f;
        for (var i = 0; i < a.Length; i++)
        {
            dot += a[i] * b[i];
            normA += a[i] * a[i];
            normB += b[i] * b[i];
        }

        var denom = MathF.Sqrt(normA) * MathF.Sqrt(normB);
        return denom <= 0 ? 0f : dot / denom;
    }

    private static float CalculateHybridMatch(string question, string text)
    {
        var words = Regex.Matches(question.ToLowerInvariant(), @"\b\w{3,}\b")
            .Select(m => m.Value)
            .Where(w => !TurkishStops.Contains(w))
            .ToList();

        if (words.Count == 0)
        {
            return 0.5f;
        }

        var weights = new Dictionary<string, float>(StringComparer.OrdinalIgnoreCase);
        var questionWordsOriginal = Regex.Matches(question, @"\b\w{3,}\b").Select(m => m.Value).ToList();
        var wordCaseMap = questionWordsOriginal.ToDictionary(w => w.ToLowerInvariant(), w => w, StringComparer.OrdinalIgnoreCase);

        foreach (var wLower in words)
        {
            var original = wordCaseMap.GetValueOrDefault(wLower, wLower);
            if (char.IsUpper(original[0]))
            {
                weights[wLower] = 3.0f;
            }
            else if (wLower.Length > 6)
            {
                weights[wLower] = 1.5f;
            }
            else
            {
                weights[wLower] = 1.0f;
            }
        }

        var totalWeight = weights.Values.Sum();
        var textLower = text.ToLowerInvariant();
        var score = 0f;
        var penalty = 0f;

        foreach (var (word, weight) in weights)
        {
            if (Regex.IsMatch(textLower, $@"\b{Regex.Escape(word)}\b"))
            {
                score += weight;
            }
            else if (weight >= 3.0f)
            {
                penalty += 1.0f;
            }
        }

        return Math.Max(0f, (score - penalty) / totalWeight);
    }
}
