'use client'

import { type ChangeEvent, type FormEvent, type ReactNode, useEffect, useMemo, useState } from 'react'

type Section = 'Overview' | 'Filing research' | 'Markets & watchlists' | 'Portfolio' | 'Mutual funds' | 'RBI & economy' | 'System status'
type MacroRow = { series: string; period: string; value: string; unit: string; observed_at: string; source_url: string }
type Health = { status?: string; database?: string; providers?: Record<string, boolean> }
type Metrics = { sample_count?: number; latency_ms?: { p50: number | null; p95: number | null }; scope?: string }
type Watchlist = { id: number; name: string; tickers: string[] }
type Announcement = { ticker: string; headline: string; category: string; summary: string; source: string; source_url: string; published_at: string }
type Citation = { document: string; page: number }
type ResearchAnswer = { answer: string; citations: Citation[]; sources?: { document: string; page: number; text: string }[]; tools?: { tool: string; status: string; display?: string; count?: number }[]; provider?: string; prompt_version?: string }
type PriceRow = { date: string; close: number; volume: number }
type Prices = { ticker: string; provider: string; source_url: string; as_of: string; prices: PriceRow[] }
type Scheme = { scheme_code: string; scheme_name: string }
type FundCompare = { scheme_code: string; scheme_name?: string; category?: string; expense_ratio_pct?: string | null; nav_start?: string; nav_start_date?: string; nav_latest?: string; nav_latest_date?: string; nav_change_pct?: string; error?: string; source_url?: string }
type FundOverlap = { scheme_codes: string[]; common_tickers: string[]; overlap_pct: number }
type NavPoint = { date: string; nav: string }
type Portfolio = { total_value: string; holding_count: number; sector_allocation: { sector: string; value: string; weight_pct: string }[]; holdings_overlap: { group_a: string; group_b: string; shared_tickers: string[]; overlap_pct: string }[]; method: string }
type ApiError = { error?: string; detail?: string }

const API = '/api/backend/'
const dateSortValue = (value: string) => {
  const parts = value.split('-')
  return parts.length === 3 && parts[0].length === 2 ? Date.UTC(Number(parts[2]), Number(parts[1]) - 1, Number(parts[0])) : Date.parse(value)
}
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(API + path, { ...init, cache: 'no-store' })
  const data = await response.json().catch(() => ({})) as T & ApiError
  if (!response.ok) throw new Error(data.error || data.detail || 'The request could not be completed.')
  return data
}
const jsonPost = (value: unknown): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) })
const number = (value: string | number | null | undefined, digits = 2) => value == null || value === '' ? '—' : Number.isFinite(Number(value)) ? Number(value).toLocaleString('en-IN', { maximumFractionDigits: digits }) : String(value)
const money = (value: string | number | null | undefined) => value == null || value === '' ? '—' : '₹' + number(value)
const initials = (value: string) => value.split(' ').map(part => part[0]).join('').slice(0, 2).toUpperCase()

const iconData: Record<string, string> = {
  Overview: 'M3 3h8v8H3z M13 3h8v5h-8z M13 10h8v11h-8z M3 13h8v8H3z',
  'Filing research': 'M6 2h9l5 5v15H6z M14 2v6h6 M9 13h8 M9 17h8 M9 9h2',
  'Markets & watchlists': 'M3 20h18 M5 16l4-5 4 3 6-8 M16 6h3v3',
  Portfolio: 'M3 7h18v13H3z M7 7V4h10v3 M3 11h18 M10 11v3h4v-3',
  'Mutual funds': 'M4 20V9 M10 20V4 M16 20v-8 M22 20H2',
  'RBI & economy': 'M3 9h18L12 3z M5 10v8 M9 10v8 M15 10v8 M19 10v8 M3 21h18 M2 18h20',
  'System status': 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M19 12a7 7 0 0 0-.5-2.6l1.4-1.1-1.6-2.8-1.7.7a7 7 0 0 0-2.3-1.3L14 3h-4l-.3 1.9a7 7 0 0 0-2.3 1.3l-1.7-.7-1.6 2.8 1.4 1.1a7 7 0 0 0 0 3.2l-1.4 1.1 1.6 2.8 1.7-.7a7 7 0 0 0 2.3 1.3L10 21h4l.3-1.9a7 7 0 0 0 2.3-1.3l1.7.7 1.6-2.8-1.4-1.1A7 7 0 0 0 19 12Z',
  search: 'm20 20-4.5-4.5 M18 10.5a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z',
  arrow: 'M5 12h14 M13 6l6 6-6 6',
  plus: 'M12 5v14 M5 12h14',
  bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9 M10 21h4',
  settings: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M19 12a7 7 0 0 0-.5-2.6l1.4-1.1-1.6-2.8-1.7.7a7 7 0 0 0-2.3-1.3L14 3h-4l-.3 1.9a7 7 0 0 0-2.3 1.3l-1.7-.7-1.6 2.8 1.4 1.1a7 7 0 0 0 0 3.2l-1.4 1.1 1.6 2.8 1.7-.7a7 7 0 0 0 2.3 1.3L10 21h4l.3-1.9a7 7 0 0 0 2.3-1.3l1.7.7 1.6-2.8-1.4-1.1A7 7 0 0 0 19 12Z',
}
function Icon({ name, size = 18 }: { name: string; size?: number }) {
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d={iconData[name] || iconData.Overview} /></svg>
}
function Button({ children, onClick, secondary = false, disabled = false, type = 'button', className = '' }: { children: ReactNode; onClick?: () => void; secondary?: boolean; disabled?: boolean; type?: 'button' | 'submit'; className?: string }) {
  return <button type={type} onClick={onClick} disabled={disabled} className={'button ' + (secondary ? 'button-secondary ' : '') + className}>{children}</button>
}
function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return <label className="field"><span className="field-label">{label}</span>{children}{hint ? <small className="field-hint">{hint}</small> : null}</label>
}
function PageTitle({ eyebrow, title, subtitle, action }: { eyebrow: string; title: string; subtitle: string; action?: ReactNode }) {
  return <div className="page-title"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p></div>{action ? <div className="page-title-action">{action}</div> : null}</div>
}
function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={'card ' + className}>{children}</section>
}
function CardTitle({ title, note, action }: { title: string; note?: string; action?: ReactNode }) {
  return <div className="card-title"><div><h2>{title}</h2>{note ? <p>{note}</p> : null}</div>{action}</div>
}
function Notice({ children, tone = 'info' }: { children: ReactNode; tone?: 'info' | 'warning' | 'success' }) {
  return <div className={'notice notice-' + tone}>{children}</div>
}
function ErrorMessage({ children }: { children: string }) {
  return <div className="error-message" role="alert">{children}</div>
}
function Table({ headers, rows }: { headers: string[]; rows: ReactNode[][] }) {
  return <div className="table-wrap"><table><thead><tr>{headers.map(header => <th key={header}>{header}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{row.map((cell, cellIndex) => <td key={cellIndex}>{cell}</td>)}</tr>)}</tbody></table></div>
}
function Chart({ values, labels, color = '#ed6b24' }: { values: number[]; labels?: string[]; color?: string }) {
  if (values.length < 2) return <div className="chart-empty">More history is needed to draw a chart.</div>
  const min = Math.min(...values), max = Math.max(...values), span = max - min || 1
  const points = values.map((value, index) => (24 + index * (552 / (values.length - 1))) + ',' + (126 - (value - min) / span * 100)).join(' ')
  return <div className="chart-frame"><svg viewBox="0 0 600 160" role="img" aria-label="Historical data chart" preserveAspectRatio="none"><defs><linearGradient id="chartFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor={color} stopOpacity=".2"/><stop offset="100%" stopColor={color} stopOpacity="0"/></linearGradient></defs><line x1="24" y1="130" x2="576" y2="130" stroke="#e9e7e3"/><line x1="24" y1="80" x2="576" y2="80" stroke="#efeeeb" strokeDasharray="4 6"/><line x1="24" y1="30" x2="576" y2="30" stroke="#efeeeb" strokeDasharray="4 6"/><polygon points={'24,145 ' + points + ' 576,145'} fill="url(#chartFill)"/><polyline points={points} fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/></svg><div className="chart-labels"><span>{labels?.[0] || ''}</span><span>{labels?.[Math.floor((labels?.length || 0) / 2)] || ''}</span><span>{labels?.[(labels?.length || 1) - 1] || ''}</span></div></div>
}
function MacroBars({ rows }: { rows: MacroRow[] }) {
  const shown = rows.filter(row => /repo|cpi|wpi|cash reserve|statutory liquidity/i.test(row.series)).slice(0, 6)
  const max = Math.max(10, ...shown.map(row => Math.abs(Number(row.value))))
  if (!shown.length) return <div className="empty-state">Macro records will appear here when the API is connected.</div>
  return <div className="macro-bars">{shown.map((row, index) => <div className="macro-bar-row" key={row.series + row.period + index}><div className="macro-bar-caption"><span>{row.series}</span><strong>{number(row.value)} <small>{row.unit}</small></strong></div><div className="macro-track"><i style={{ width: Math.min(100, Math.max(3, Math.abs(Number(row.value)) / max * 100)) + '%' }} /></div><small className="muted">{row.period}</small></div>)}</div>
}

