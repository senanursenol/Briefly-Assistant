using DocSage.Core.Models;
using DocSage.Infrastructure.Services;
using Microsoft.AspNetCore.Mvc;

namespace DocSage.Api.Controllers;

[ApiController]
[Route("documents")]
public sealed class DocumentsController : ControllerBase
{
    private readonly DocumentUploadService _uploadService;

    public DocumentsController(DocumentUploadService uploadService)
    {
        _uploadService = uploadService;
    }

    [HttpPost("upload")]
    [RequestSizeLimit(50 * 1024 * 1024)]
    public async Task<ActionResult<UploadDocumentResponse>> Upload(IFormFile file, CancellationToken cancellationToken)
    {
        if (file.Length == 0)
        {
            return BadRequest("Boş dosya gönderildi.");
        }

        var filename = file.FileName;
        var parts = filename.Split('.');
        var ext = parts.Length > 1 ? parts[^1].ToLowerInvariant() : string.Empty;

        if (ext is not ("pdf" or "doc" or "docx" or "txt"))
        {
            return BadRequest("Sadece PDF, DOC, DOCX ve TXT dosyaları destekleniyor.");
        }

        try
        {
            await using var stream = file.OpenReadStream();
            var (docId, name, numChunks) = await _uploadService.UploadAsync(stream, filename, cancellationToken);
            return Ok(new UploadDocumentResponse
            {
                DocId = docId,
                Filename = name,
                NumChars = numChunks
            });
        }
        catch (Exception ex)
        {
            return StatusCode(500, $"Dosya işlenirken hata oluştu: {ex.Message}");
        }
    }
}
