export default async function handler(req, res) {
  const { url } = req.query
  if (!url) return res.status(400).send('missing url')
  try {
    const r = await fetch(decodeURIComponent(url), {
      headers: { 'User-Agent': 'Mozilla/5.0 (compatible; PeaceEnergy/1.0)' },
      signal: AbortSignal.timeout(8000),
    })
    const text = await r.text()
    res.setHeader('Content-Type', r.headers.get('Content-Type') || 'application/xml')
    res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=600')
    res.status(200).send(text)
  } catch (e) {
    res.status(502).send('upstream error')
  }
}