function ResearchView() {
  const [company, setCompany] = useState('tcs')
  const [language, setLanguage] = useState('en')
  const [question, setQuestion] = useState('')
  const [calcOperation, setCalcOperation] = useState('margin')
  const [calcValues, setCalcValues] = useState('')
  const [answer, setAnswer] = useState<ResearchAnswer | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [hasAsked, setHasAsked] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setAnswer(null); setHasAsked(true)
    if (question.trim().length < 3) { setError('Please enter a question with at least three characters.'); return }
    const raw = calcValues.trim()
    let calculation: { operation: string; values: number[] } | null = null
    if (raw) {
      const values = raw.split(',').map(value => Number(value.trim()))
      if (values.some(value => !Number.isFinite(value))) { setError('Enter calculator inputs as numbers separated by commas.'); return }
      calculation = { operation: calcOperation, values }
    }
    setBusy(true)
    try {
      let sessionId = localStorage.getItem('finsight-session-v1')
      if (!sessionId) { sessionId = crypto.randomUUID(); localStorage.setItem('finsight-session-v1', sessionId) }
      const controller = new AbortController()
      const timeout = window.setTimeout(() => controller.abort(), 125000)
      let result: ResearchAnswer
      try {
        result = await api<ResearchAnswer>('api/v1/ask', { ...jsonPost({ company, question: question.trim(), language, session_id: sessionId, calculation }), signal: controller.signal })
      } finally { window.clearTimeout(timeout) }
      setAnswer(result)
    } catch (caught) {
      setError(caught instanceof DOMException && caught.name === 'AbortError'
        ? 'This filing search took longer than 125 seconds. Check that the backend and vector index are ready, then try again.'
        : caught instanceof Error ? caught.message : 'The research request failed.')
    }
    finally { setBusy(false) }
  }
  return <>
    <PageTitle eyebrow="Company filings" title="Filing research" subtitle="Ask a precise question and review the filing passages behind the answer." />
    <Notice tone="warning"><strong>Research and explanation only.</strong> FinSight does not give personalized investment advice or price predictions. Answers depend on the indexed documents and any configured language model.</Notice>
    <div className="content-grid research-grid">
      <Card className="research-form-card"><CardTitle title="Ask across company filings" note="Choose an indexed company, then ask about a report, quarter, or specific figure." />
        <form onSubmit={submit} className="stack-form">
          <div className="form-row"><Field label="Company"><select value={company} onChange={event => setCompany(event.target.value)}><option value="tcs">Tata Consultancy Services</option><option value="infosys">Infosys</option></select></Field><Field label="Answer language"><select value={language} onChange={event => setLanguage(event.target.value)}><option value="en">English</option><option value="hi">हिन्दी</option><option value="bn">বাংলা</option><option value="ta">தமிழ்</option><option value="te">తెలుగు</option><option value="mr">मराठी</option></select></Field></div>
          <Field label="Your question"><textarea value={question} onChange={event => setQuestion(event.target.value)} maxLength={1600} rows={5} placeholder="For example: What did management say about revenue growth in Q3 FY2026?" /></Field>
          <div className="soft-panel"><div className="soft-panel-title"><Icon name="Portfolio" size={16} /> Optional calculator</div><p>Numbers are calculated by deterministic code, not guessed by the language model.</p><div className="form-row"><Field label="Calculation"><select value={calcOperation} onChange={event => setCalcOperation(event.target.value)}><option value="margin">Margin (%) — profit, revenue</option><option value="percentage_change">Change (%) — old, new</option><option value="ratio">Ratio — numerator, denominator</option><option value="sum">Sum</option><option value="difference">Difference — first, second</option></select></Field><Field label="Numbers"><input value={calcValues} onChange={event => setCalcValues(event.target.value)} placeholder="e.g. 250, 1000" /></Field></div></div>
          {error ? <ErrorMessage>{error}</ErrorMessage> : null}
          <Button type="submit" disabled={busy}>{busy ? 'Searching filings…' : 'Ask with citations'} <Icon name="arrow" size={16} /></Button>
        </form>
      </Card>
      <Card className="answer-card"><CardTitle title="Research answer" note="Retrieved evidence, citations, and the tools used appear here." />
        {!answer && !busy && error ? <div className="empty-large research-error-state"><span className="empty-icon"><Icon name="Filing research" size={22} /></span><h3>We couldn’t retrieve an answer</h3><p>{error}</p><p>Check that the company’s filings are indexed and the backend is running. You can retry the same question.</p></div> : null}
        {!answer && !busy && !error && !hasAsked ? <div className="empty-large"><span className="empty-icon"><Icon name="Filing research" size={22} /></span><h3>Your answer will appear here</h3><p>Try a specific period and figure, such as “What was TCS net profit in Q3 FY2026?”</p><div className="suggestion-list"><button onClick={() => setQuestion('Summarize the latest available annual report.')}>Summarize the latest annual report <Icon name="arrow" size={14} /></button><button onClick={() => setQuestion('What was the net profit in Q3 FY2026?')}>Find a quarterly figure <Icon name="arrow" size={14} /></button><button onClick={() => setQuestion('What risks did management describe?')}>Explain reported business risks <Icon name="arrow" size={14} /></button></div></div> : null}
        {busy ? <div className="loading-state"><span className="spinner" />Searching the indexed filings and checking source passages…</div> : null}
        {answer ? <div className="answer-content"><div className="answer-meta"><span className="pill pill-orange">{answer.provider || 'Research response'}</span><span className="pill">{answer.prompt_version || 'Source-linked'}</span></div><p className="answer-text">{answer.answer}</p>{answer.tools?.length ? <div className="tool-row">{answer.tools.map(tool => <span className="tool-chip" key={tool.tool}><i />{tool.tool.replaceAll('_', ' ')} · {tool.status}</span>)}</div> : null}{answer.citations?.length ? <><h3 className="subheading">Sources cited</h3><div className="citation-list">{answer.citations.map((citation, index) => <a className="citation" key={citation.document + citation.page + index} href={`/api/backend/api/v1/documents/${company}/${encodeURIComponent(citation.document)}/pdf#page=${citation.page}`} target="_blank" rel="noopener noreferrer" aria-label={`Open ${citation.document}, page ${citation.page}, in a new tab`}><span className="citation-page">p. {citation.page}</span><span>{citation.document}</span><span className="citation-open" aria-hidden="true">↗</span></a>)}</div></> : <Notice tone="warning">No supporting filing page was returned for this answer.</Notice>}{answer.sources?.length ? <details className="source-details"><summary>Review retrieved passages</summary>{answer.sources.map((source, index) => <article key={source.document + index}><strong>{source.document} · page {source.page}</strong><pre className="source-excerpt">{source.text}</pre></article>)}</details> : null}</div> : null}
      </Card>
    </div>
    <CalculatorTool />
  </>
}

