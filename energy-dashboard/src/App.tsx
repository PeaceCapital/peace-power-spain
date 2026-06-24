import { useState, useEffect, useCallback, CSSProperties } from 'react'
import {
  AreaChart, Area, BarChart, Bar, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'

// ── Design tokens ───────────────────────────────────────────────
const PA = {
  bg:      '#0a0a0a',
  surface: '#111111',
  card:    '#1a1a1a',
  border:  '#2a2a2a',
  text:    '#ffffff',
  dim:     '#888888',
  muted:   '#555555',
  amber:   '#f59e0b',
  green:   '#10b981',
  red:     '#ef4444',
  teal:    '#14b8a6',
  blue:    '#3b82f6',
  purple:  '#8b5cf6',
  hv:      '"Helvetica Neue", Helvetica, Arial, sans-serif',
} as const

// ── Types ───────────────────────────────────────────────────────
interface LiveRow {
  ts: string
  omie_price: number
  gen_wind?: number
  gen_solar_pv?: number
  gen_solar_thermal?: number
  gen_hydro?: number
  gen_nuclear?: number
  demand_forecast?: number
  atc_es_fr?: number
  ttf: number
  eua: number
  gen_renewable?: number
  rsi: number
  thermal_floor: number
  floor_discount: number
  regime: string
}

interface Scalars {
  last_spot: number
  last_regime: string
  last_rsi: number
  last_discount: number
  floor_proxy: number
  live_ttf: number
  live_eua: number
  vol_annual: number
  b76_call: number
  mc_call: number
  spike_prob: number
  neg_prob: number
  cur_dir: string
  cur_conf: number
  atc_last?: number
  omip_m1?: number
  omip_q1?: number
  forward_basis?: number
  es_pt_spread?: number
}

interface PricerData {
  last_spot: number
  strike: number
  shift_constant: number
  shifted_f: number
  sigma: number
  T: number
  r: number
  b76_call: number
  mc_call: number
  mc_se: number
  b76_vs_mc: number
  spike_prob: number
  neg_price_prob: number
  vol_annual: number
  vol_daily: number
  vol_hourly: number
  vol_normal_min: number
  vol_normal_max: number
  price_vs_floor: number
  floor_proxy: number
  mc_payoff: { midpoints: number[]; counts: number[]; itm_count: number; itm_pct: number }
  percentiles: Record<string, number>
  rolling_vol: { ts: string; vol: number }[]
}

interface LiveData {
  live: LiveRow[]
  scalars: Scalars
  pricer: PricerData | null
  updated_at: string
}

interface NewsItem {
  title: string
  link: string
  source: string
  ago: string
  topic: string
  topicColor: string
  topicTag: string
}

// ── News config ─────────────────────────────────────────────────
const NEWS_TOPICS = [
  { label: 'Gas & Oil',    query: 'TTF+natural+gas+LNG+oil+energy+europe+spain',           color: PA.amber,  tag: 'GAS' },
  { label: 'Renewables',  query: 'solar+wind+renewable+energy+europe+spain+offshore',      color: PA.green,  tag: 'RNW' },
  { label: 'BESS',        query: 'battery+energy+storage+BESS+grid+lithium',               color: PA.teal,   tag: 'BSS' },
  { label: 'Nuclear',     query: 'nuclear+energy+power+plant+europe+spain+SMR',            color: PA.blue,   tag: 'NUC' },
  { label: 'Carbon',      query: 'EUA+carbon+EU+ETS+emissions+trading+carbon+price',       color: PA.purple, tag: 'C02' },
  { label: 'OMIE & REE',  query: 'OMIE+REE+electricity+spain+iberia+power+market+precio', color: PA.red,    tag: 'MKT' },
  { label: 'EU Markets',  query: 'EPEX+european+power+electricity+market+futures+OMIP',    color: '#60a5fa', tag: 'EUR' },
  { label: 'Hydrogen',    query: 'green+hydrogen+electrolysis+H2+electrolyser+spain',      color: '#34d399', tag: 'H2'  },
]

// ── Hooks ───────────────────────────────────────────────────────
function useLiveData() {
  const [data, setData]   = useState<LiveData | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const r = await fetch('/live_data.json?t=' + Date.now())
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      setData(await r.json())
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load data')
    }
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, 60_000)
    return () => clearInterval(id)
  }, [load])

  return { data, error, reload: load }
}

function useTTFLive() {
  const [price, setPrice] = useState<number | null>(null)

  useEffect(() => {
    async function fetch_() {
      try {
        const url = 'https://corsproxy.io/?https://query1.finance.yahoo.com/v8/finance/chart/TTF%3DF'
        const r   = await fetch(url)
        const j   = await r.json()
        const p   = j?.chart?.result?.[0]?.meta?.regularMarketPrice as number | undefined
        if (p) setPrice(p)
      } catch { /* silently degrade */ }
    }
    fetch_()
    const id = setInterval(fetch_, 300_000)
    return () => clearInterval(id)
  }, [])

  return price
}

function useNews() {
  const [feeds,    setFeeds]    = useState<{ label: string; color: string; tag: string; items: NewsItem[] }[]>([])
  const [allItems, setAllItems] = useState<NewsItem[]>([])
  const [loading,  setLoading]  = useState(true)

  useEffect(() => {
    const BASE = 'https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q='

    async function fetchTopic(t: typeof NEWS_TOPICS[0]): Promise<NewsItem[]> {
      try {
        const rssUrl = encodeURIComponent(BASE + t.query)
        const r = await fetch(`https://api.rss2json.com/v1/api.json?rss_url=${rssUrl}`)
        const j = await r.json()
        if (j.status !== 'ok') return []
        return (j.items as Record<string, string>[] || []).slice(0, 8).map(item => ({
          title:      (item.title || '').replace(/ - [^-]+$/, '').trim(),
          link:       item.link || '#',
          source:     item.author || '—',
          ago:        getAgo(item.pubDate || ''),
          topic:      t.label,
          topicColor: t.color,
          topicTag:   t.tag,
        }))
      } catch { return [] }
    }

    async function fetchAll() {
      setLoading(true)
      const results  = await Promise.all(NEWS_TOPICS.map(fetchTopic))
      const newFeeds = NEWS_TOPICS.map((t, i) => ({ label: t.label, color: t.color, tag: t.tag, items: results[i] }))
      setFeeds(newFeeds)
      const all = newFeeds.flatMap(f => f.items).sort((a, b) => agoMinutes(a.ago) - agoMinutes(b.ago))
      setAllItems(all)
      setLoading(false)
    }

    fetchAll()
    const id = setInterval(fetchAll, 1_800_000)
    return () => clearInterval(id)
  }, [])

  return { feeds, allItems, loading }
}

// ── Helpers ─────────────────────────────────────────────────────
function getAgo(pubDate: string): string {
  try {
    const delta = (Date.now() - new Date(pubDate).getTime()) / 1000
    const m = Math.floor(delta / 60)
    if (m < 60) return `${m}m`
    const h = Math.floor(m / 60)
    if (h < 24) return `${h}h`
    return `${Math.floor(h / 24)}d`
  } catch { return '—' }
}

function agoMinutes(ago: string): number {
  if (ago === '—') return 99999
  if (ago.endsWith('m')) return parseInt(ago)
  if (ago.endsWith('h')) return parseInt(ago) * 60
  if (ago.endsWith('d')) return parseInt(ago) * 1440
  return 99999
}

function fmtTs(ts: string): string {
  try { return new Date(ts).toLocaleDateString('en-GB', { month: 'short', day: 'numeric' }) }
  catch { return ts }
}

function regimeColor(regime: string): string {
  if (regime === 'Renewable-Dom.') return PA.green
  if (regime === 'Demand-Stress')  return PA.red
  return PA.amber
}

function dirColor(dir: string): string {
  if (dir === 'LONG')  return PA.green
  if (dir === 'SHORT') return PA.red
  return PA.dim
}

function filterByDays(live: LiveRow[], days: number): LiveRow[] {
  if (!live.length) return live
  const cutoff = new Date(live[live.length - 1].ts).getTime() - days * 86_400_000
  return live.filter(r => new Date(r.ts).getTime() >= cutoff)
}

// ── Recharts custom tooltip ──────────────────────────────────────
interface TooltipPayloadEntry { name: string; value: number; color: string }
function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: TooltipPayloadEntry[]; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: PA.card, border: `1px solid ${PA.border}`, borderRadius: 4, padding: '8px 12px', fontFamily: PA.hv, fontSize: 11 }}>
      <div style={{ color: PA.dim, marginBottom: 4, fontWeight: 300 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, marginBottom: 2, fontWeight: 400 }}>
          {p.name}: <strong style={{ fontWeight: 700 }}>{typeof p.value === 'number' ? p.value.toFixed(2) : p.value}</strong>
        </div>
      ))}
    </div>
  )
}

// ── UI primitives ───────────────────────────────────────────────
function SectionHeader({ children }: { children: string }) {
  return (
    <div style={{
      fontFamily: PA.hv, fontSize: 11, fontWeight: 700,
      textTransform: 'uppercase', letterSpacing: '0.1em',
      color: PA.amber, marginBottom: 20, paddingBottom: 8,
      borderBottom: `2px solid ${PA.border}`,
    }}>
      {children}
    </div>
  )
}

function DataRow({ label, value, color = PA.text }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '11px 0', borderBottom: `1px solid ${PA.border}` }}>
      <span style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: 300, color: PA.dim }}>{label}</span>
      <span style={{ fontFamily: PA.hv, fontSize: 13, fontWeight: 700, color }}>{value}</span>
    </div>
  )
}

function Tag({ label, color }: { label: string; color: string }) {
  return (
    <span style={{ fontFamily: PA.hv, fontSize: 8, fontWeight: 700, letterSpacing: '0.1em', border: `1px solid ${color}`, color, padding: '1px 6px' }}>
      {label}
    </span>
  )
}

