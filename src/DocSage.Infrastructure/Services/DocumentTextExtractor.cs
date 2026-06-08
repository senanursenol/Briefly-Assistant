using System.Diagnostics;
using System.Text;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;
using UglyToad.PdfPig;

namespace DocSage.Infrastructure.Services;

public static class DocumentTextExtractor
{
    private static readonly Encoding[] TxtEncodings =
    [
        new UTF8Encoding(encoderShouldEmitUTF8Identifier: true),
        Encoding.UTF8,
        Encoding.GetEncoding(1254),
        Encoding.Latin1
    ];

    public static string ExtractText(byte[] content, string ext)
    {
        return ext.ToLowerInvariant() switch
        {
            "pdf" => ExtractFromPdf(content),
            "docx" => ExtractFromDocx(content),
            "txt" => ExtractFromTxt(content),
            "doc" => ExtractFromDoc(content),
            _ => throw new ArgumentException($"Desteklenmeyen dosya formatı: {ext}")
        };
    }

    public static string ExtractFromTxt(byte[] content)
    {
        foreach (var encoding in TxtEncodings)
        {
            try
            {
                return encoding.GetString(content);
            }
            catch (DecoderFallbackException)
            {
                // try next encoding
            }
        }

        return Encoding.UTF8.GetString(content);
    }

    public static string ExtractFromPdf(byte[] content)
    {
        var text = new StringBuilder();
        using var stream = new MemoryStream(content);
        using var document = PdfDocument.Open(stream);
        foreach (var page in document.GetPages())
        {
            var pageText = page.Text;
            if (!string.IsNullOrWhiteSpace(pageText))
            {
                text.AppendLine(pageText);
            }
        }

        return text.ToString();
    }

    public static string ExtractFromDocx(byte[] content)
    {
        using var stream = new MemoryStream(content);
        using var document = WordprocessingDocument.Open(stream, false);
        var body = document.MainDocumentPart?.Document.Body;
        if (body is null)
        {
            return string.Empty;
        }

        var fullText = new List<string>();

        foreach (var para in body.Descendants<Paragraph>())
        {
            var paraText = para.InnerText?.Trim();
            if (!string.IsNullOrWhiteSpace(paraText))
            {
                fullText.Add(paraText);
            }
        }

        foreach (var table in body.Descendants<Table>())
        {
            foreach (var row in table.Descendants<TableRow>())
            {
                foreach (var cell in row.Descendants<TableCell>())
                {
                    var cellText = cell.InnerText?.Trim();
                    if (!string.IsNullOrWhiteSpace(cellText))
                    {
                        fullText.Add(cellText);
                    }
                }
            }
        }

        if (fullText.Count == 0)
        {
            fullText.Add(body.InnerText);
        }

        return string.Join('\n', fullText.Where(t => !string.IsNullOrWhiteSpace(t)));
    }

    public static string ExtractFromDoc(byte[] content)
    {
        var libreText = TryExtractWithLibreOffice(content);
        if (!string.IsNullOrWhiteSpace(libreText))
        {
            return libreText;
        }

        var antiwordText = TryExtractWithAntiword(content);
        if (!string.IsNullOrWhiteSpace(antiwordText))
        {
            return antiwordText;
        }

        throw new InvalidOperationException(
            "DOC dosyası işlenemedi. LibreOffice (soffice) veya antiword kurulu olduğundan emin olun.");
    }

    private static string? TryExtractWithLibreOffice(byte[] content)
    {
        var libreOffice = Environment.GetEnvironmentVariable("LIBREOFFICE_PATH") ?? "soffice";
        return ConvertDocWithExternalTool(content, libreOffice, "--headless --convert-to txt:Text --outdir");
    }

    private static string? TryExtractWithAntiword(byte[] content)
    {
        var antiword = Environment.GetEnvironmentVariable("ANTIWORD_PATH") ?? "antiword";
        var tempDir = Path.Combine(Path.GetTempPath(), "docsage-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(tempDir);

        try
        {
            var inputPath = Path.Combine(tempDir, "input.doc");
            File.WriteAllBytes(inputPath, content);

            var startInfo = new ProcessStartInfo
            {
                FileName = antiword,
                Arguments = $"\"{inputPath}\"",
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            using var process = Process.Start(startInfo);
            if (process is null)
            {
                return null;
            }

            var output = process.StandardOutput.ReadToEnd();
            process.WaitForExit(60_000);
            return process.ExitCode == 0 ? output : null;
        }
        catch
        {
            return null;
        }
        finally
        {
            try
            {
                Directory.Delete(tempDir, recursive: true);
            }
            catch
            {
                // ignore cleanup errors
            }
        }
    }

    private static string? ConvertDocWithExternalTool(byte[] content, string toolPath, string convertArgsPrefix)
    {
        var tempDir = Path.Combine(Path.GetTempPath(), "docsage-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(tempDir);

        try
        {
            var inputPath = Path.Combine(tempDir, "input.doc");
            File.WriteAllBytes(inputPath, content);

            var startInfo = new ProcessStartInfo
            {
                FileName = toolPath,
                Arguments = $"{convertArgsPrefix} \"{tempDir}\" \"{inputPath}\"",
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            using var process = Process.Start(startInfo);
            process?.WaitForExit(120_000);

            var outputPath = Path.Combine(tempDir, "input.txt");
            return File.Exists(outputPath) ? File.ReadAllText(outputPath) : null;
        }
        catch
        {
            return null;
        }
        finally
        {
            try
            {
                Directory.Delete(tempDir, recursive: true);
            }
            catch
            {
                // ignore cleanup errors
            }
        }
    }
}