function CalculatorTool() {
  const [operation, setOperation] = useState('margin')
  const [valuesText, setValuesText] = useState('')
  const [result, setResult] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function calculate(event: FormEvent) {
    event.preventDefault(); setError(''); setResult('')
    const values = valuesText.split(',').map(value => Number(value.trim()))
    if (!valuesText.trim() || values.some(value => !Number.isFinite(value))) { setError('Enter one or more finite numbers, separated by commas.'); return }
    setBusy(true)
    try { const data = await api<{ display: string }>('api/v1/calculate', jsonPost({ operation, values })); setResult(data.display) }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'Calculation failed.') }
    finally { setBusy(false) }
  }
  return <Card className="calculator-card"><CardTitle title="Deterministic financial calculator" note="Use the same arithmetic tool without asking a filing question. The LLM does not calculate these values." />
    <form className="calculator-form" onSubmit={calculate}><Field label="Calculation"><select value={operation} onChange={event => setOperation(event.target.value)}><option value="margin">Margin (%) — profit, revenue</option><option value="percentage_change">Percentage change (%) — old, new</option><option value="ratio">Ratio — numerator, denominator</option><option value="sum">Sum — one or more numbers</option><option value="difference">Difference — first, second</option></select></Field><Field label="Numbers, comma-separated"><input value={valuesText} onChange={event => setValuesText(event.target.value)} placeholder="e.g. 250, 1000" /></Field><Button type="submit" disabled={busy}>{busy ? 'Calculating…' : 'Calculate'} <Icon name="arrow" size={15} /></Button></form>
    {error ? <ErrorMessage>{error}</ErrorMessage> : null}{result ? <div className="calculator-result"><span>Deterministic result</span><strong>{result}</strong></div> : null}
  </Card>
}

