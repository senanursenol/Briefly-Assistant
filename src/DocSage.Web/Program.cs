using DocSage.Web.Components;
using DocSage.Web.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();

var backendUrl = builder.Configuration["Backend:Url"]
    ?? Environment.GetEnvironmentVariable("BACKEND_URL")
    ?? "http://localhost:8000";

builder.Services.AddHttpClient<DocSageApiClient>(client =>
{
    client.BaseAddress = new Uri(backendUrl.TrimEnd('/') + "/");
    client.Timeout = TimeSpan.FromMinutes(10);
});

var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseAntiforgery();

app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.Run();
