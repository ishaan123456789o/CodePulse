import { NextRequest, NextResponse } from "next/server";
export const dynamic = "force-dynamic";
async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  if (path.some((part) => !/^[a-zA-Z0-9_-]+$/.test(part)))
    return NextResponse.json({ detail: "Invalid API path" }, { status: 400 });
  const base = process.env.API_INTERNAL_URL || "http://localhost:8000";
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const workspace = request.headers.get("X-Workspace-Id");
  if (workspace) headers["X-Workspace-Id"] = workspace;
  // Reject cross-origin mutations; no browser secrets or privileged API credentials are forwarded.
  if (request.method !== "GET") {
    const origin = request.headers.get("origin");
    if (origin && new URL(origin).host !== request.headers.get("host"))
      return NextResponse.json(
        { detail: "Cross-origin mutation rejected" },
        { status: 403 },
      );
  }
  try {
    const body = request.method === "POST" ? await request.text() : undefined;
    if (body && body.length > 2048)
      return NextResponse.json(
        { detail: "Request too large" },
        { status: 413 },
      );
    const response = await fetch(
      `${base}/api/v1/${path.join("/")}${request.nextUrl.search}`,
      {
        method: request.method,
        headers,
        body,
        cache: "no-store",
        signal: AbortSignal.timeout(15000),
      },
    );
    return new NextResponse(
      response.status === 204 ? null : await response.text(),
      {
        status: response.status,
        headers: {
          "Content-Type": "application/json",
          "Cache-Control": "no-store",
        },
      },
    );
  } catch {
    return NextResponse.json(
      {
        detail:
          "CodePulse API is unavailable. Start the backend and check Settings.",
      },
      { status: 503 },
    );
  }
}
export { proxy as GET, proxy as POST, proxy as DELETE };