function MarketsView() {
  const [ticker, setTicker] = useState('TCS')
  const [period, setPeriod] = useState('1y')
  const [prices, setPrices] = useState<Prices | null>(null)
  const [priceError, setPriceError] = useState('')
  const [priceBusy, setPriceBusy] = useState(false)
  const [watchlists, setWatchlists] = useState<Watchlist[]>([])
  const [watchText, setWatchText] = useState('TCS, INFY')
  const [watchError, setWatchError] = useState('')
  const [announcements, setAnnouncements] = useState<Announcement[]>([])
  const [announcementError, setAnnouncementError] = useState('')
  const [saved, setSaved] = useState(false)
  async function loadPrices(event?: FormEvent) {
    event?.preventDefault(); setPriceBusy(true); setPriceError(''); setPrices(null)
    try { const result = await api<Prices>('api/v1/prices/' + encodeURIComponent(ticker.trim()) + '?period=' + period); setPrices(result) }
    catch (caught) { setPriceError(caught instanceof Error ? caught.message : 'Price history is unavailable.') }
    finally { setPriceBusy(false) }
  }
  async function loadLists() {
    try { const result = await api<{ watchlists: Watchlist[] }>('api/v1/watchlists'); setWatchlists(result.watchlists); if (result.watchlists.length) setWatchText(result.watchlists[0].tickers.join(', ')) }
    catch (caught) { setWatchError(caught instanceof Error ? caught.message : 'Could not load your watchlists.') }
  }
  async function saveList(event: FormEvent) {
    event.preventDefault(); setWatchError(''); setSaved(false)
    const tickers = watchText.split(',').map(item => item.trim().toUpperCase()).filter(Boolean)
    try { await api('api/v1/watchlists/save', jsonPost({ name: 'My watchlist', tickers })); setSaved(true); await loadLists(); await loadAnnouncements() }
    catch (caught) { setWatchError(caught instanceof Error ? caught.message : 'Could not save your watchlist.') }
  }
  async function loadAnnouncements() {
    setAnnouncementError('')
    try { const result = await api<{ announcements: Announcement[] }>('api/v1/announcements'); setAnnouncements(result.announcements) }
    catch (caught) { setAnnouncementError(caught instanceof Error ? caught.message : 'Could not load announcements.') }
  }
  useEffect(() => {
    let cancelled = false
    Promise.all([api<{ watchlists: Watchlist[] }>('api/v1/watchlists'), api<{ announcements: Announcement[] }>('api/v1/announcements')])
      .then(([lists, news]) => {
        if (cancelled) return
        setWatchlists(lists.watchlists)
        if (lists.watchlists.length) setWatchText(lists.watchlists[0].tickers.join(', '))
        setAnnouncements(news.announcements)
      })
      .catch(caught => {
        if (cancelled) return
        const message = caught instanceof Error ? caught.message : 'Could not load watchlist data.'
        setWatchError(message)
        setAnnouncementError(message)
      })
    return () => { cancelled = true }
  }, [])
  const chartValues = prices?.prices.map(item => Number(item.close)) || []
  return <>
    <PageTitle eyebrow="Listed markets" title="Markets & watchlists" subtitle="Explore historical price series and approved company announcements for your watchlist." />
    <Notice><strong>Source note.</strong> Price history comes from Yahoo Finance through yfinance and is secondary, not exchange-certified. Verify important figures against the exchange or issuer source.</Notice>
    <div className="content-grid">
      <Card className="span-8"><CardTitle title="Historical price explorer" note="Load a price history, check the source date, and inspect closing values." />
        <form className="form-row market-form" onSubmit={loadPrices}><Field label="NSE ticker"><input value={ticker} onChange={event => setTicker(event.target.value)} maxLength={32} placeholder="TCS" /></Field><Field label="Period"><select value={period} onChange={event => setPeriod(event.target.value)}><option value="1mo">1 month</option><option value="3mo">3 months</option><option value="6mo">6 months</option><option value="1y">1 year</option><option value="5y">5 years</option></select></Field><div className="form-action"><Button type="submit" disabled={priceBusy}>{priceBusy ? 'Loading…' : 'Load history'} <Icon name="arrow" size={15} /></Button></div></form>
        {priceError ? <ErrorMessage>{priceError}</ErrorMessage> : null}{priceBusy ? <div className="loading-state"><span className="spinner" />Retrieving market history…</div> : null}
        {prices ? <div className="price-result"><div className="price-summary"><div><span className="muted">Most recent close</span><strong>{money(prices.prices[prices.prices.length - 1]?.close)}</strong><small>{prices.ticker} · {prices.as_of}</small></div><span className="pill">{prices.prices.length} observations</span></div><Chart values={chartValues} labels={[prices.prices[0]?.date, prices.prices[Math.floor(prices.prices.length / 2)]?.date, prices.as_of]} /><p className="source-line">Source: {prices.provider} · <a href={prices.source_url} target="_blank" rel="noreferrer">Open source <Icon name="arrow" size={13} /></a></p><Table headers={['Date', 'Close', 'Volume']} rows={prices.prices.slice(-8).reverse().map(row => [row.date, money(row.close), number(row.volume, 0)])} /></div> : !priceError && !priceBusy ? <div className="empty-state">Enter a ticker and load its history to view a sourced chart.</div> : null}
      </Card>
      <Card className="span-4"><CardTitle title="Your watchlist" note="Save symbols for session-based research." action={<span className="count-badge">{watchlists.length} saved</span>} />
        <form onSubmit={saveList} className="stack-form"><Field label="Tickers, separated by commas"><textarea rows={3} value={watchText} onChange={event => setWatchText(event.target.value)} placeholder="TCS, INFY, RELIANCE" /></Field>{watchError ? <ErrorMessage>{watchError}</ErrorMessage> : null}{saved ? <div className="success-message">Watchlist saved.</div> : null}<Button type="submit">Save watchlist <Icon name="plus" size={15} /></Button></form>
        {watchlists.length ? <div className="watchlist-tags">{watchlists.flatMap(group => group.tickers).map((item, index) => <button key={item + index} onClick={() => setTicker(item)}>{item}</button>)}</div> : <p className="muted small-text">Your saved tickers will appear here.</p>}
      </Card>
      <Card className="span-12"><CardTitle title="Approved company announcements" note="Only human-approved, source-linked records for your watchlist are shown." action={<Button secondary onClick={() => void loadAnnouncements()}>Refresh</Button>} />
        {announcementError ? <ErrorMessage>{announcementError}</ErrorMessage> : null}{announcements.length ? <div className="announcement-list">{announcements.map((item, index) => <article className="announcement-row" key={item.ticker + item.published_at + index}><div className="announcement-symbol">{initials(item.ticker)}</div><div className="announcement-copy"><div className="announcement-meta"><strong>{item.ticker}</strong><span className="pill">{item.category}</span><time>{new Date(item.published_at).toLocaleDateString('en-IN')}</time></div><h3>{item.headline}</h3>{item.summary ? <p>{item.summary}</p> : null}<a href={item.source_url} target="_blank" rel="noreferrer">{item.source || 'View source'} <Icon name="arrow" size={13} /></a></div></article>)}</div> : <div className="empty-state">No approved announcements match this watchlist yet. An administrator must import and approve announcements before they appear.{process.env.NEXT_PUBLIC_FINSIGHT_ADMIN_URL ? <> <a href={process.env.NEXT_PUBLIC_FINSIGHT_ADMIN_URL} target="_blank" rel="noreferrer">Open staff review <Icon name="arrow" size={13} /></a></> : null}</div>}
      </Card>
    </div>
  </>
}

function PortfolioView() {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<Portfolio | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  function choose(event: ChangeEvent<HTMLInputElement>) { setResult(null); setError(''); setFile(event.target.files?.[0] || null) }
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setResult(null)
    if (!file) { setError('Choose a CSV file first.'); return }
    if (file.size > 2 * 1024 * 1024) { setError('The CSV must be smaller than 2 MiB.'); return }
    setBusy(true)
    try { const form = new FormData(); form.append('file', file); setResult(await api<Portfolio>('api/v1/portfolio/analyze', { method: 'POST', body: form })) }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'The portfolio could not be analyzed.') }
    finally { setBusy(false) }
  }
  return <>
    <PageTitle eyebrow="Holdings analysis" title="Portfolio explainer" subtitle="See sector exposure and holdings overlap from your own CSV. Your file is processed by the analysis API and is not represented as investment advice." />
    <div className="content-grid"><Card className="span-5"><CardTitle title="Upload holdings" note="The calculator uses the numbers in your file; it does not ask an LLM to calculate portfolio values." />
      <Notice><strong>CSV format:</strong> include <code>ticker,quantity</code> and either <code>market_value</code> or <code>price</code>. Add <code>sector</code> for sector exposure; add <code>fund</code> or <code>portfolio</code> labels to compare holdings overlap.</Notice>
      <form onSubmit={submit} className="stack-form"><Field label="Holdings CSV" hint="Maximum file size: 2 MiB. Up to 1,000 holdings."><input type="file" accept=".csv,text/csv" onChange={choose} /></Field>{file ? <div className="file-chip"><Icon name="Filing research" size={16} />{file.name}<span>{number(file.size, 0)} bytes</span></div> : null}{error ? <ErrorMessage>{error}</ErrorMessage> : null}<Button type="submit" disabled={busy}>{busy ? 'Calculating exposure…' : 'Analyze portfolio'} <Icon name="arrow" size={15} /></Button></form>
      <details className="source-details"><summary>View a sample CSV</summary><pre>ticker,quantity,price,sector,fund{'\n'}TCS,10,3500,Information Technology,Fund A{'\n'}INFY,8,1500,Information Technology,Fund A</pre></details>
    </Card>
    <Card className="span-7"><CardTitle title="Exposure report" note="A breakdown is shown after you submit a valid holdings file." />{result ? <div className="portfolio-result"><div className="result-stats"><div><small>Portfolio value</small><strong>{money(result.total_value)}</strong></div><div><small>Holdings</small><strong>{result.holding_count}</strong></div></div><div className="section-divider"><h3>Sector allocation</h3><p>Weights are calculated from the supplied market values.</p></div><div className="sector-bars">{result.sector_allocation.map(sector => <div className="sector-row" key={sector.sector}><div><span>{sector.sector}</span><strong>{sector.weight_pct}%</strong></div><div className="macro-track"><i style={{ width: Math.min(100, Number(sector.weight_pct)) + '%' }} /></div></div>)}</div>{result.holdings_overlap.length ? <><div className="section-divider"><h3>Holdings overlap</h3><p>Comparison between the groups named in your CSV.</p></div><Table headers={['Group A', 'Group B', 'Overlap', 'Shared tickers']} rows={result.holdings_overlap.map(item => [item.group_a, item.group_b, item.overlap_pct + '%', item.shared_tickers.join(', ') || 'None'])} /></> : null}<Notice>{result.method}</Notice></div> : <div className="empty-large"><span className="empty-icon"><Icon name="Portfolio" size={22} /></span><h3>Report will appear here</h3><p>Upload a holdings CSV to calculate allocation and overlap.</p></div>}</Card></div>
  </>
}

