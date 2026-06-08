using Microsoft.AspNetCore.Mvc;

namespace DocSage.Api.Controllers;

[ApiController]
public sealed class RootController : ControllerBase
{
    [HttpGet("/")]
    public IActionResult Get() => Ok(new { message = "DocSage API is running correctly!" });
}