// ── Header ──────────────────────────────────────────────────────
function Header({ dataSource, updatedAt }: { dataSource: string; updatedAt: string }) {
  const [now, setNow] = useState(() => {
    const d = new Date()
    return `${d.getDate()} ${d.toLocaleString('en-GB', { month: 'short' })} ${d.getFullYear()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
  })
  useEffect(() => {
    const id = setInterval(() => {
      const d = new Date()
      setNow(`${d.getDate()} ${d.toLocaleString('en-GB', { month: 'short' })} ${d.getFullYear()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`)
    }, 30_000)
    return () => clearInterval(id)
  }, [])
  const live = dataSource === 'ESIOS LIVE'
  const dotColor = live ? PA.green : PA.amber
  return (
    <div style={{ background: PA.surface, borderBottom: `1px solid ${PA.border}`, padding: '0 32px', height: 54, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
        <div style={{ fontFamily: PA.hv, fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>
          Peace<span style={{ color: PA.amber }}>*</span>
          <span style={{ fontWeight: 300, color: PA.dim }}> Capital</span>
        </div>
        <div style={{ width: 1, height: 18, background: PA.border, margin: '0 20px' }} />
        <span style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: 300, color: PA.dim }}>Iberia Signal Engine</span>
        <div style={{ marginLeft: 20, display: 'inline-flex', alignItems: 'center', gap: 7, fontFamily: PA.hv, fontSize: 11, fontWeight: 700, letterSpacing: '0.05em', color: dotColor }}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: dotColor, display: 'inline-block', animation: 'pulse 2s infinite' }} />
          {dataSource}
        </div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: 300, color: PA.dim }}>{now}</div>
        {updatedAt && (
          <div style={{ fontFamily: PA.hv, fontSize: 10, fontWeight: 700, color: PA.muted, letterSpacing: '0.05em', marginTop: 2 }}>
            REF PC-NRG-2026
          </div>
        )}
      </div>
    </div>
  )
}

// ── Scrolling ticker ─────────────────────────────────────────────
function ScrollingTicker({ items }: { items: { label: string; value: string; color: string }[] }) {
  if (!items.length) return null
  const doubled = [...items, ...items]
  return (
    <div style={{ background: '#080808', borderBottom: `1px solid ${PA.border}`, height: 34, overflow: 'hidden', display: 'flex', alignItems: 'center' }}>
      <div style={{ display: 'inline-flex', alignItems: 'center', whiteSpace: 'nowrap', animation: 'ticker 40s linear infinite' }}>
        {doubled.map((item, i) => (
          <span key={i} style={{ display: 'inline-flex', alignItems: 'center' }}>
            <span style={{ fontFamily: PA.hv, fontSize: 10, fontWeight: 300, color: PA.muted, margin: '0 14px' }}>●</span>
            <span style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 700, color: PA.dim, letterSpacing: '0.06em', textTransform: 'uppercase', marginRight: 6 }}>{item.label}</span>
            <span style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: 700, color: item.color }}>{item.value}</span>
          </span>
        ))}
      </div>
    </div>
  )
}

// ── Stats bar (static grid, always visible) ───────────────────────
function StatsBar({ items }: { items: { label: string; value: string; color: string }[] }) {
  if (!items.length) return null
  return (
    <div style={{ background: '#0d0d0d', borderBottom: `1px solid ${PA.border}`, display: 'flex' }}>
      {items.map((item, i) => (
        <div key={i} style={{
          flex: 1, padding: '10px 20px',
          borderRight: i < items.length - 1 ? `1px solid ${PA.border}` : 'none',
        }}>
          <div style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 300, color: PA.dim, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>{item.label}</div>
          <div style={{ fontFamily: PA.hv, fontSize: 13, fontWeight: 700, color: item.color }}>{item.value}</div>
        </div>
      ))}
    </div>
  )
}

// ── Signal card (shown on Signal tab) ───────────────────────────
function SignalCard({ s }: { s: Scalars }) {
  const dc  = s.last_discount < 0 ? PA.red : PA.green
  const ddc = dirColor(s.cur_dir)
  return (
    <div style={{
      background: `linear-gradient(135deg, ${PA.card} 0%, ${PA.surface} 100%)`,
      border: `1px solid ${PA.border}`, borderLeft: `4px solid ${PA.amber}`,
      borderRadius: 8, padding: 24,
    }}>
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 12px', background: 'rgba(245,158,11,0.1)', border: `1px solid ${PA.amber}`, borderRadius: 6, fontFamily: PA.hv, fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: PA.amber, marginBottom: 16 }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'currentColor', animation: 'pulse 2s infinite', display: 'inline-block' }} />
        Live Signal
      </div>
      <div style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', color: regimeColor(s.last_regime), marginBottom: 8 }}>
        IBERIA POWER · {s.last_regime.toUpperCase()}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontFamily: PA.hv, fontSize: 28, fontWeight: 700, marginBottom: 8 }}>
            OMIE {s.last_spot.toFixed(2)}{' '}
            <span style={{ fontSize: 14, fontWeight: 300, color: PA.dim }}>EUR/MWh</span>
          </div>
          <div style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: 300, color: PA.dim }}>
            Floor {s.floor_proxy.toFixed(2)} · TTF {s.live_ttf.toFixed(2)} · EUA {s.live_eua.toFixed(0)} €/t
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontFamily: PA.hv, fontSize: 10, fontWeight: 300, color: PA.dim, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>Signal</div>
          <div style={{ fontFamily: PA.hv, fontSize: 40, fontWeight: 700, color: ddc, lineHeight: 1 }}>{s.cur_dir}</div>
          <div style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: 700, color: dc, marginTop: 4 }}>{s.last_discount >= 0 ? '+' : ''}{s.last_discount.toFixed(2)} disc</div>
        </div>
      </div>
      <div style={{ marginTop: 24, paddingTop: 24, borderTop: `1px solid ${PA.border}` }}>
        <DataRow label="RSI · Renewable / Demand"       value={s.last_rsi.toFixed(2)}                                           color={PA.dim}    />
        <DataRow label="Thermal Floor · CCGT 50%"       value={`${s.floor_proxy.toFixed(2)} €/MWh`}                             color={PA.blue}   />
        <DataRow label="Floor Discount · Spot vs Floor" value={`${s.last_discount >= 0 ? '+' : ''}${s.last_discount.toFixed(2)} €/MWh`} color={dc} />
        <DataRow label="TTF Natural Gas · front-month"  value={`${s.live_ttf.toFixed(2)} €/MWh`}                                color={PA.amber}  />
        <DataRow label="EUA Carbon · EUR/tCO₂"          value={`${s.live_eua.toFixed(0)} €/t`}                                  color={PA.purple} />
        <DataRow label="Confidence"                     value={s.cur_conf.toFixed(2)}                                           color={PA.teal}   />
      </div>
    </div>
  )
}

// ── Metric grid ─────────────────────────────────────────────────
function MetricGrid({ metrics }: { metrics: { label: string; value: string; color: string }[] }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
      {metrics.map((m, i) => (
        <div key={i} style={{ background: PA.surface, border: `1px solid ${PA.border}`, borderRadius: 6, padding: 16 }}>
          <div style={{ fontFamily: PA.hv, fontSize: 10, fontWeight: 700, color: PA.dim, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>{m.label}</div>
          <div style={{ fontFamily: PA.hv, fontSize: 22, fontWeight: 700, color: m.color }}>{m.value}</div>
        </div>
      ))}
    </div>
  )
}

// ── Math helpers (in-browser Black-76) ──────────────────────────
function normCDF(x: number): number {
  const t = 1 / (1 + 0.2316419 * Math.abs(x))
  const d = 0.3989422820 * Math.exp(-x * x / 2)
  const p = t * (0.3193815309 + t * (-0.3565637851 + t * (1.7814779370 + t * (-1.8212559800 + t * 1.3302744290))))
  const cdf = 1 - d * p
  return x > 0 ? cdf : 1 - cdf
}
function b76Call(F: number, K: number, sigma: number, T: number, r = 0): number {
  if (T <= 0) return Math.exp(-r * 0) * Math.max(0, F - K)
  if (sigma <= 0 || F <= 0 || K <= 0) return Math.exp(-r * T) * Math.max(0, F - K)
  const sqT = Math.sqrt(T)
  const d1  = (Math.log(F / K) + 0.5 * sigma * sigma * T) / (sigma * sqT)
  const d2  = d1 - sigma * sqT
  return Math.exp(-r * T) * (F * normCDF(d1) - K * normCDF(d2))
}
function b76Delta(F: number, K: number, sigma: number, T: number, r = 0): number {
  if (T <= 0 || sigma <= 0 || F <= 0 || K <= 0) return F > K ? 1 : 0
  const d1 = (Math.log(F / K) + 0.5 * sigma * sigma * T) / (sigma * Math.sqrt(T))
  return Math.exp(-r * T) * normCDF(d1)
}
function b76Vega(F: number, K: number, sigma: number, T: number, r = 0): number {
  if (T <= 0 || sigma <= 0 || F <= 0 || K <= 0) return 0
  const d1  = (Math.log(F / K) + 0.5 * sigma * sigma * T) / (sigma * Math.sqrt(T))
  const pdf = Math.exp(-0.5 * d1 * d1) / Math.sqrt(2 * Math.PI)
  return Math.exp(-r * T) * F * pdf * Math.sqrt(T) / 100  // per 1% vol move
}

// ── Paper trade store (session-only) ────────────────────────────
interface PaperTrade {
  id: number; ts: string; dir: 'LONG' | 'SHORT'; size: number
  entry: number; exit: number | null; pnl: number | null; status: 'OPEN' | 'CLOSED'
}
const paperTrades: PaperTrade[] = []
let tradeIdSeq = 1

// ── Tab bar ─────────────────────────────────────────────────────
const TABS = ['Signal', 'Charts', 'Analysis', 'Pricer', 'SarAI', 'Execution', 'Readiness', 'News'] as const
type Tab = typeof TABS[number]

function TabBar({ active, onSelect }: { active: Tab; onSelect: (t: Tab) => void }) {
  return (
    <div style={{ background: PA.surface, borderBottom: `1px solid ${PA.border}`, display: 'flex', padding: '0 32px' }}>
      {TABS.map(t => (
        <button key={t} onClick={() => onSelect(t)} style={{
          background: 'transparent', border: 'none', cursor: 'pointer',
          fontFamily: PA.hv, fontSize: 13,
          fontWeight: active === t ? 700 : 400,
          color: active === t ? PA.text : PA.dim,
          borderBottom: `2px solid ${active === t ? PA.amber : 'transparent'}`,
          padding: '0 24px', height: 48, transition: 'all 0.15s',
        }}>
          {t}
        </button>
      ))}
    </div>
  )
}

// ── Chart range picker ──────────────────────────────────────────
type DayRange = 7 | 14 | 30
function RangePicker({ value, onChange }: { value: DayRange; onChange: (d: DayRange) => void }) {
  const opts: DayRange[] = [7, 14, 30]
  return (
    <div style={{ display: 'flex', gap: 1, marginBottom: 24 }}>
      {opts.map(d => (
        <button key={d} onClick={() => onChange(d)} style={{
          background: value === d ? PA.amber : 'transparent',
          border: `1px solid ${value === d ? PA.amber : PA.border}`,
          color: value === d ? '#000' : PA.dim,
          fontFamily: PA.hv, fontSize: 11, fontWeight: 700,
          padding: '4px 14px', cursor: 'pointer',
          borderRadius: d === 7 ? '4px 0 0 4px' : d === 30 ? '0 4px 4px 0' : 0,
        }}>
          {d}D
        </button>
      ))}
    </div>
  )
}

// ── Charts tab ──────────────────────────────────────────────────
function ChartsTab({ live }: { live: LiveRow[] }) {
  const [days, setDays] = useState<DayRange>(14)
  const [showDemand, setShowDemand] = useState(true)

  const sliced  = filterByDays(live, days)
  const sample  = sliced.filter((_, i) => i % 3 === 0)

  const spotFloorData = sample.map(r => ({ ts: fmtTs(r.ts), Spot: r.omie_price, Floor: r.thermal_floor }))
  const discountData  = sample.map(r => ({ ts: fmtTs(r.ts), Discount: r.floor_discount }))
  const genData       = sample.map(r => ({
    ts:            fmtTs(r.ts),
    Wind:          r.gen_wind ?? 0,
    'Solar PV':    r.gen_solar_pv ?? 0,
    'Solar Therm': r.gen_solar_thermal ?? 0,
    Hydro:         r.gen_hydro ?? 0,
    Nuclear:       r.gen_nuclear ?? 0,
    Demand:        r.demand_forecast ?? 0,
  }))
  const rsiData = sample.map(r => ({ ts: fmtTs(r.ts), RSI: r.rsi }))

  const axisStyle = { fill: PA.dim, fontSize: 9, fontFamily: PA.hv }
  const gridProps = { stroke: PA.border, strokeDasharray: '0' as const }
  const chartBg: CSSProperties = { background: 'transparent' }

  const gradients = (
    <defs>
      <linearGradient id="gSpot"  x1="0" y1="0" x2="0" y2="1">
        <stop offset="5%"  stopColor={PA.amber} stopOpacity={0.18} />
        <stop offset="95%" stopColor={PA.amber} stopOpacity={0} />
      </linearGradient>
      <linearGradient id="gFloor" x1="0" y1="0" x2="0" y2="1">
        <stop offset="5%"  stopColor={PA.teal}  stopOpacity={0.1} />
        <stop offset="95%" stopColor={PA.teal}  stopOpacity={0} />
      </linearGradient>
      <linearGradient id="gRSI"   x1="0" y1="0" x2="0" y2="1">
        <stop offset="5%"  stopColor={PA.teal}  stopOpacity={0.2} />
        <stop offset="95%" stopColor={PA.teal}  stopOpacity={0} />
      </linearGradient>
    </defs>
  )

  return (
    <div style={{ padding: 32 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 0 }}>
        <RangePicker value={days} onChange={setDays} />
        <label style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 400, color: PA.dim, display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
          <input type="checkbox" checked={showDemand} onChange={e => setShowDemand(e.target.checked)} style={{ accentColor: PA.amber }} />
          Show demand on generation chart
        </label>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32, marginBottom: 32 }}>
        {/* Spot vs Floor */}
        <div>
          <SectionHeader>OMIE Spot vs Thermal Floor</SectionHeader>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={spotFloorData} style={chartBg}>
              {gradients}
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="ts" tick={axisStyle} tickLine={false} axisLine={{ stroke: PA.border }} interval="preserveStartEnd" />
              <YAxis tick={axisStyle} tickLine={false} axisLine={{ stroke: PA.border }} width={58} tickFormatter={v => `${v}€`} />
              <Tooltip content={<ChartTooltip />} />
              <Legend wrapperStyle={{ fontFamily: PA.hv, fontSize: 10, fontWeight: 400, color: PA.dim }} />
              <Area type="monotone" dataKey="Spot"  stroke={PA.amber} fill="url(#gSpot)"  strokeWidth={2}   dot={false} />
              <Area type="monotone" dataKey="Floor" stroke={PA.teal}  fill="url(#gFloor)" strokeWidth={1.5} dot={false} strokeDasharray="4 4" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Floor Discount */}
        <div>
          <SectionHeader>Floor Discount (EUR/MWh)</SectionHeader>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={discountData} style={chartBg}>
              <CartesianGrid {...gridProps} vertical={false} />
              <XAxis dataKey="ts" tick={axisStyle} tickLine={false} axisLine={{ stroke: PA.border }} interval="preserveStartEnd" />
              <YAxis tick={axisStyle} tickLine={false} axisLine={{ stroke: PA.border }} width={58} tickFormatter={v => `${v}€`} />
              <Tooltip content={<ChartTooltip />} />
              <ReferenceLine y={0} stroke={PA.border} strokeWidth={1.5} />
              <Bar dataKey="Discount" name="Floor Discount" radius={0}>
                {discountData.map((entry, i) => (
                  <Cell key={i} fill={entry.Discount < 0 ? PA.red : PA.green} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32 }}>
        {/* Generation mix */}
        <div>
          <SectionHeader>Generation Mix (MWh/h)</SectionHeader>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={genData} style={chartBg}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="ts" tick={axisStyle} tickLine={false} axisLine={{ stroke: PA.border }} interval="preserveStartEnd" />
              <YAxis tick={axisStyle} tickLine={false} axisLine={{ stroke: PA.border }} width={65} tickFormatter={v => `${(v / 1000).toFixed(0)}GW`} />
              <Tooltip content={<ChartTooltip />} />
              <Legend wrapperStyle={{ fontFamily: PA.hv, fontSize: 10, fontWeight: 400, color: PA.dim }} />
              <Area type="monotone" dataKey="Wind"          stackId="1" stroke="#3a8fd1"  fill="rgba(58,143,209,0.5)"  strokeWidth={0.5} dot={false} />
              <Area type="monotone" dataKey="Solar PV"      stackId="1" stroke={PA.amber} fill="rgba(245,158,11,0.5)" strokeWidth={0.5} dot={false} />
              <Area type="monotone" dataKey="Solar Therm"   stackId="1" stroke="#e67e22"  fill="rgba(230,126,34,0.5)"  strokeWidth={0.5} dot={false} />
              <Area type="monotone" dataKey="Hydro"         stackId="1" stroke={PA.teal}  fill="rgba(20,184,166,0.5)" strokeWidth={0.5} dot={false} />
              <Area type="monotone" dataKey="Nuclear"       stackId="1" stroke={PA.purple} fill="rgba(139,92,246,0.5)" strokeWidth={0.5} dot={false} />
              {showDemand && <Area type="monotone" dataKey="Demand" stackId="2" stroke={PA.red} fill="none" strokeWidth={1.5} dot={false} strokeDasharray="4 3" />}
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* RSI */}
        <div>
          <SectionHeader>Renewable Surplus Index</SectionHeader>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={rsiData} style={chartBg}>
              {gradients}
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="ts" tick={axisStyle} tickLine={false} axisLine={{ stroke: PA.border }} interval="preserveStartEnd" />
              <YAxis tick={axisStyle} tickLine={false} axisLine={{ stroke: PA.border }} width={58} domain={[0, 1.2]} />
              <Tooltip content={<ChartTooltip />} />
              <ReferenceLine y={0.6} stroke={PA.red} strokeDasharray="4 4" strokeWidth={1} label={{ value: 'Renewable threshold', position: 'insideTopRight', fontSize: 9, fill: PA.dim, fontFamily: PA.hv }} />
              <Area type="monotone" dataKey="RSI" stroke={PA.teal} fill="url(#gRSI)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

// ── Compact news feed (used inline on Signal tab) ────────────────
function NewsFeedPanel({ allItems, loading }: { allItems: NewsItem[]; loading: boolean }) {
  if (loading && allItems.length === 0) {
    return <div style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: 300, color: PA.muted }}>Fetching feeds…</div>
  }
  return (
    <div style={{ maxHeight: 620, overflowY: 'auto', paddingRight: 4 }}>
      {allItems.slice(0, 25).map((item, i) => (
        <div key={i} style={{ paddingBottom: 14, marginBottom: 14, borderBottom: `1px solid ${PA.border}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
            <Tag label={item.topicTag} color={item.topicColor} />
            <span style={{ fontFamily: PA.hv, fontSize: 10, fontWeight: 300, color: PA.dim }}>{item.source.toUpperCase().slice(0, 24)}</span>
            <span style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 300, color: PA.muted, marginLeft: 'auto' }}>{item.ago}</span>
          </div>
          <a href={item.link} target="_blank" rel="noopener noreferrer"
            style={{ fontFamily: PA.hv, fontWeight: 700, fontSize: 12, color: PA.text, textDecoration: 'none', lineHeight: 1.45, display: 'block' }}>
            {item.title}
          </a>
        </div>
      ))}
      {allItems.length === 0 && !loading && (
        <div style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.muted }}>No articles loaded yet.</div>
      )}
    </div>
  )
}

