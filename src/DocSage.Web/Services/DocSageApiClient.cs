using System.Net.Http.Headers;
using System.Net.Http.Json;
using DocSage.Core.Models;

namespace DocSage.Web.Services;

public sealed class DocSageApiClient
{
    private readonly HttpClient _http;

    public DocSageApiClient(HttpClient http)
    {
        _http = http;
    }

    public async Task<UploadDocumentResponse?> UploadDocumentAsync(Stream stream, string fileName, string contentType, CancellationToken cancellationToken = default)
    {
        using var content = new MultipartFormDataContent();
        var fileContent = new StreamContent(stream);
        fileContent.Headers.ContentType = new MediaTypeHeaderValue(contentType);
        content.Add(fileContent, "file", fileName);

        var response = await _http.PostAsync("documents/upload", content, cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            var error = await response.Content.ReadAsStringAsync(cancellationToken);
            throw new HttpRequestException(error);
        }

        return await response.Content.ReadFromJsonAsync<UploadDocumentResponse>(cancellationToken: cancellationToken);
    }

    public async Task<QaResponse?> AskAsync(QuestionRequest request, CancellationToken cancellationToken = default)
    {
        var response = await _http.PostAsJsonAsync("qa", request, cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            var error = await response.Content.ReadAsStringAsync(cancellationToken);
            throw new HttpRequestException(error);
        }

        return await response.Content.ReadFromJsonAsync<QaResponse>(cancellationToken: cancellationToken);
    }

    public async Task<SummarizeResponse?> SummarizeAsync(string docId, CancellationToken cancellationToken = default)
    {
        var response = await _http.PostAsJsonAsync("qa/summarize", new SummarizeRequest { DocId = docId }, cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            var error = await response.Content.ReadAsStringAsync(cancellationToken);
            throw new HttpRequestException(error);
        }

        return await response.Content.ReadFromJsonAsync<SummarizeResponse>(cancellationToken: cancellationToken);
    }
}