function FundsView() {
  const [query, setQuery] = useState('')
  const [schemes, setSchemes] = useState<Scheme[]>([])
  const [searchError, setSearchError] = useState('')
  const [searchBusy, setSearchBusy] = useState(false)
  const [selected, setSelected] = useState<Scheme[]>([])
  const [comparisons, setComparisons] = useState<FundCompare[]>([])
  const [overlaps, setOverlaps] = useState<FundOverlap[]>([])
  const [compareNotice, setCompareNotice] = useState('')
  const [compareError, setCompareError] = useState('')
  const [compareBusy, setCompareBusy] = useState(false)
  const [navCode, setNavCode] = useState('')
  const [navHistory, setNavHistory] = useState<NavPoint[]>([])
  const [navProvider, setNavProvider] = useState('')
  const [navSource, setNavSource] = useState('')
  const [navError, setNavError] = useState('')
  const [navBusy, setNavBusy] = useState(false)
  async function search(event: FormEvent) {
    event.preventDefault(); setSearchError(''); setSchemes([])
    if (query.trim().length < 2) { setSearchError('Type at least two characters to search.'); return }
    setSearchBusy(true)
    try { const response = await api<{ schemes: Scheme[] }>('api/v1/funds/search?q=' + encodeURIComponent(query.trim())); setSchemes(response.schemes) }
    catch (caught) { setSearchError(caught instanceof Error ? caught.message : 'Fund search failed.') }
    finally { setSearchBusy(false) }
  }
  function add(scheme: Scheme) { if (!selected.some(item => item.scheme_code === scheme.scheme_code) && selected.length < 5) setSelected(items => [...items, scheme]) }
  async function compare() {
    setCompareError(''); setCompareNotice(''); setComparisons([])
    if (selected.length < 2) { setCompareError('Choose at least two schemes to compare.'); return }
    setCompareBusy(true)
    try { const response = await api<{ comparisons: FundCompare[]; holdings_overlap: FundOverlap[]; notice: string }>('api/v1/funds/compare', jsonPost({ scheme_codes: selected.map(item => item.scheme_code) })); setComparisons(response.comparisons); setOverlaps(response.holdings_overlap); setCompareNotice(response.notice) }
    catch (caught) { setCompareError(caught instanceof Error ? caught.message : 'The funds could not be compared.') }
    finally { setCompareBusy(false) }
  }
  async function loadNav(event: FormEvent) {
    event.preventDefault(); setNavError(''); setNavHistory([])
    if (!/^\d+$/.test(navCode.trim())) { setNavError('Enter the numeric scheme code from the search results.'); return }
    setNavBusy(true)
    try { const response = await api<{ history: NavPoint[]; provider: string; source_url: string }>('api/v1/funds/nav/' + navCode.trim() + '?days=365'); setNavHistory(response.history); setNavProvider(response.provider); setNavSource(response.source_url) }
    catch (caught) { setNavError(caught instanceof Error ? caught.message : 'NAV history is unavailable.') }
    finally { setNavBusy(false) }
  }
  const orderedNav = useMemo(() => [...navHistory].sort((a, b) => dateSortValue(a.date) - dateSortValue(b.date)), [navHistory])
  return <>
    <PageTitle eyebrow="Mutual-fund research" title="Fund explorer" subtitle="Search schemes, inspect NAV history, and compare historical NAV movement using source-labelled data." />
    <Notice tone="warning"><strong>Check the source.</strong> Live NAV lookup uses the MFapi.in mirror unless local AMFI records are imported. Verify data with <a href="https://www.amfiindia.com/net-asset-value/nav-download" target="_blank" rel="noreferrer">AMFI</a>. NAV changes are not total returns, forecasts, or recommendations.</Notice>
    <div className="content-grid"><Card className="span-7"><CardTitle title="Find a scheme" note="Search by fund or scheme name; add up to five schemes for a one-year comparison." />
      <form className="inline-search" onSubmit={search}><Field label="Scheme name"><input value={query} onChange={event => setQuery(event.target.value)} maxLength={80} placeholder="e.g. HDFC Nifty 50 Index Fund" /></Field><Button type="submit" disabled={searchBusy}>{searchBusy ? 'Searching…' : <><Icon name="search" size={16} /> Search schemes</>}</Button></form>
      {searchError ? <ErrorMessage>{searchError}</ErrorMessage> : null}<div className="scheme-results">{schemes.map(scheme => <div className="scheme-item" key={scheme.scheme_code}><div><strong>{scheme.scheme_name}</strong><small>Scheme code {scheme.scheme_code}</small></div><Button secondary onClick={() => add(scheme)} disabled={selected.some(item => item.scheme_code === scheme.scheme_code) || selected.length >= 5}>{selected.some(item => item.scheme_code === scheme.scheme_code) ? 'Added' : 'Add'}</Button></div>)}</div>{!schemes.length && !searchError ? <div className="empty-state compact-empty">Search results appear here.</div> : null}
      <div className="selected-schemes"><div className="selection-heading"><h3>Selected schemes <span>{selected.length}/5</span></h3><button className="text-button" onClick={() => { setSelected([]); setComparisons([]) }}>Clear</button></div>{selected.length ? <div className="selected-list">{selected.map(scheme => <button key={scheme.scheme_code} onClick={() => setSelected(items => items.filter(item => item.scheme_code !== scheme.scheme_code))} aria-label={'Remove ' + scheme.scheme_name}>{scheme.scheme_name}<span>×</span></button>)}</div> : <p className="muted small-text">Add at least two schemes to compare.</p>}<Button onClick={() => void compare()} disabled={compareBusy}>{compareBusy ? 'Comparing…' : 'Compare one-year NAV'} <Icon name="arrow" size={15} /></Button></div>
      {compareError ? <ErrorMessage>{compareError}</ErrorMessage> : null}{comparisons.length ? <div className="comparison-result"><Table headers={['Scheme', 'Category', 'NAV at start', 'Latest NAV', '1-year NAV change', 'Expense ratio']} rows={comparisons.map(item => [<strong key="name">{item.scheme_name || item.scheme_code}</strong>, item.error || item.category || 'Not imported', item.nav_start ? money(item.nav_start) + ' · ' + item.nav_start_date : '—', item.nav_latest ? money(item.nav_latest) + ' · ' + item.nav_latest_date : '—', item.nav_change_pct == null ? '—' : item.nav_change_pct + '%', item.expense_ratio_pct == null ? 'Not imported' : item.expense_ratio_pct + '%'])} />{overlaps.length ? <Table headers={['Scheme pair', 'Holdings in common', 'Overlap']} rows={overlaps.map(item => [item.scheme_codes.join(' / '), item.common_tickers.join(', ') || '—', item.overlap_pct + '%'])} /> : null}<p className="source-line">{compareNotice}</p></div> : null}
    </Card>
    <Card className="span-5"><CardTitle title="NAV history" note="Load up to one year of source-labelled NAV observations for a scheme." />
      <form className="inline-search" onSubmit={loadNav}><Field label="Scheme code"><input inputMode="numeric" value={navCode} onChange={event => setNavCode(event.target.value)} placeholder="Enter scheme code" /></Field><Button type="submit" disabled={navBusy}>{navBusy ? 'Loading…' : 'Load history'}</Button></form>
      {navError ? <ErrorMessage>{navError}</ErrorMessage> : null}{orderedNav.length ? <div className="price-result"><div className="price-summary"><div><span className="muted">Latest NAV</span><strong>{money(orderedNav[orderedNav.length - 1]?.nav)}</strong><small>{orderedNav[orderedNav.length - 1]?.date}</small></div><span className="pill">{orderedNav.length} points</span></div><Chart values={orderedNav.map(item => Number(item.nav))} labels={[orderedNav[0]?.date, orderedNav[Math.floor(orderedNav.length / 2)]?.date, orderedNav[orderedNav.length - 1]?.date]} /><p className="source-line">{navProvider} · <a href={navSource} target="_blank" rel="noreferrer">View source <Icon name="arrow" size={13} /></a></p><Table headers={['Date', 'NAV']} rows={orderedNav.slice(-8).reverse().map(item => [item.date, money(item.nav)])} /></div> : !navError ? <div className="empty-state">Search for a scheme and enter its code to view historical NAV.</div> : null}
    </Card></div>
    <p className="page-footnote">Expense ratio and holdings overlap are shown only when source-linked factsheets have been imported. A missing value is left blank.</p>
  </>
}