// ── Signal tab ──────────────────────────────────────────────────
function SignalTab({ s, allItems, loading }: { s: Scalars; allItems: NewsItem[]; loading: boolean }) {
  const dc = s.last_discount < 0 ? PA.red : PA.green
  return (
    <div style={{ padding: 32, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32 }}>
      {/* Left: signal card + metrics + thesis */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <SignalCard s={s} />
        <div>
          <SectionHeader>Key Metrics</SectionHeader>
          <MetricGrid metrics={[
            { label: 'OMIE Spot',      value: `${s.last_spot.toFixed(0)} €`,               color: PA.amber  },
            { label: 'Thermal Floor',  value: `${s.floor_proxy.toFixed(2)} €`,              color: PA.blue   },
            { label: 'Floor Discount', value: `${s.last_discount >= 0 ? '+' : ''}${s.last_discount.toFixed(2)} €`, color: dc },
            { label: 'TTF Gas',        value: `${s.live_ttf.toFixed(2)} €`,                 color: PA.amber  },
            { label: 'EUA Carbon',     value: `${s.live_eua.toFixed(0)} €`,                 color: PA.purple },
            { label: 'Confidence',     value: s.cur_conf.toFixed(2),                        color: PA.teal   },
          ]} />
        </div>
        <div>
          <SectionHeader>Working Thesis</SectionHeader>
          <p style={{ fontFamily: PA.hv, fontSize: 13, fontWeight: 300, color: PA.dim, lineHeight: 1.7 }}>
            {s.last_discount < -10 && s.last_rsi > 0.5
              ? `Gas floor ${s.floor_proxy.toFixed(0)} EUR/MWh above spot — SHORT edge; RSI ${s.last_rsi.toFixed(2)} · thermal-dominant regime.`
              : s.last_discount > 15
              ? `Demand stress — spot ${s.last_spot.toFixed(0)} EUR/MWh is ${s.last_discount.toFixed(0)}€ above gas floor. LONG thesis intact.`
              : s.last_rsi > 0.65
              ? `Renewable dominance. RSI ${s.last_rsi.toFixed(2)} above threshold. Thermal no longer marginal — monitor negative price risk.`
              : `Thermal-Marginal regime holds. Gas floor ${s.floor_proxy.toFixed(0)} EUR/MWh shapes OMIE spread. ${s.cur_dir} with ${s.cur_conf.toFixed(2)} confidence.`
            }
          </p>
        </div>
      </div>

      {/* Right: live news feed */}
      <div>
        <SectionHeader>Live Wire · Iberian Energy</SectionHeader>
        <NewsFeedPanel allItems={allItems} loading={loading} />
      </div>
    </div>
  )
}

// ── Analysis tab ─────────────────────────────────────────────────
function AnalysisTab({ live, s }: { live: LiveRow[]; s: Scalars }) {
  const [days, setDays] = useState<DayRange>(14)
  const sliced   = filterByDays(live, days)
  const sample   = sliced.filter((_, i) => i % 3 === 0)
  const atcData  = sample.map(r => ({ ts: fmtTs(r.ts), 'ATC ES→FR': r.atc_es_fr ?? 0 }))
  const axisStyle = { fill: PA.dim, fontSize: 9, fontFamily: PA.hv }

  return (
    <div style={{ padding: 32 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32 }}>

        {/* Left: full data table */}
        <div>
          <SectionHeader>Signal Readout</SectionHeader>
          <DataRow label="Regime"          value={s.last_regime}                                                      color={regimeColor(s.last_regime)} />
          <DataRow label="Direction"       value={s.cur_dir}                                                          color={dirColor(s.cur_dir)}        />
          <DataRow label="Confidence"      value={s.cur_conf.toFixed(2)}                                              color={PA.teal}                    />
          <DataRow label="OMIE Spot"       value={`${s.last_spot.toFixed(2)} EUR/MWh`}                                color={PA.amber}                   />
          <DataRow label="Thermal Floor"   value={`${s.floor_proxy.toFixed(2)} EUR/MWh`}                              color={PA.blue}                    />
          <DataRow label="Floor Discount"  value={`${s.last_discount >= 0 ? '+' : ''}${s.last_discount.toFixed(2)} EUR/MWh`} color={s.last_discount < 0 ? PA.red : PA.green} />
          <DataRow label="RSI"             value={s.last_rsi.toFixed(2)}                                              color={PA.teal}                    />
          <DataRow label="TTF Gas"         value={`${s.live_ttf.toFixed(2)} EUR/MWh`}                                 color={PA.amber}                   />
          <DataRow label="EUA Carbon"      value={`${s.live_eua.toFixed(0)} EUR/tCO₂`}                                color={PA.purple}                  />
          <DataRow label="Ann. Volatility" value={`${(s.vol_annual * 100).toFixed(1)}%`}                              color={PA.dim}                     />
          <DataRow label="Black-76 Call"   value={`${s.b76_call.toFixed(2)} EUR/MWh`}                                 color={PA.dim}                     />
          <DataRow label="MC Call"         value={`${s.mc_call.toFixed(2)} EUR/MWh`}                                  color={PA.dim}                     />
          <DataRow label="Spike Prob"      value={s.spike_prob.toFixed(2)}                                            color={s.spike_prob > 0.1 ? PA.amber : PA.dim} />
          <DataRow label="ATC ES→FR"    value={s.atc_last      !== undefined ? `${s.atc_last.toFixed(0)} MW`                                                        : '—'} color={s.atc_last      !== undefined ? PA.blue                                                                   : PA.muted} />
          <DataRow label="OMIP M+1"    value={s.omip_m1      !== undefined ? `${s.omip_m1.toFixed(2)} €/MWh`                                                  : 'Pending — re-run refresh script'} color={s.omip_m1      !== undefined ? PA.teal  : PA.muted} />
          <DataRow label="OMIP Q+1"    value={s.omip_q1      !== undefined ? `${s.omip_q1.toFixed(2)} €/MWh`                                                  : 'Pending'} color={s.omip_q1      !== undefined ? PA.teal  : PA.muted} />
          <DataRow label="Fwd Basis"   value={s.forward_basis !== undefined ? `${s.forward_basis >= 0 ? '+' : ''}${s.forward_basis.toFixed(2)} €/MWh`         : 'Pending'} color={s.forward_basis !== undefined ? (s.forward_basis < -5 ? PA.red : s.forward_basis > 5 ? PA.green : PA.dim) : PA.muted} />
          <DataRow label="ES–PT Spread" value={s.es_pt_spread !== undefined ? `${s.es_pt_spread.toFixed(2)} €/MWh`                                             : 'Pending'} color={s.es_pt_spread  !== undefined ? (s.es_pt_spread > 5 ? PA.amber : PA.dim)                        : PA.muted} />

          <div style={{ marginTop: 28 }}>
            <SectionHeader>Regime Distribution — {days}D</SectionHeader>
            <RangePicker value={days} onChange={setDays} />
            {(['Thermal-Marginal', 'Renewable-Dom.', 'Demand-Stress'] as const).map(r => {
              const count = sliced.filter(row => row.regime === r).length
              const pct   = sliced.length ? (count / sliced.length) * 100 : 0
              return (
                <div key={r} style={{ marginBottom: 14 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                    <span style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 400, color: regimeColor(r) }}>{r}</span>
                    <span style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 700, color: PA.dim }}>{pct.toFixed(1)}%</span>
                  </div>
                  <div style={{ background: PA.border, borderRadius: 2, height: 4 }}>
                    <div style={{ background: regimeColor(r), width: `${pct}%`, height: '100%', borderRadius: 2, transition: 'width 0.4s ease' }} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Right: ATC chart + thesis */}
        <div>
          <SectionHeader>ATC ES→FR Interconnector (MW)</SectionHeader>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={atcData}>
              <defs>
                <linearGradient id="gATC" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={PA.blue} stopOpacity={0.15} />
                  <stop offset="95%" stopColor={PA.blue} stopOpacity={0}    />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={PA.border} strokeDasharray="0" />
              <XAxis dataKey="ts" tick={axisStyle} tickLine={false} axisLine={{ stroke: PA.border }} interval="preserveStartEnd" />
              <YAxis tick={axisStyle} tickLine={false} axisLine={{ stroke: PA.border }} width={65} tickFormatter={v => `${v} MW`} />
              <Tooltip content={<ChartTooltip />} />
              <ReferenceLine y={0} stroke={PA.border} strokeWidth={1} />
              <Area type="monotone" dataKey="ATC ES→FR" stroke={PA.blue} fill="url(#gATC)" strokeWidth={1.5} dot={false} />
            </AreaChart>
          </ResponsiveContainer>

          <div style={{ marginTop: 28 }}>
            <SectionHeader>Working Thesis</SectionHeader>
            <p style={{ fontFamily: PA.hv, fontSize: 13, fontWeight: 300, color: PA.dim, lineHeight: 1.7, marginBottom: 20 }}>
              {s.last_discount < -10 && s.last_rsi > 0.5
                ? `Gas floor ${s.floor_proxy.toFixed(0)} EUR/MWh above spot — SHORT edge; RSI ${s.last_rsi.toFixed(2)} · thermal-dominant regime.`
                : s.last_discount > 15
                ? `Demand stress — spot ${s.last_spot.toFixed(0)} EUR/MWh is ${s.last_discount.toFixed(0)}€ above gas floor. LONG thesis intact.`
                : s.last_rsi > 0.65
                ? `Renewable dominance. RSI ${s.last_rsi.toFixed(2)} above threshold. Thermal no longer marginal — monitor negative price risk.`
                : `Thermal-Marginal regime holds. Gas floor ${s.floor_proxy.toFixed(0)} EUR/MWh shapes OMIE spread. ${s.cur_dir} with ${s.cur_conf.toFixed(2)} confidence.`
              }
            </p>
            <SectionHeader>Signal Engine Brief</SectionHeader>
            <p style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: 300, color: PA.dim, lineHeight: 1.8 }}>
              Signal engine reads {s.last_regime} regime with RSI {s.last_rsi.toFixed(2)} and floor discount {s.last_discount >= 0 ? '+' : ''}{s.last_discount.toFixed(2)} EUR/MWh.
              Gas cost floor {s.floor_proxy.toFixed(2)} EUR/MWh derived from live TTF {s.live_ttf.toFixed(2)} at 50% CCGT efficiency
              with EUA {s.live_eua.toFixed(0)} EUR/tCO₂ carbon.
              Routing {s.cur_dir} with confidence {s.cur_conf.toFixed(2)}.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Execution tab ────────────────────────────────────────────────
// ── Readiness tab ─────────────────────────────────────────────────
function ReadinessTab({ s, hasLive }: { s: Scalars; hasLive: boolean }) {
  const caps: [string, string, string][] = [
    ['OMIE DA prices',        hasLive ? 'LIVE' : 'MISSING', 'Indicator 600 · EUR/MWh'],
    ['ESIOS generation mix',  hasLive ? 'LIVE' : 'MISSING', 'Wind, solar, hydro, nuclear'],
    ['ESIOS demand forecast', hasLive ? 'LIVE' : 'MISSING', 'Indicator 544 — peninsular prevista'],
    ['ESIOS ATC ES→FR',       hasLive ? 'LIVE' : 'MISSING', 'Indicator 10209 — interconnector'],
    ['Thermal floor calc',    hasLive ? 'LIVE' : 'PROXY',   `TTF ${s.live_ttf.toFixed(1)} · EUA ${s.live_eua.toFixed(0)} · CCGT 50%`],
    ['Regime classifier',     hasLive ? 'LIVE' : 'PROXY',   'RSI + floor ratio, rule-based'],
    ['Spot pricer B76+MC',    s.b76_call > 0 ? 'LIVE' : 'MISSING', 'Shifted log-normal, correct vol'],
    ['Execution router',      'PENDING', 'PaperAdapter — Bloomberg EMSX next'],
    ['BESS sunset model',     'PENDING', 'Search ESIOS bateria indicators'],
    ['REE node map',          'PENDING', '230-node demand map — ingest REE'],
    ['Daily PDF briefing',    'PENDING', 'Wire Mailjet + scheduler'],
    ['Bloomberg EMSX',        'PENDING', 'After paper router is validated'],
  ]
  const statusColor: Record<string, string> = { LIVE: PA.green, PROXY: PA.amber, PENDING: PA.dim, MISSING: PA.red }

  return (
    <div style={{ padding: 32 }}>
      <SectionHeader>System Capabilities</SectionHeader>
      {caps.map(([label, status, note], i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '9px 0', borderBottom: `1px solid ${PA.border}` }}>
          <span style={{ fontFamily: PA.hv, fontSize: 8, fontWeight: 700, letterSpacing: '0.14em', color: statusColor[status], border: `1px solid ${statusColor[status]}`, padding: '2px 8px', minWidth: 58, textAlign: 'center' }}>{status}</span>
          <span style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 400, color: PA.text, minWidth: 220 }}>{label}</span>
          <span style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 300, color: PA.dim }}>{note}</span>
        </div>
      ))}
    </div>
  )
}

