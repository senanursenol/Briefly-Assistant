using DocSage.Core.Models;
using DocSage.Infrastructure.Services;
using Microsoft.AspNetCore.Mvc;

namespace DocSage.Api.Controllers;

[ApiController]
[Route("qa")]
public sealed class QaController : ControllerBase
{
    private readonly InMemoryDocumentStore _documentStore;
    private readonly QaService _qaService;

    public QaController(InMemoryDocumentStore documentStore, QaService qaService)
    {
        _documentStore = documentStore;
        _qaService = qaService;
    }

    [HttpPost]
    public async Task<ActionResult<QaResponse>> Ask([FromBody] QuestionRequest request, CancellationToken cancellationToken)
    {
        var documents = new List<DocumentObject>();
        foreach (var docId in request.DocIds)
        {
            var doc = _documentStore.GetDocumentObject(docId);
            if (doc is null)
            {
                return NotFound($"Doküman bulunamadı: {docId}");
            }

            documents.Add(doc);
        }

        var response = await _qaService.AnswerAsync(request.Question, documents, cancellationToken);
        return Ok(response);
    }

    [HttpPost("summarize")]
    public async Task<ActionResult<SummarizeResponse>> Summarize(
        [FromBody] SummarizeRequest request,
        CancellationToken cancellationToken)
    {
        var doc = _documentStore.GetDocumentObject(request.DocId);
        if (doc is null)
        {
            return NotFound($"Doküman bulunamadı: {request.DocId}");
        }

        var summary = await _qaService.SummarizeAsync(doc, cancellationToken);
        return Ok(new SummarizeResponse { Summary = summary });
    }
}