function EconomyView({ rows, error, refresh }: { rows: MacroRow[]; error: string; refresh: (series?: string) => Promise<void> }) {
  const [filter, setFilter] = useState('')
  const visible = rows.filter(row => !filter || row.series.toLowerCase().includes(filter.toLowerCase()))
  const current = useMemo(() => {
    const repo = visible.find(row => /repo rate/i.test(row.series))
    const cpi = visible.find(row => /consumer price|cpi/i.test(row.series))
    const wpi = visible.find(row => /wholesale price|wpi/i.test(row.series))
    return { repo, cpi, wpi }
  }, [visible])
  const chartRows = visible.filter(row => /repo|cpi|wpi/i.test(row.series)).slice(0, 10)
  async function submit(event: FormEvent) { event.preventDefault(); await refresh(filter.trim()); }
  return <>
    <PageTitle eyebrow="Economic context" title="RBI & economy" subtitle="Review imported policy and macroeconomic records with their observation dates and sources." action={<Button secondary onClick={() => void refresh(filter.trim())}>Refresh data <Icon name="arrow" size={14} /></Button>} />
    <Notice>RBI policy records and government inflation releases provide historical context. They do not indicate a future market direction.</Notice>
    {error ? <ErrorMessage>{error}</ErrorMessage> : null}
    <div className="stat-grid"><div className="stat-card"><span>Policy repo rate</span><strong>{current.repo ? number(current.repo.value) + ' ' + current.repo.unit : '—'}</strong><small>{current.repo?.period || 'No record loaded'}</small></div><div className="stat-card"><span>Consumer inflation</span><strong>{current.cpi ? number(current.cpi.value) + ' ' + current.cpi.unit : '—'}</strong><small>{current.cpi?.period || 'No CPI record loaded'}</small></div><div className="stat-card"><span>Wholesale inflation</span><strong>{current.wpi ? number(current.wpi.value) + ' ' + current.wpi.unit : '—'}</strong><small>{current.wpi?.period || 'No WPI record loaded'}</small></div><div className="stat-card"><span>Records in view</span><strong>{number(visible.length, 0)}</strong><small>Each record retains its source</small></div></div>
    <div className="content-grid"><Card className="span-5"><CardTitle title="Indicator snapshot" note="Values returned by the configured data API." /><MacroBars rows={chartRows} /><p className="source-line">Rates and inflation vary by observation date; use the source links in the records table.</p></Card><Card className="span-7"><CardTitle title="Find a series" note="Filter loaded records by series name." />
      <form className="inline-search" onSubmit={submit}><Field label="Series name"><input value={filter} onChange={event => setFilter(event.target.value)} placeholder="e.g. Repo, CPI, WPI" /></Field><Button type="submit">Filter records <Icon name="search" size={15} /></Button></form>
      <div className="source-links"><a href="https://data.rbi.org.in/DBIE/" target="_blank" rel="noreferrer">RBI Database on Indian Economy <Icon name="arrow" size={13} /></a><a href="https://www.amfiindia.com/net-asset-value/nav-download" target="_blank" rel="noreferrer">AMFI NAV data <Icon name="arrow" size={13} /></a></div>
      <Notice tone="info">Need a longer time series? Download an allowed RBI DBIE series and import the source-linked CSV using the documented macro import command.</Notice>
    </Card><Card className="span-12"><CardTitle title="Source-linked observations" note="The table shows the reported period, observation timestamp, and original source." />{visible.length ? <Table headers={['Series', 'Period', 'Value', 'Unit', 'Observed at', 'Source']} rows={visible.map((row, index) => [<strong key={'series' + index}>{row.series}</strong>, row.period, number(row.value), row.unit, new Date(row.observed_at).toLocaleString('en-IN'), <a key={'source' + index} href={row.source_url} target="_blank" rel="noreferrer">Open source <Icon name="arrow" size={13} /></a>])} /> : <div className="empty-state">No matching records. Clear the filter or load another series.</div>}</Card></div>
  </>
}

