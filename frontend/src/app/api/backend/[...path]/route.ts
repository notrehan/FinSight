import { NextRequest } from 'next/server'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'
// Retrieval may need to load the embedding model on the first request, then
// wait for a free routed LLM. Leave headroom beyond the provider's own timeout.
export const maxDuration = 120

const allowed = (path: string, method: string) => {
  if (path === 'api/health' || path === 'api/metrics') return method === 'GET'
  if (/^api\/v1\/funds\/(search|nav\/\d+)$/.test(path)) return method === 'GET'
  if (/^api\/v1\/documents\/(tcs|infosys)\/[^/]+\/pdf$/.test(path)) return method === 'GET'
  if (path === 'api/v1/funds/compare') return method === 'POST'
  if (path === 'api/v1/macro') return method === 'GET'
  if (path === 'api/v1/ask' || path === 'api/v1/calculate' || path === 'api/v1/portfolio/analyze' || path === 'api/v1/watchlists/save') return method === 'POST'
  if (/^api\/v1\/prices\/[A-Za-z0-9.-]+$/.test(path)) return method === 'GET'
  if (path === 'api/v1/watchlists' || path === 'api/v1/announcements') return method === 'GET'
  return false
}

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path: parts } = await context.params
  const path = parts.join('/')
  if (!allowed(path, request.method)) return Response.json({ error: 'This API route is not available through the frontend proxy.' }, { status: 404 })
  const base = process.env.FINSIGHT_API_URL?.replace(/\/+$/, '')
  if (!base) return Response.json({ error: 'The Django API is not configured. Set FINSIGHT_API_URL in the frontend environment.' }, { status: 503 })
  const incoming = new URL(request.url)
  const headers = new Headers()
  for (const name of ['accept', 'content-type', 'cookie', 'x-correlation-id']) {
    const value = request.headers.get(name)
    if (value) headers.set(name, value)
  }
  try {
    const upstream = await fetch(base + '/' + path + incoming.search, {
      method: request.method,
      headers,
      body: request.method === 'GET' || request.method === 'HEAD' ? undefined : await request.arrayBuffer(),
      cache: 'no-store',
      signal: AbortSignal.timeout(110_000),
    })
    const responseHeaders = new Headers({ 'Cache-Control': 'no-store' })
    const contentType = upstream.headers.get('content-type')
    if (contentType) responseHeaders.set('content-type', contentType)
    const disposition = upstream.headers.get('content-disposition')
    if (disposition) responseHeaders.set('content-disposition', disposition)
    const correlationId = upstream.headers.get('x-correlation-id')
    if (correlationId) responseHeaders.set('x-correlation-id', correlationId)
    for (const cookie of upstream.headers.getSetCookie()) responseHeaders.append('set-cookie', cookie)
    return new Response(await upstream.arrayBuffer(), { status: upstream.status, headers: responseHeaders })
  } catch (error) {
    const message = error instanceof Error && error.name === 'TimeoutError' ? 'The research service took too long to respond. Please try again.' : 'The research service could not be reached. Check that the Django API is running.'
    return Response.json({ error: message }, { status: 502 })
  }
}

export const GET = proxy
export const POST = proxy