// ── News tab ─────────────────────────────────────────────────────
function NewsTab({ feeds, allItems, loading }: { feeds: { label: string; color: string; tag: string; items: NewsItem[] }[]; allItems: NewsItem[]; loading: boolean }) {
  const now = new Date().toUTCString().slice(0, 25)
  if (loading && allItems.length === 0) {
    return <div style={{ padding: 32, fontFamily: PA.hv, fontSize: 12, fontWeight: 300, color: PA.dim }}>Fetching news feeds…</div>
  }
  return (
    <div style={{ padding: 32 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '55fr 45fr', gap: 0, borderBottom: `1px solid ${PA.border}`, marginBottom: 32, paddingBottom: 32 }}>
        {/* Live wire */}
        <div style={{ paddingRight: 32, borderRight: `1px solid ${PA.border}` }}>
          <SectionHeader>Live Wire · Iberian Energy</SectionHeader>
          <div style={{ maxHeight: 520, overflowY: 'auto', paddingRight: 8 }}>
            {allItems.slice(0, 20).map((item, i) => (
              <div key={i} style={{ paddingBottom: 14, marginBottom: 14, borderBottom: `1px solid ${PA.border}` }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <Tag label={item.topicTag} color={item.topicColor} />
                  <span style={{ fontFamily: PA.hv, fontSize: 10, fontWeight: 300, color: PA.dim }}>{item.source.toUpperCase().slice(0, 28)}</span>
                  <span style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 300, color: PA.muted, marginLeft: 'auto' }}>{item.ago}</span>
                </div>
                <a href={item.link} target="_blank" rel="noopener noreferrer"
                  style={{ fontFamily: PA.hv, fontWeight: 700, fontSize: 12, color: PA.text, textDecoration: 'none', lineHeight: 1.45, display: 'block' }}>
                  {item.title}
                </a>
              </div>
            ))}
          </div>
        </div>

        {/* Brief panel */}
        <div style={{ paddingLeft: 32 }}>
          <div style={{ fontFamily: PA.hv, fontSize: 10, fontWeight: 700, color: PA.amber, letterSpacing: '0.12em', marginBottom: 16 }}>ENERGY SIGNAL BRIEF</div>
          {allItems[0] && (
            <div style={{ fontFamily: PA.hv, fontSize: 20, fontWeight: 700, color: PA.text, lineHeight: 1.3, marginBottom: 24, letterSpacing: '-0.01em' }}>
              {allItems[0].title}
            </div>
          )}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, paddingTop: 16, borderTop: `1px solid ${PA.border}` }}>
            {[
              { label: 'ARTICLES LIVE', value: String(allItems.length), color: PA.text },
              { label: 'FEEDS ACTIVE',  value: `${feeds.filter(f => f.items.length > 0).length}/${NEWS_TOPICS.length}`, color: PA.green },
              { label: 'FETCH TIME',    value: now.slice(17, 22), color: PA.dim },
            ].map((m, i) => (
              <div key={i}>
                <div style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 700, color: PA.dim, letterSpacing: '0.08em', marginBottom: 6 }}>{m.label}</div>
                <div style={{ fontFamily: PA.hv, fontSize: 22, fontWeight: 700, color: m.color }}>{m.value}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 4-topic grid */}
      <SectionHeader>By Topic</SectionHeader>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1, background: PA.border }}>
        {feeds.map(feed => (
          <div key={feed.label} style={{ background: PA.card, padding: '16px 18px' }}>
            <div style={{ fontFamily: PA.hv, fontWeight: 700, fontSize: 10, color: feed.color, letterSpacing: '0.14em', borderBottom: `2px solid ${feed.color}`, paddingBottom: 8, marginBottom: 14 }}>
              {feed.label.toUpperCase()}
            </div>
            {feed.items.slice(0, 4).map((item, j) => (
              <div key={j} style={{ marginBottom: 12, paddingBottom: 12, borderBottom: `1px solid ${PA.border}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 700, color: feed.color }}>{item.source.toUpperCase().slice(0, 20)}</span>
                  <span style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 300, color: PA.muted }}>{item.ago}</span>
                </div>
                <a href={item.link} target="_blank" rel="noopener noreferrer"
                  style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 400, color: PA.text, textDecoration: 'none', lineHeight: 1.4, display: 'block' }}>
                  {item.title}
                </a>
              </div>
            ))}
            {feed.items.length === 0 && <div style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.muted }}>Loading…</div>}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Interactive Pricer tab ────────────────────────────────────────
function PricerTab({ p, scalars }: { p: PricerData; scalars: Scalars }) {
  const defaultF   = scalars.omip_m1 ?? scalars.last_spot
  const defaultVol = Math.min(Math.round(p.vol_annual * 100), 400)

  const [useMIBEL, setUseMIBEL] = useState(!!scalars.omip_m1)
  const [F,        setF]        = useState(parseFloat(defaultF.toFixed(2)))
  const [K,        setK]        = useState(parseFloat(defaultF.toFixed(2)))
  const [volPct,   setVolPct]   = useState(defaultVol)
  const [days,     setDays]     = useState(30)

  const sigma = volPct / 100
  const T     = days / 365
  const call  = b76Call(F, K, sigma, T)
  const delta = b76Delta(F, K, sigma, T)
  const vega  = b76Vega(F, K, sigma, T)
  const intrinsic  = Math.max(0, F - K)
  const timeValue  = Math.max(0, call - intrinsic)
  const moneyness  = K > 0 ? ((F / K - 1) * 100) : 0

  const scenarios = [0.70, 0.80, 0.90, 0.95, 1.00, 1.05, 1.10, 1.20, 1.30].map(m => ({
    pct:   `${Math.round(m * 100)}%`,
    K:     (F * m).toFixed(2),
    call:  b76Call(F, F * m, sigma, T).toFixed(2),
    delta: b76Delta(F, F * m, sigma, T).toFixed(2),
    vega:  b76Vega(F, F * m, sigma, T).toFixed(2),
    atm:   m === 1.00,
  }))

  const volSweep = [50,100,150,200,250,300,350,400].map(v => ({
    vol: v, call: b76Call(F, K, v / 100, T).toFixed(2),
  }))

  const axisStyle = { fill: PA.dim, fontSize: 9, fontFamily: PA.hv }
  const gridProps = { stroke: PA.border, strokeDasharray: '0' as const }

  const slider: CSSProperties = {
    width: '100%', accentColor: PA.amber, cursor: 'pointer',
    background: 'transparent', appearance: 'auto' as const,
  }
  const numInput: CSSProperties = {
    background: PA.surface, border: `1px solid ${PA.border}`, color: PA.text,
    fontFamily: PA.hv, fontSize: 13, fontWeight: 700, padding: '4px 10px',
    width: 90, textAlign: 'right' as const, outline: 'none', borderRadius: 3,
  }

  return (
    <div style={{ padding: 32 }}>
      {/* MIBEL context banner */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 28, padding: '12px 20px', background: useMIBEL ? 'rgba(20,184,166,0.08)' : 'rgba(245,158,11,0.06)', border: `1px solid ${useMIBEL ? PA.teal : PA.border}`, borderRadius: 6 }}>
        <button onClick={() => { setUseMIBEL(v => !v); setF(parseFloat((useMIBEL ? scalars.last_spot : (scalars.omip_m1 ?? scalars.last_spot)).toFixed(2))); setK(parseFloat((useMIBEL ? scalars.last_spot : (scalars.omip_m1 ?? scalars.last_spot)).toFixed(2))) }}
          style={{ fontFamily: PA.hv, fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', background: useMIBEL ? PA.teal : 'transparent', color: useMIBEL ? '#000' : PA.dim, border: `1px solid ${useMIBEL ? PA.teal : PA.border}`, padding: '4px 12px', cursor: 'pointer', borderRadius: 3 }}>
          {useMIBEL ? '✓ MIBEL' : 'MIBEL'}
        </button>
        <span style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.dim }}>
          {useMIBEL
            ? `Using OMIP M+1 forward ${scalars.omip_m1?.toFixed(2) ?? '—'} €/MWh as F — MIBEL futures context`
            : `Using OMIE spot ${scalars.last_spot.toFixed(2)} €/MWh as F — toggle MIBEL to use OMIP M+1 forward`}
        </span>
        <span style={{ marginLeft: 'auto', fontFamily: PA.hv, fontSize: 10, fontWeight: 300, color: PA.muted }}>
          Black-76 · shifted log-normal · in-browser live
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 32 }}>

        {/* Left: controls + live output */}
        <div>
          <SectionHeader>Interactive Calculator</SectionHeader>

          {/* Controls */}
          {([
            { label: 'Forward Price F', val: F, setVal: setF, min: 1, max: 400, step: 0.5, unit: '€/MWh' },
            { label: 'Strike K',        val: K, setVal: setK, min: 1, max: 400, step: 0.5, unit: '€/MWh' },
          ] as { label: string; val: number; setVal: (v: number) => void; min: number; max: number; step: number; unit: string }[]).map(({ label, val, setVal, min, max, step, unit }) => (
            <div key={label} style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.dim }}>{label}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <input type="number" value={val} min={min} max={max} step={step}
                    onChange={e => setVal(parseFloat(e.target.value) || min)}
                    style={numInput} />
                  <span style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 300, color: PA.muted }}>{unit}</span>
                </div>
              </div>
              <input type="range" min={min} max={max} step={step} value={val}
                onChange={e => setVal(parseFloat(e.target.value))} style={slider} />
            </div>
          ))}

          <div style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.dim }}>Implied Vol σ</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <input type="number" value={volPct} min={5} max={600} step={5}
                  onChange={e => setVolPct(parseFloat(e.target.value) || 5)} style={numInput} />
                <span style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 300, color: PA.muted }}>%</span>
              </div>
            </div>
            <input type="range" min={5} max={600} step={5} value={volPct}
              onChange={e => setVolPct(parseFloat(e.target.value))} style={slider} />
            <div style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 300, color: PA.muted, marginTop: 3 }}>
              Historical (pkl): {(p.vol_annual * 100).toFixed(0)}% ann · Normal range {(p.vol_normal_min * 100).toFixed(0)}–{(p.vol_normal_max * 100).toFixed(0)}%
            </div>
          </div>

          <div style={{ marginBottom: 28 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.dim }}>Days to Expiry T</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <input type="number" value={days} min={1} max={365} step={1}
                  onChange={e => setDays(parseInt(e.target.value) || 1)} style={numInput} />
                <span style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 300, color: PA.muted }}>days</span>
              </div>
            </div>
            <input type="range" min={1} max={365} step={1} value={days}
              onChange={e => setDays(parseInt(e.target.value))} style={slider} />
          </div>

          {/* Live output */}
          <div style={{ background: PA.card, border: `1px solid ${PA.border}`, borderLeft: `4px solid ${PA.amber}`, borderRadius: 6, padding: 20, marginBottom: 20 }}>
            <div style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 700, color: PA.dim, letterSpacing: '0.1em', marginBottom: 12 }}>LIVE OUTPUT · BLACK-76</div>
            <div style={{ fontFamily: PA.hv, fontSize: 36, fontWeight: 700, color: PA.amber, lineHeight: 1, marginBottom: 4 }}>
              {call.toFixed(2)} <span style={{ fontSize: 14, fontWeight: 300, color: PA.dim }}>€/MWh</span>
            </div>
            <div style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.dim, marginBottom: 16 }}>
              Call price · F/K moneyness {moneyness >= 0 ? '+' : ''}{moneyness.toFixed(1)}%
            </div>
            <DataRow label="Delta (ITM prob)"  value={`${(delta * 100).toFixed(1)}%`}     color={PA.teal}   />
            <DataRow label="Vega (per 1% σ)"   value={`${vega.toFixed(2)} €/MWh`}          color={PA.purple} />
            <DataRow label="Intrinsic value"    value={`${intrinsic.toFixed(2)} €/MWh`}     color={PA.text}   />
            <DataRow label="Time value"         value={`${timeValue.toFixed(2)} €/MWh`}     color={PA.dim}    />
          </div>

          {/* Vol sensitivity */}
          <SectionHeader>Vol Sensitivity (K fixed)</SectionHeader>
          {volSweep.map(row => (
            <div key={row.vol} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: `1px solid ${PA.border}` }}>
              <span style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.dim }}>{row.vol}%</span>
              <span style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: 700, color: row.vol === volPct ? PA.amber : PA.text }}>{row.call} €</span>
            </div>
          ))}
        </div>

        {/* Right: scenario table + rolling vol chart */}
        <div>
          <SectionHeader>Strike Scenario Analysis — MIBEL Call Options</SectionHeader>
          <div style={{ marginBottom: 8, fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.dim }}>
            F = {F.toFixed(2)} €/MWh · σ = {volPct}% · T = {days}d · r = 0%
          </div>
          <div style={{ background: PA.surface, border: `1px solid ${PA.border}`, borderRadius: 4, overflow: 'hidden', marginBottom: 32 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '80px 100px 100px 80px 80px', background: PA.card, borderBottom: `1px solid ${PA.border}` }}>
              {['Moneyness', 'Strike K', 'Call Price', 'Delta', 'Vega'].map(h => (
                <div key={h} style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 700, color: PA.dim, padding: '10px 14px', letterSpacing: '0.08em' }}>{h}</div>
              ))}
            </div>
            {scenarios.map(row => (
              <div key={row.pct} style={{
                display: 'grid', gridTemplateColumns: '80px 100px 100px 80px 80px',
                borderBottom: `1px solid ${PA.border}`,
                background: row.atm ? 'rgba(245,158,11,0.06)' : 'transparent',
              }}>
                <div style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: row.atm ? 700 : 400, color: row.atm ? PA.amber : PA.dim, padding: '10px 14px' }}>{row.pct}{row.atm ? ' ATM' : ''}</div>
                <div style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: 700, color: PA.text, padding: '10px 14px' }}>{row.K}</div>
                <div style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: 700, color: PA.amber, padding: '10px 14px' }}>{row.call}</div>
                <div style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: 400, color: PA.teal, padding: '10px 14px' }}>{row.delta}</div>
                <div style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: 400, color: PA.purple, padding: '10px 14px' }}>{row.vega}</div>
              </div>
            ))}
          </div>

          <SectionHeader>Rolling 30-Day Annualised Vol (historical)</SectionHeader>
          {p.rolling_vol.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={p.rolling_vol} style={{ background: 'transparent' }}>
                <defs>
                  <linearGradient id="gVol" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={PA.amber} stopOpacity={0.15} />
                    <stop offset="95%" stopColor={PA.amber} stopOpacity={0}    />
                  </linearGradient>
                </defs>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="ts" tick={axisStyle} tickLine={false} axisLine={{ stroke: PA.border }} interval="preserveStartEnd"
                  tickFormatter={v => { try { return new Date(v).toLocaleDateString('en-GB', { month: 'short', day: 'numeric' }) } catch { return v } }} />
                <YAxis tick={axisStyle} tickLine={false} axisLine={{ stroke: PA.border }} width={52} tickFormatter={v => `${v}%`} />
                <Tooltip content={<ChartTooltip />} />
                <ReferenceLine y={p.vol_normal_min * 100} stroke={PA.green} strokeDasharray="3 3" strokeWidth={1} />
                <ReferenceLine y={p.vol_normal_max * 100} stroke={PA.red}   strokeDasharray="3 3" strokeWidth={1} label={{ value: 'Normal range', position: 'insideTopRight', fontSize: 9, fill: PA.dim, fontFamily: PA.hv }} />
                <Area type="monotone" dataKey="vol" name="Ann. Vol %" stroke={PA.amber} fill="url(#gVol)" strokeWidth={1.5} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: 300, color: PA.dim }}>Insufficient data for rolling vol.</div>
          )}

          <div style={{ marginTop: 28 }}>
            <SectionHeader>Calibration Reference (pkl)</SectionHeader>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {([
                ['Pkl Spot F',    `${p.last_spot.toFixed(2)} €/MWh`,   PA.amber],
                ['Pkl Strike',    `${p.strike.toFixed(2)} €/MWh`,       PA.dim  ],
                ['Pkl Vol σ',     `${(p.sigma*100).toFixed(2)}%`,        PA.teal ],
                ['B76 Call',      `${p.b76_call.toFixed(2)} €/MWh`,     PA.amber],
                ['MC Call',       `${p.mc_call.toFixed(2)} €/MWh`,      PA.amber],
                ['Spike Prob',    `${(p.spike_prob*100).toFixed(2)}%`,   p.spike_prob > 0.1 ? PA.amber : PA.dim],
                ['Neg Price',     `${(p.neg_price_prob*100).toFixed(2)}%`, p.neg_price_prob > 0.05 ? PA.red : PA.dim],
                ['ITM Paths',     `${p.mc_payoff.itm_count} / 10k`,     PA.dim  ],
              ] as [string,string,string][]).map(([l,v,c]) => (
                <div key={l} style={{ background: PA.surface, border: `1px solid ${PA.border}`, borderRadius: 4, padding: '8px 12px' }}>
                  <div style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 300, color: PA.dim, marginBottom: 3 }}>{l}</div>
                  <div style={{ fontFamily: PA.hv, fontSize: 13, fontWeight: 700, color: c }}>{v}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── SarAI tab ─────────────────────────────────────────────────────
function SarAITab({ s }: { s: Scalars }) {
  const [autoTrade, setAutoTrade] = useState(false)
  const [trades, setTrades]       = useState<PaperTrade[]>([...paperTrades])
  const lastRefresh = s ? new Date().toUTCString().slice(0, 25) : '—'

  const reason =
    s.last_discount < -10 && s.last_rsi > 0.5
      ? `Floor ${s.floor_proxy.toFixed(2)} EUR/MWh is ${Math.abs(s.last_discount).toFixed(2)}€ above spot. RSI ${s.last_rsi.toFixed(2)} in thermal-dom range. SHORT edge confirmed.`
    : s.last_discount > 15
      ? `Spot ${s.last_spot.toFixed(2)} EUR/MWh breaches gas floor by ${s.last_discount.toFixed(2)}€. Demand stress regime. LONG thesis.`
    : s.last_rsi > 0.65
      ? `RSI ${s.last_rsi.toFixed(2)} exceeds 0.65 threshold. Renewable surplus driving spot below floor. Negative price risk elevated.`
    : `Thermal-Marginal regime. Floor discount ${s.last_discount >= 0 ? '+' : ''}${s.last_discount.toFixed(2)} EUR/MWh. Monitoring for regime change.`

  const guardrails = [
    ['Floor discount < ±50 €', Math.abs(s.last_discount) < 50],
    ['Confidence ≥ 0.40',      s.cur_conf >= 0.40],
    ['RSI in bounds',           s.last_rsi < 0.9 && s.last_rsi > 0.05],
    ['Spike prob < 15%',        s.spike_prob < 0.15],
  ] as [string, boolean][]
  const allPass = guardrails.every(([, p]) => p)

  const ddc = dirColor(s.cur_dir)

  return (
    <div style={{ padding: 32, display: 'grid', gridTemplateColumns: '320px 1fr', gap: 32 }}>

      {/* Left: status + decision */}
      <div>
        {/* Agent status card */}
        <div style={{ background: PA.card, border: `1px solid ${PA.teal}`, borderLeft: `4px solid ${PA.teal}`, borderRadius: 8, padding: 20, marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: PA.green, display: 'inline-block', animation: 'pulse 2s infinite' }} />
            <span style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 700, color: PA.green, letterSpacing: '0.1em' }}>SarAI ONLINE</span>
          </div>
          <DataRow label="Signal engine"   value="Railway · live"            color={PA.green}  />
          <DataRow label="Last refresh"    value={lastRefresh.slice(5, 22)}  color={PA.dim}    />
          <DataRow label="Next scheduled"  value="Hourly cron (pending)"     color={PA.amber}  />
          <DataRow label="Mode"            value={autoTrade ? 'AUTO-TRADE · PAPER' : 'MONITOR ONLY'} color={autoTrade ? PA.amber : PA.dim} />
        </div>

        {/* Current decision */}
        <div style={{ background: PA.surface, border: `1px solid ${PA.border}`, borderRadius: 8, padding: 20, marginBottom: 24 }}>
          <div style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 700, color: PA.dim, letterSpacing: '0.1em', marginBottom: 12 }}>CURRENT DECISION</div>
          <div style={{ fontFamily: PA.hv, fontSize: 42, fontWeight: 700, color: ddc, lineHeight: 1, marginBottom: 8 }}>
            {s.cur_dir === 'LONG' ? '▲' : s.cur_dir === 'SHORT' ? '▼' : '—'} {s.cur_dir}
          </div>
          <div style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.dim, lineHeight: 1.7, marginBottom: 16 }}>{reason}</div>
          <DataRow label="Confidence"    value={s.cur_conf.toFixed(2)}   color={PA.teal}  />
          <DataRow label="Regime"        value={s.last_regime}           color={regimeColor(s.last_regime)} />
        </div>

        {/* Guardrails */}
        <SectionHeader>Guardrail Check</SectionHeader>
        {guardrails.map(([label, passed], i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', borderBottom: `1px solid ${PA.border}` }}>
            <span style={{ fontFamily: PA.hv, fontSize: 13, fontWeight: 700, color: passed ? PA.green : PA.red }}>{passed ? '✓' : '✗'}</span>
            <span style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.dim }}>{label}</span>
          </div>
        ))}
        <div style={{ marginTop: 12, padding: '8px 12px', borderRadius: 4, background: allPass ? 'rgba(16,185,129,0.07)' : 'rgba(239,68,68,0.07)', border: `1px solid ${allPass ? PA.green : PA.red}` }}>
          <span style={{ fontFamily: PA.hv, fontSize: 10, fontWeight: 700, color: allPass ? PA.green : PA.red }}>
            {allPass ? '✓ CLEAR TO TRADE' : '✗ BLOCKED'}
          </span>
        </div>

        {/* Auto-trade toggle */}
        <div style={{ marginTop: 24, padding: 16, background: 'rgba(245,158,11,0.05)', border: `1px solid ${PA.border}`, borderRadius: 6 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: 700, color: PA.text }}>Paper Auto-Trade</span>
            <button onClick={() => setAutoTrade(v => !v)} style={{
              fontFamily: PA.hv, fontSize: 10, fontWeight: 700, letterSpacing: '0.08em',
              background: autoTrade ? PA.amber : 'transparent',
              color: autoTrade ? '#000' : PA.dim,
              border: `1px solid ${autoTrade ? PA.amber : PA.border}`,
              padding: '5px 14px', cursor: 'pointer', borderRadius: 3,
            }}>
              {autoTrade ? 'ON' : 'OFF'}
            </button>
          </div>
          <div style={{ fontFamily: PA.hv, fontSize: 10, fontWeight: 300, color: PA.muted, marginTop: 8 }}>
            When ON, SarAI submits paper fills at current OMIE spot on each signal change. Live OMIP routing requires broker API.
          </div>
        </div>
      </div>

      {/* Right: architecture + roadmap */}
      <div>
        <SectionHeader>Agent Architecture</SectionHeader>
        {([
          ['DATA LAYER',      PA.blue,   'ESIOS API (indicators 600, 541, 542, 474, 544, 10209) · TTF via Yahoo Finance · EUA hardcoded → ICE/EEX feed next'],
          ['SIGNAL ENGINE',   PA.green,  'RSI = gen_renewable / demand · Floor discount = OMIE − CCGT floor · Regime classifier (3 states) · Confidence = f(|discount|, RSI)'],
          ['MIBEL LAYER',     PA.teal,   'OMIP M+1 forward (OMIP scraper) · ES–PT spread (ind. 600 geo_id 4) · SIDC intraday sessions (pending) · Balancing prices (pending)'],
          ['SARAI BRAIN',     PA.amber,  'Reads signal + guardrails → produces LONG / SHORT / NEUTRAL + confidence + reasoning · Currently session-only; hourly Railway cron pending'],
          ['EXECUTION',       PA.purple, 'Paper: fills at OMIE spot · Live: OMIP futures broker API (requires participant status) · SIDC intraday: REE participant API (pending)'],
          ['REPORTING',       PA.dim,    'Daily PDF briefing via Mailjet (pending) · P&L tracker · Position monitor · REE 230-node demand map (pending)'],
        ] as [string, string, string][]).map(([layer, color, desc], i) => (
          <div key={i} style={{ display: 'flex', gap: 16, padding: '16px 0', borderBottom: `1px solid ${PA.border}`, alignItems: 'flex-start' }}>
            <span style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 700, letterSpacing: '0.12em', color, border: `1px solid ${color}`, padding: '3px 10px', minWidth: 100, textAlign: 'center', flexShrink: 0, marginTop: 2 }}>{layer}</span>
            <span style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.dim, lineHeight: 1.7 }}>{desc}</span>
          </div>
        ))}

        <div style={{ marginTop: 32 }}>
          <SectionHeader>Build Roadmap</SectionHeader>
          {([
            ['NOW',   PA.green,  'Interactive Pricer — live Black-76 in browser ✓'],
            ['NOW',   PA.green,  'SarAI tab — agent status + decision display ✓'],
            ['NEXT',  PA.amber,  'Railway hourly cron: refresh_live_data.py + export_json.py'],
            ['NEXT',  PA.amber,  'Execution parser: paper fill at OMIE + P&L tracker'],
            ['NEXT',  PA.amber,  'EUA live feed — ICE/EEX API or licensed data vendor'],
            ['SOON',  PA.teal,   'SIDC intraday sessions S1–S6: OMIE public XML scraper'],
            ['SOON',  PA.teal,   'Daily PDF briefing via Mailjet scheduler'],
            ['LATER', PA.dim,    'REE 230-node demand map ingestion'],
            ['LATER', PA.dim,    'OMIP broker API — live futures execution after paper validation'],
            ['LATER', PA.dim,    'Bloomberg EMSX adapter (if institutional route)'],
          ] as [string, string, string][]).map(([prio, color, text], i) => (
            <div key={i} style={{ display: 'flex', gap: 14, padding: '8px 0', borderBottom: `1px solid ${PA.border}`, alignItems: 'center' }}>
              <span style={{ fontFamily: PA.hv, fontSize: 8, fontWeight: 700, letterSpacing: '0.14em', color, border: `1px solid ${color}`, padding: '2px 8px', minWidth: 46, textAlign: 'center' }}>{prio}</span>
              <span style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.dim }}>{text}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Execution tab (paper trading interface) ───────────────────────
function ExecutionTab({ s }: { s: Scalars }) {
  const [trades, setTrades] = useState<PaperTrade[]>([])
  const [dir,  setDir]  = useState<'LONG' | 'SHORT'>('LONG')
  const [size, setSize] = useState(1)
  const [pnl, setPnl]   = useState(0)

  function submitOrder() {
    const id    = tradeIdSeq++
    const entry = s.last_spot
    const trade: PaperTrade = { id, ts: new Date().toISOString(), dir, size, entry, exit: null, pnl: null, status: 'OPEN' }
    paperTrades.push(trade)
    setTrades([...paperTrades])
  }

  function closeAll() {
    let total = 0
    paperTrades.forEach(t => {
      if (t.status === 'OPEN') {
        t.exit   = s.last_spot
        t.pnl    = (t.dir === 'LONG' ? 1 : -1) * (t.exit - t.entry) * t.size
        t.status = 'CLOSED'
        total   += t.pnl
      }
    })
    setPnl(prev => prev + total)
    setTrades([...paperTrades])
  }

  const openTrades  = trades.filter(t => t.status === 'OPEN')
  const closedTrades = trades.filter(t => t.status === 'CLOSED')
  const totalPnL    = closedTrades.reduce((a, t) => a + (t.pnl ?? 0), 0)
  const ddc = dirColor(s.cur_dir)

  const guardrails = [
    ['Floor discount within bounds (±50€)',  Math.abs(s.last_discount) < 50],
    ['Confidence ≥ 0.40',                   s.cur_conf >= 0.40],
    ['RSI within normal range (0.05–0.90)',  s.last_rsi < 0.9 && s.last_rsi > 0.05],
    ['Spike probability < 15%',             s.spike_prob < 0.15],
    ['Negative price risk < 5%',            s.neg_prob < 0.05],
  ] as [string, boolean][]
  const allPass = guardrails.every(([, p]) => p)

  return (
    <div style={{ padding: 32, display: 'grid', gridTemplateColumns: '320px 1fr', gap: 32 }}>
      {/* Left: order entry */}
      <div>
        <SectionHeader>Paper Order Entry</SectionHeader>
        <div style={{ background: PA.card, border: `1px solid ${PA.border}`, borderRadius: 8, padding: 20, marginBottom: 20 }}>
          <div style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 700, color: PA.dim, letterSpacing: '0.1em', marginBottom: 14 }}>DIRECTION</div>
          <div style={{ display: 'flex', gap: 1, marginBottom: 20 }}>
            {(['LONG', 'SHORT'] as const).map(d => (
              <button key={d} onClick={() => setDir(d)} style={{
                flex: 1, fontFamily: PA.hv, fontSize: 13, fontWeight: 700,
                background: dir === d ? (d === 'LONG' ? PA.green : PA.red) : 'transparent',
                color: dir === d ? '#000' : PA.dim,
                border: `1px solid ${d === 'LONG' ? PA.green : PA.red}`,
                padding: '10px', cursor: 'pointer',
                borderRadius: d === 'LONG' ? '4px 0 0 4px' : '0 4px 4px 0',
              }}>
                {d === 'LONG' ? '▲ LONG' : '▼ SHORT'}
              </button>
            ))}
          </div>

          <div style={{ marginBottom: 16 }}>
            <div style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 700, color: PA.dim, letterSpacing: '0.1em', marginBottom: 8 }}>SIZE (MWh)</div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input type="number" value={size} min={1} max={1000} step={1}
                onChange={e => setSize(Math.max(1, parseInt(e.target.value) || 1))}
                style={{ background: PA.surface, border: `1px solid ${PA.border}`, color: PA.text, fontFamily: PA.hv, fontSize: 16, fontWeight: 700, padding: '8px 12px', width: '100%', outline: 'none', borderRadius: 3 }} />
              <span style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.dim }}>MWh</span>
            </div>
          </div>

          <DataRow label="Entry price (OMIE)" value={`${s.last_spot.toFixed(2)} €/MWh`} color={PA.amber} />
          <DataRow label="Notional"           value={`${(s.last_spot * size).toFixed(2)} €`} color={PA.dim} />

          <button onClick={submitOrder} disabled={!allPass}
            style={{
              width: '100%', marginTop: 16, fontFamily: PA.hv, fontSize: 13, fontWeight: 700,
              background: allPass ? (dir === 'LONG' ? PA.green : PA.red) : PA.muted,
              color: '#000', border: 'none', padding: '12px', cursor: allPass ? 'pointer' : 'not-allowed',
              borderRadius: 4, letterSpacing: '0.05em',
            }}>
            {allPass ? `SUBMIT PAPER ${dir}` : 'BLOCKED — GUARDRAIL FAIL'}
          </button>
          {openTrades.length > 0 && (
            <button onClick={closeAll}
              style={{ width: '100%', marginTop: 8, fontFamily: PA.hv, fontSize: 11, fontWeight: 700, background: 'transparent', color: PA.red, border: `1px solid ${PA.red}`, padding: '8px', cursor: 'pointer', borderRadius: 4 }}>
              CLOSE ALL OPEN
            </button>
          )}
        </div>

        <SectionHeader>Guardrails</SectionHeader>
        {guardrails.map(([label, passed], i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', borderBottom: `1px solid ${PA.border}` }}>
            <span style={{ fontFamily: PA.hv, fontSize: 13, fontWeight: 700, color: passed ? PA.green : PA.red }}>{passed ? '✓' : '✗'}</span>
            <span style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.dim }}>{label}</span>
          </div>
        ))}
      </div>

      {/* Right: P&L + trade log */}
      <div>
        <SectionHeader>Position Summary</SectionHeader>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 28 }}>
          {[
            { label: 'OPEN TRADES',   value: String(openTrades.length),                                  color: openTrades.length > 0 ? PA.amber : PA.dim },
            { label: 'CLOSED TRADES', value: String(closedTrades.length),                                color: PA.dim  },
            { label: 'REALISED P&L',  value: `${totalPnL >= 0 ? '+' : ''}${totalPnL.toFixed(2)} €`,     color: totalPnL > 0 ? PA.green : totalPnL < 0 ? PA.red : PA.dim },
          ].map((m, i) => (
            <div key={i} style={{ background: PA.surface, border: `1px solid ${PA.border}`, borderRadius: 6, padding: 16 }}>
              <div style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 700, color: PA.dim, letterSpacing: '0.08em', marginBottom: 8 }}>{m.label}</div>
              <div style={{ fontFamily: PA.hv, fontSize: 22, fontWeight: 700, color: m.color }}>{m.value}</div>
            </div>
          ))}
        </div>

        <SectionHeader>Trade Log</SectionHeader>
        {trades.length === 0 ? (
          <div style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: 300, color: PA.muted, padding: '20px 0' }}>
            No paper trades yet. Submit an order above.
          </div>
        ) : (
          <div style={{ background: PA.surface, border: `1px solid ${PA.border}`, borderRadius: 4, overflow: 'hidden' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '40px 160px 60px 80px 90px 90px 90px 70px', background: PA.card, borderBottom: `1px solid ${PA.border}` }}>
              {['#', 'Time', 'Dir', 'Size', 'Entry', 'Exit', 'P&L', 'Status'].map(h => (
                <div key={h} style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 700, color: PA.dim, padding: '8px 12px', letterSpacing: '0.08em' }}>{h}</div>
              ))}
            </div>
            {[...trades].reverse().map(t => {
              const tPnl = t.pnl ?? ((t.dir === 'LONG' ? 1 : -1) * (s.last_spot - t.entry) * t.size)
              const pnlColor = tPnl > 0 ? PA.green : tPnl < 0 ? PA.red : PA.dim
              return (
                <div key={t.id} style={{ display: 'grid', gridTemplateColumns: '40px 160px 60px 80px 90px 90px 90px 70px', borderBottom: `1px solid ${PA.border}` }}>
                  <div style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.muted, padding: '8px 12px' }}>{t.id}</div>
                  <div style={{ fontFamily: PA.hv, fontSize: 10, fontWeight: 300, color: PA.dim, padding: '8px 12px' }}>{new Date(t.ts).toLocaleTimeString('en-GB')}</div>
                  <div style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 700, color: t.dir === 'LONG' ? PA.green : PA.red, padding: '8px 12px' }}>{t.dir === 'LONG' ? '▲' : '▼'} {t.dir}</div>
                  <div style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.dim, padding: '8px 12px' }}>{t.size} MWh</div>
                  <div style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 700, color: PA.text, padding: '8px 12px' }}>{t.entry.toFixed(2)} €</div>
                  <div style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.dim, padding: '8px 12px' }}>{t.exit?.toFixed(2) ?? `${s.last_spot.toFixed(2)} *`}</div>
                  <div style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 700, color: pnlColor, padding: '8px 12px' }}>{tPnl >= 0 ? '+' : ''}{tPnl.toFixed(2)} €</div>
                  <div style={{ fontFamily: PA.hv, fontSize: 9, fontWeight: 700, color: t.status === 'OPEN' ? PA.amber : PA.dim, padding: '8px 12px', letterSpacing: '0.05em' }}>{t.status}</div>
                </div>
              )
            })}
          </div>
        )}
        <div style={{ marginTop: 8, fontFamily: PA.hv, fontSize: 9, fontWeight: 300, color: PA.muted }}>
          * Mark-to-market at current OMIE spot. Paper trades only — no real capital at risk.
        </div>

        <div style={{ marginTop: 28 }}>
          <SectionHeader>Execution Roadmap</SectionHeader>
          {([
            ['LIVE',  PA.green,  'Paper fills at OMIE spot on order submit ✓'],
            ['NEXT',  PA.amber,  'SarAI auto-submit: fires on signal change when guardrails pass'],
            ['NEXT',  PA.amber,  'OMIP futures API — requires Spanish qualified market participant'],
            ['SOON',  PA.teal,   'SIDC intraday session S1–S6 order routing via OMIE API'],
            ['LATER', PA.dim,    'Bloomberg EMSX adapter — post paper validation, institutional route'],
          ] as [string, string, string][]).map(([prio, color, text], i) => (
            <div key={i} style={{ display: 'flex', gap: 14, padding: '8px 0', borderBottom: `1px solid ${PA.border}`, alignItems: 'center' }}>
              <span style={{ fontFamily: PA.hv, fontSize: 8, fontWeight: 700, letterSpacing: '0.14em', color, border: `1px solid ${color}`, padding: '2px 8px', minWidth: 46, textAlign: 'center' }}>{prio}</span>
              <span style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.dim }}>{text}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── No data state ────────────────────────────────────────────────
function NoData({ error }: { error: string | null }) {
  return (
    <div style={{ padding: 32 }}>
      <div style={{ background: PA.card, border: `1px solid ${PA.border}`, borderLeft: `4px solid ${PA.red}`, borderRadius: 8, padding: 24 }}>
        <div style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: 700, color: PA.red, marginBottom: 8 }}>DATA NOT AVAILABLE</div>
        <div style={{ fontFamily: PA.hv, fontSize: 12, fontWeight: 300, color: PA.dim, marginBottom: 16 }}>{error ?? 'live_data.json not found'}</div>
        <div style={{ fontFamily: PA.hv, fontSize: 11, fontWeight: 300, color: PA.muted, lineHeight: 1.8 }}>
          Run the export script to generate data:<br />
          <span style={{ color: PA.amber, fontWeight: 700 }}>python scripts/export_json.py</span>
        </div>
      </div>
    </div>
  )
}

// ── Root App ─────────────────────────────────────────────────────
export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('Signal')
  const { data, error }            = useLiveData()
  const liveTTF                    = useTTFLive()
  const { feeds, allItems, loading } = useNews()

  const scalars: Scalars | null = data?.scalars
    ? liveTTF ? { ...data.scalars, live_ttf: liveTTF } : data.scalars
    : null

  const live = data?.live ?? []

  const dc = scalars ? (scalars.last_discount < 0 ? PA.red : PA.green) : PA.dim
  const sigDir = scalars?.cur_dir ?? 'NEUTRAL'
  const sigArrow = sigDir === 'LONG' ? '▲' : sigDir === 'SHORT' ? '▼' : '—'

  // Scrolling ticker — everything including electricity input prices
  const tickerItems = scalars ? [
    { label: 'OMIE Spot',      value: `${scalars.last_spot.toFixed(2)} €/MWh`,                                          color: PA.amber  },
    { label: 'Thermal Floor',  value: `${scalars.floor_proxy.toFixed(2)} €/MWh`,                                         color: PA.blue   },
    { label: 'Floor Disc',     value: `${scalars.last_discount >= 0 ? '+' : ''}${scalars.last_discount.toFixed(2)} €/MWh`, color: dc        },
    { label: 'Signal',         value: `${sigArrow} ${sigDir} ${scalars.cur_conf.toFixed(2)}`,                            color: dirColor(sigDir) },
    { label: 'Regime',         value: scalars.last_regime,                                                                color: regimeColor(scalars.last_regime) },
    { label: 'RSI',            value: scalars.last_rsi.toFixed(2),                                                       color: PA.teal   },
    { label: 'TTF Gas',        value: `${scalars.live_ttf.toFixed(2)} €/MWh`,                                            color: PA.amber  },
    { label: 'EUA Carbon',     value: `${scalars.live_eua.toFixed(0)} €/t`,                                              color: PA.purple },
    { label: 'Ann Vol',        value: `${(scalars.vol_annual * 100).toFixed(1)}%`,                                       color: PA.dim    },
    { label: 'B76 Call',       value: `${scalars.b76_call.toFixed(2)} €`,                                                color: PA.dim    },
    { label: 'MC Call',        value: `${scalars.mc_call.toFixed(2)} €`,                                                 color: PA.dim    },
    { label: 'Spike Prob',     value: `${(scalars.spike_prob * 100).toFixed(2)}%`,                                       color: scalars.spike_prob > 0.1 ? PA.amber : PA.dim },
    ...(scalars.atc_last      !== undefined ? [{ label: 'ATC ES→FR',   value: `${scalars.atc_last.toFixed(0)} MW`,    color: PA.blue  }] : []),
    ...(scalars.omip_m1       !== undefined ? [{ label: 'OMIP M+1',    value: `${scalars.omip_m1.toFixed(2)} €/MWh`, color: PA.teal  }] : []),
    ...(scalars.forward_basis !== undefined ? [{ label: 'Fwd Basis',   value: `${scalars.forward_basis >= 0 ? '+' : ''}${scalars.forward_basis.toFixed(2)}`, color: scalars.forward_basis < -5 ? PA.red : PA.green }] : []),
    ...(scalars.es_pt_spread  !== undefined ? [{ label: 'ES-PT',       value: `${scalars.es_pt_spread.toFixed(2)} €`, color: scalars.es_pt_spread > 5 ? PA.amber : PA.dim }] : []),
  ] : []

  // Stats bar — 8 fixed boxes always visible below the ticker
  const statsItems = scalars ? [
    { label: 'OMIE Spot',      value: `${scalars.last_spot.toFixed(2)} €`,                                               color: PA.amber },
    { label: 'Regime',         value: scalars.last_regime,                                                                color: regimeColor(scalars.last_regime) },
    { label: 'RSI',            value: scalars.last_rsi.toFixed(2),                                                       color: PA.teal  },
    { label: 'Floor Disc',     value: `${scalars.last_discount >= 0 ? '+' : ''}${scalars.last_discount.toFixed(2)} €/MWh`, color: dc       },
    { label: 'Ann Vol',        value: `${(scalars.vol_annual * 100).toFixed(1)}%`,                                       color: PA.dim   },
    { label: 'B76 Call',       value: `${scalars.b76_call.toFixed(2)} €`,                                                color: PA.dim   },
    { label: 'Spike Prob',     value: `${(scalars.spike_prob * 100).toFixed(2)}%`,                                       color: scalars.spike_prob > 0.1 ? PA.amber : PA.dim },
    { label: 'Signal',         value: `${sigArrow} ${sigDir} ${scalars.cur_conf.toFixed(2)}`,                            color: dirColor(sigDir) },
  ] : []

  return (
    <div style={{ minHeight: '100vh', background: PA.bg, color: PA.text, fontFamily: PA.hv }}>
      <style>{`
        @keyframes pulse  { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        @keyframes ticker { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
        button { outline: none; }
        a:hover { opacity: 0.8; }
      `}</style>

      <Header dataSource={data ? 'ESIOS LIVE' : error ? 'OFFLINE' : 'LOADING'} updatedAt={data?.updated_at ?? ''} />
      <ScrollingTicker items={tickerItems} />
      {scalars && <StatsBar items={statsItems} />}
      <TabBar active={activeTab} onSelect={setActiveTab} />

      {!scalars && !error ? (
        <div style={{ padding: 32, fontFamily: PA.hv, fontSize: 12, fontWeight: 300, color: PA.dim }}>Connecting…</div>
      ) : !scalars ? (
        <NoData error={error} />
      ) : (
        <>
          {activeTab === 'Signal'    && <SignalTab    s={scalars} allItems={allItems} loading={loading} />}
          {activeTab === 'Charts'    && <ChartsTab    live={live} />}
          {activeTab === 'Analysis'  && <AnalysisTab  live={live} s={scalars} />}
          {activeTab === 'Pricer'    && (data?.pricer
            ? <PricerTab p={data.pricer} scalars={scalars} />
            : <div style={{ padding: 32, fontFamily: PA.hv, fontSize: 12, fontWeight: 300, color: PA.dim }}>Pricer data not available — check pc_spot_pricer_real_v2.pkl exists and re-run export_json.py.</div>
          )}
          {activeTab === 'SarAI'    && <SarAITab s={scalars} />}
          {activeTab === 'Execution' && <ExecutionTab s={scalars} />}
          {activeTab === 'Readiness' && <ReadinessTab s={scalars} hasLive={live.length > 0} />}
          {activeTab === 'News'      && <NewsTab feeds={feeds} allItems={allItems} loading={loading} />}
        </>
      )}
    </div>
  )
}
