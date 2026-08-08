// Same-origin image proxy.
//
// vlr's image CDN (owcdn.net) is fronted by CloudFront with a hotlink guard
// that 403s browser <img> loads coming from a different origin. It keys on the
// browser's Sec-Fetch-Dest/Sec-Fetch-Site request headers (the built-in
// "this is a cross-site image embed" signal), which a web page cannot remove —
// so no client-side trick (referrerPolicy, crossorigin, …) can get past it.
//
// A *server-side* fetch carries none of those headers, so the CDN serves the
// image normally. This route does that fetch and re-serves the bytes from our
// own origin, where <img> loads are same-origin and never blocked. Callers wrap
// URLs with proxyImage() in lib/utils.ts.
import { NextRequest } from 'next/server';

// Restrict to the CDN we actually embed, so this can never become an open proxy.
function allowedHost(hostname: string): boolean {
  return hostname === 'owcdn.net' || hostname.endsWith('.owcdn.net');
}

export async function GET(req: NextRequest) {
  const src = req.nextUrl.searchParams.get('u');
  if (!src) return new Response('missing "u" query param', { status: 400 });

  let target: URL;
  try {
    target = new URL(src);
  } catch {
    return new Response('invalid url', { status: 400 });
  }
  if (target.protocol !== 'https:' || !allowedHost(target.hostname)) {
    return new Response('host not allowed', { status: 403 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(target.toString(), {
      // Present as a vlr.gg request; a server fetch sends no Sec-Fetch-* hints.
      headers: {
        Referer: 'https://www.vlr.gg/',
        'User-Agent': 'Mozilla/5.0 (compatible; vlr-analytics/1.0)',
      },
    });
  } catch {
    return new Response('upstream fetch failed', { status: 502 });
  }

  if (!upstream.ok || !upstream.body) {
    return new Response('upstream error', { status: 502 });
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      'Content-Type': upstream.headers.get('content-type') ?? 'image/png',
      // Images are immutable per URL — cache hard in the browser and on the edge.
      'Cache-Control': 'public, max-age=86400, s-maxage=604800, immutable',
    },
  });
}