function Overview({ rows, health, metrics, announcements, watchlists, error, onNavigate }: { rows: MacroRow[]; health: Health | null; metrics: Metrics | null; announcements: Announcement[]; watchlists: Watchlist[]; error: string; onNavigate: (section: Section) => void }) {
  const repo = rows.find(row => /repo rate/i.test(row.series))
  const cpi = rows.find(row => /consumer price|cpi/i.test(row.series))
  const wpi = rows.find(row => /wholesale price|wpi/i.test(row.series))
  const tickers = watchlists.flatMap(list => list.tickers)
  return <>
    <PageTitle eyebrow="Your research workspace" title="Good to see you." subtitle="Sourced company research and market context, in one clear view." action={<span className={'system-status ' + (health?.status === 'ok' ? 'is-healthy' : 'is-unknown')}><i />{health?.status === 'ok' ? 'API connected' : 'API status unknown'}</span>} />
    {error ? <Notice tone="warning">Some overview data could not be loaded: {error} Use the other sections to retry their data sources.</Notice> : null}
    <div className="stat-grid four-stats"><div className="stat-card"><div className="stat-symbol orange-symbol"><Icon name="RBI & economy" size={17} /></div><span>Policy repo rate</span><strong>{repo ? number(repo.value) + ' ' + repo.unit : '—'}</strong><small>{repo?.period || 'No record available'}</small></div><div className="stat-card"><div className="stat-symbol"><Icon name="RBI & economy" size={17} /></div><span>Consumer inflation</span><strong>{cpi ? number(cpi.value) + ' ' + cpi.unit : '—'}</strong><small>{cpi?.period || 'No CPI record'}</small></div><div className="stat-card"><div className="stat-symbol"><Icon name="RBI & economy" size={17} /></div><span>Wholesale inflation</span><strong>{wpi ? number(wpi.value) + ' ' + wpi.unit : '—'}</strong><small>{wpi?.period || 'No WPI record'}</small></div><div className="stat-card"><div className="stat-symbol"><Icon name="Markets & watchlists" size={17} /></div><span>Watchlist symbols</span><strong>{tickers.length || '—'}</strong><small>{tickers.length ? tickers.slice(0, 4).join(' · ') : 'Save a watchlist to track symbols'}</small></div></div>
    <div className="overview-grid"><Card className="overview-chart"><CardTitle title="Macro context" note="Selected source-linked RBI and inflation observations." action={<button className="text-link" onClick={() => onNavigate('RBI & economy')}>View all <Icon name="arrow" size={14} /></button>} /><MacroBars rows={rows} /><div className="chart-legend"><span><i className="legend-orange" />Policy and inflation data</span><span className="muted">Observed values · not forecasts</span></div></Card>
      <Card className="insight-card"><div className="insight-icon"><span>✳</span></div><span className="eyebrow">FinSight research assistant</span><h2>Ask a question with sources.</h2><p>Search indexed annual reports and earnings calls. Review the cited document pages alongside each answer.</p><Button onClick={() => onNavigate('Filing research')}>Start filing research <Icon name="arrow" size={15} /></Button><div className="assistant-foot"><span><i /> Filing retrieval</span><span><i /> Deterministic calculator</span></div></Card>
      <Card className="overview-activity"><CardTitle title="Your research tools" note="Choose a workspace to get started." /><div className="quick-grid"><button onClick={() => onNavigate('Markets & watchlists')}><span className="quick-icon"><Icon name="Markets & watchlists" /></span><strong>Market history</strong><small>Explore ticker prices</small><Icon name="arrow" size={15} /></button><button onClick={() => onNavigate('Portfolio')}><span className="quick-icon"><Icon name="Portfolio" /></span><strong>Portfolio analysis</strong><small>Upload a holdings CSV</small><Icon name="arrow" size={15} /></button><button onClick={() => onNavigate('Mutual funds')}><span className="quick-icon"><Icon name="Mutual funds" /></span><strong>Fund comparison</strong><small>Compare scheme NAVs</small><Icon name="arrow" size={15} /></button><button onClick={() => onNavigate('RBI & economy')}><span className="quick-icon"><Icon name="RBI & economy" /></span><strong>Economic records</strong><small>Review RBI and macro data</small><Icon name="arrow" size={15} /></button></div></Card>
      <Card className="overview-announcements"><CardTitle title="Watchlist announcements" note="Approved and sourced items for your saved tickers." action={<button className="text-link" onClick={() => onNavigate('Markets & watchlists')}>Open watchlist <Icon name="arrow" size={14} /></button>} />{announcements.length ? <div className="announcement-list">{announcements.slice(0, 3).map((item, index) => <article className="announcement-row" key={item.ticker + item.published_at + index}><div className="announcement-symbol">{initials(item.ticker)}</div><div className="announcement-copy"><div className="announcement-meta"><strong>{item.ticker}</strong><span className="pill">{item.category}</span></div><h3>{item.headline}</h3><time>{new Date(item.published_at).toLocaleDateString('en-IN')}</time></div></article>)}</div> : <div className="empty-inline"><Icon name="bell" size={18} /><span>No approved announcements for this watchlist yet.</span></div>}</Card>
    </div>
    <div className="footnote-line"><span>Research and explanation only. Not investment advice.</span><span>Database: {health?.database || 'not verified'} · {metrics?.sample_count ?? 0} local samples · P50 {metrics?.latency_ms?.p50 == null ? '—' : number(metrics.latency_ms.p50) + ' ms'} · P95 {metrics?.latency_ms?.p95 == null ? '—' : number(metrics.latency_ms.p95) + ' ms'}</span></div>
  </>
}

