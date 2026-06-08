namespace DocSage.Infrastructure.Services;

public static class TextChunker
{
    public static List<string> SplitIntoChunks(string text, int maxChars = 500, int overlap = 100)
    {
        var chunks = new List<string>();
        var start = 0;
        var textLength = text.Length;

        while (start < textLength)
        {
            var end = Math.Min(start + maxChars, textLength);
            var chunk = text[start..end];
            chunks.Add(chunk.Trim());

            start = end - overlap;
            if (start < 0)
            {
                start = 0;
            }

            if (start >= end)
            {
                start = end;
            }
        }

        return chunks;
    }
}