function OperationsView({ health, metrics }: { health: Health | null; metrics: Metrics | null }) {
  const healthy = health?.status === 'ok'
  return <>
    <PageTitle eyebrow="Service and review" title="System status" subtitle="Check the API connection, configured model providers, request latency, and staff review controls." />
    <div className="stat-grid"><div className="stat-card"><span>Application API</span><strong className={healthy ? 'status-good' : 'status-pending'}>{health?.status || 'Unknown'}</strong><small>GET /api/health</small></div><div className="stat-card"><span>Database</span><strong className={health?.database === 'ok' ? 'status-good' : 'status-pending'}>{health?.database || 'Unknown'}</strong><small>Conversation and imported data store</small></div><div className="stat-card"><span>OpenRouter provider key</span><strong className={health?.providers?.openrouter ? 'status-good' : 'status-pending'}>{health?.providers?.openrouter ? 'Configured' : 'Not configured'}</strong><small>GPT and other routed models</small></div><div className="stat-card"><span>Gemini provider key</span><strong className={health?.providers?.gemini ? 'status-good' : 'status-pending'}>{health?.providers?.gemini ? 'Configured' : 'Not configured'}</strong><small>Optional language generation</small></div><div className="stat-card"><span>OpenAI provider key</span><strong className={health?.providers?.openai ? 'status-good' : 'status-pending'}>{health?.providers?.openai ? 'Configured' : 'Not configured'}</strong><small>Optional fallback generation</small></div></div>
    <div className="content-grid"><Card className="span-5"><CardTitle title="API request latency" note="Samples are local to the Django worker process and reset when it restarts." /><div className="latency-grid"><div><span>P50</span><strong>{metrics?.latency_ms?.p50 == null ? '—' : number(metrics.latency_ms.p50) + ' ms'}</strong></div><div><span>P95</span><strong>{metrics?.latency_ms?.p95 == null ? '—' : number(metrics.latency_ms.p95) + ' ms'}</strong></div></div><p className="source-line">{metrics?.sample_count ?? 0} measured requests · {metrics?.scope || 'Metric scope unavailable.'}</p></Card><Card className="span-7"><CardTitle title="Staff review and prompt controls" note="These workflows stay behind Django staff authentication." /><div className="admin-feature-list"><div><span className="quick-icon"><Icon name="bell" /></span><div><strong>Announcement approval</strong><small>Review imported records before they are visible to users.</small></div></div><div><span className="quick-icon"><Icon name="Filing research" /></span><div><strong>Prompt versions and evaluation scores</strong><small>Inspect active prompts and scores recorded by the evaluation command.</small></div></div><div><span className="quick-icon"><Icon name="settings" /></span><div><strong>Fund factsheets and macro imports</strong><small>Manage source-linked records and staff-only data tools.</small></div></div></div>{process.env.NEXT_PUBLIC_FINSIGHT_ADMIN_URL ? <a className="button admin-button" href={process.env.NEXT_PUBLIC_FINSIGHT_ADMIN_URL} target="_blank" rel="noreferrer">Open Django staff console <Icon name="arrow" size={14} /></a> : <Notice tone="warning">Set NEXT_PUBLIC_FINSIGHT_ADMIN_URL to the deployed Django /admin/ URL to show the staff-console link.</Notice>}</Card></div>
  </>
}

export default function Home() {
  const [section, setSection] = useState<Section>('Overview')
  const [rows, setRows] = useState<MacroRow[]>([])
  const [health, setHealth] = useState<Health | null>(null)
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [watchlists, setWatchlists] = useState<Watchlist[]>([])
  const [announcements, setAnnouncements] = useState<Announcement[]>([])
  const [loadError, setLoadError] = useState('')
  const navigation: Section[] = ['Overview', 'Filing research', 'Markets & watchlists', 'Portfolio', 'Mutual funds', 'RBI & economy', 'System status']
  useEffect(() => {
    const saved = localStorage.getItem('finsight-theme-v1')
    const nextTheme = saved === 'dark' ? 'dark' : 'light'
    document.documentElement.dataset.theme = nextTheme
  }, [])
  function toggleTheme() {
    const nextTheme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = nextTheme
    localStorage.setItem('finsight-theme-v1', nextTheme)
  }
  useEffect(() => {
    async function loadOverview() {
      const tasks = await Promise.allSettled([
        api<{ observations: MacroRow[] }>('api/v1/macro'),
        api<Health>('api/health'),
        api<Metrics>('api/metrics'),
        api<{ watchlists: Watchlist[] }>('api/v1/watchlists'),
        api<{ announcements: Announcement[] }>('api/v1/announcements'),
      ])
      const failures: string[] = []
      if (tasks[0].status === 'fulfilled') setRows(tasks[0].value.observations); else failures.push('economic records')
      if (tasks[1].status === 'fulfilled') setHealth(tasks[1].value); else failures.push('API health')
      if (tasks[2].status === 'fulfilled') setMetrics(tasks[2].value); else failures.push('service metrics')
      if (tasks[3].status === 'fulfilled') setWatchlists(tasks[3].value.watchlists); else failures.push('watchlists')
      if (tasks[4].status === 'fulfilled') setAnnouncements(tasks[4].value.announcements); else failures.push('announcements')
      if (failures.length) setLoadError(failures.join(', '))
    }
    void loadOverview()
  }, [])
  return <div className="app-shell"><aside className="sidebar"><a className="brand" href="#overview" onClick={event => { event.preventDefault(); setSection('Overview') }}><span className="brand-mark">F</span><span>FinSight<small>RESEARCH WORKSPACE</small></span></a><div className="side-label">WORKSPACE</div><nav className="primary-nav" aria-label="Main navigation">{navigation.map(item => <button key={item} className={'nav-item ' + (section === item ? 'active' : '')} onClick={() => setSection(item)} aria-current={section === item ? 'page' : undefined}><Icon name={item} /><span>{item}</span>{item === 'Filing research' ? <span className="nav-indicator" /> : null}</button>)}</nav><div className="sidebar-bottom"><div className="side-label">ABOUT YOUR DATA</div><p>Sources are shown beside observations. Missing figures are left blank.</p><a href="https://www.amfiindia.com/terms-of-use" target="_blank" rel="noreferrer">Data and source notes <Icon name="arrow" size={13} /></a><div className="profile"><div className="avatar">FS</div><div><strong>Research workspace</strong><small>Local session</small></div><Icon name="settings" size={16} /></div></div></aside>
    <main className="main-area"><header className="topbar"><div className="breadcrumbs"><span>FinSight</span><b>/</b><strong>{section}</strong></div><div className="topbar-actions"><span className={'health-dot ' + (health?.status === 'ok' ? 'online' : '')} title={health?.status === 'ok' ? 'API connected' : 'API status unknown'} /><span className="topbar-status">{health?.status === 'ok' ? 'Connected' : 'Connecting'}</span><button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle light or dark theme" title="Change color theme"><span aria-hidden="true">☾ / ☀</span>Theme</button><button className="icon-button" aria-label="Go to filing research" onClick={() => setSection('Filing research')}><Icon name="bell" size={17} /></button><div className="avatar avatar-small">FS</div></div></header>
      <div className="page-content">{section === 'Overview' ? <Overview rows={rows} health={health} metrics={metrics} announcements={announcements} watchlists={watchlists} error={loadError} onNavigate={setSection} /> : null}{section === 'Filing research' ? <ResearchView /> : null}{section === 'Markets & watchlists' ? <MarketsView /> : null}{section === 'Portfolio' ? <PortfolioView /> : null}{section === 'Mutual funds' ? <FundsView /> : null}{section === 'RBI & economy' ? <EconomyView rows={rows} error={loadError} refresh={async series => { try { const response = await api<{ observations: MacroRow[] }>('api/v1/macro' + (series ? '?series=' + encodeURIComponent(series) : '')); setRows(response.observations); setLoadError('') } catch (caught) { setLoadError(caught instanceof Error ? caught.message : 'Could not refresh economic records.') } }} /> : null}{section === 'System status' ? <OperationsView health={health} metrics={metrics} /> : null}</div>
    </main></div>
}
