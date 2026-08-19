'use client'

import { useState } from 'react'
import {
  AppWindow,
  ArrowLeft,
  ArrowRight,
  ChevronDown,
  CircleUserRound,
  Compass,
  Expand,
  Gamepad2,
  Globe2,
  Grid2X2,
  Home,
  Maximize2,
  Menu,
  MoreHorizontal,
  Plus,
  Search,
  Shield,
  Sparkles,
  Star,
  TerminalSquare,
  X,
  Zap,
} from 'lucide-react'

const games = [
  { id: 'orbit', name: 'Orbit Rush', category: 'Arcade', icon: '◒', tone: 'cyan', description: 'Dodge the debris. Beat the clock.' },
  { id: 'neon', name: 'Neon Drift', category: 'Racing', icon: '✦', tone: 'pink', description: 'Cut through the city after dark.' },
  { id: 'pixel', name: 'Pixel Quest', category: 'Adventure', icon: '◆', tone: 'gold', description: 'A tiny world with a big secret.' },
  { id: 'chess', name: 'Checkmate', category: 'Strategy', icon: '♞', tone: 'violet', description: 'Think three moves ahead.' },
]

const apps = [
  { id: 'notion', name: 'Notion', category: 'Productivity', icon: 'N', tone: 'paper' },
  { id: 'terminal', name: 'Terminal', category: 'Utility', icon: '>_', tone: 'green' },
  { id: 'drive', name: 'Drive', category: 'Storage', icon: '△', tone: 'blue' },
  { id: 'music', name: 'Soundroom', category: 'Audio', icon: '◉', tone: 'orange' },
]

function Logo({ small = false }: { small?: boolean }) {
  return <div className={`sentinel-mark ${small ? 'sentinel-mark-small' : ''}`} aria-label="Sentinel logo"><span /><span /><span /></div>
}

function TopNav({ active, setActive }: { active: string; setActive: (tab: string) => void }) {
  return (
    <header className="top-nav">
      <div className="brand-lockup" onClick={() => setActive('browser')} role="button" tabIndex={0}>
        <Logo small />
        <span>Sentinel</span>
      </div>
      <nav className="main-tabs" aria-label="Primary navigation">
        {[
          { id: 'browser', label: 'Browser', icon: Globe2 },
          { id: 'apps', label: 'Apps', icon: AppWindow },
          { id: 'games', label: 'Games', icon: Gamepad2 },
          { id: 'search', label: 'Search', icon: Search },
        ].map(({ id, label, icon: Icon }) => (
          <button key={id} className={`main-tab ${active === id ? 'active' : ''}`} onClick={() => setActive(id)}>
            <Icon size={16} strokeWidth={1.8} /> {label}
          </button>
        ))}
      </nav>
      <div className="nav-actions">
        <button className="icon-button" aria-label="Open menu"><Menu size={17} /></button>
        <button className="profile-button" aria-label="Account"><CircleUserRound size={18} /></button>
      </div>
    </header>
  )
}

function BrowserHome({ launch }: { launch: (item: { name: string; category?: string; icon: string; tone: string }) => void }) {
  return (
    <section className="browser-shell">
      <div className="browser-tabs">
        <div className="browser-tab selected"><Globe2 size={13} /><span>Sentinel — Home</span><X size={13} /></div>
        <button className="new-tab" aria-label="New tab"><Plus size={15} /></button>
        <div className="window-controls"><span /><span /><span /></div>
      </div>
      <div className="browser-toolbar">
        <div className="browser-history"><ArrowLeft size={16} /><ArrowRight size={16} /><RotateIcon /></div>
        <div className="address-bar"><Shield size={13} /><span>sentinel.local</span><Star size={13} className="address-star" /></div>
        <MoreHorizontal size={18} className="toolbar-more" />
      </div>
      <div className="favorites-bar"><span>Sentinel</span><span>Apps</span><span>Games</span><span>Recently used</span></div>
      <div className="browser-page">
        <div className="browser-hero">
          <Logo />
          <h1>Sentinel</h1>
          <p>Your private launchpad for the web, apps, and play.</p>
          <div className="search-box"><Search size={18} /><span>Search</span><kbd>⌘ K</kbd></div>
        </div>
        <div className="quick-section">
          <div className="section-heading"><span>Quick selection</span><button>Customize <ChevronDown size={13} /></button></div>
          <div className="quick-grid">
            {[...apps.slice(0, 2), ...games.slice(0, 2)].map((item) => <LaunchTile key={item.id} item={item} onClick={() => launch(item)} />)}
          </div>
        </div>
        <div className="browser-footer"><Sparkles size={13} /> <span>Everything you need, one quiet place.</span></div>
      </div>
    </section>
  )
}

function RotateIcon() { return <svg className="rotate-icon" viewBox="0 0 24 24" aria-label="Reload"><path d="M20 11a8.1 8.1 0 0 0-14.8-4.3L3 9m0-5v5h5M4 13a8.1 8.1 0 0 0 14.8 4.3L21 15m0 5v-5h-5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg> }

function LaunchTile({ item, onClick }: { item: { name: string; category?: string; icon: string; tone: string }; onClick: () => void }) {
  return <button className="launch-tile" onClick={onClick}><div className={`app-icon tone-${item.tone}`}>{item.icon}</div><div><strong>{item.name}</strong><span>{item.category}</span></div><ArrowRight size={14} /></button>
}

function LibraryView({ type, launch }: { type: 'apps' | 'games'; launch: (item: { name: string; category?: string; icon: string; tone: string }) => void }) {
  const items = type === 'games' ? games : apps
  return <section className="library-view"><div className="view-intro"><div><div className="eyebrow"><span className="status-dot" /> Sentinel / {type}</div><h1>{type === 'games' ? 'Play something.' : 'Your workspace.'}</h1></div><button className="filter-button"><Grid2X2 size={15} /> All {type}<ChevronDown size={14} /></button></div><div className="library-grid">{items.map(item => <button className="library-card" aria-label={`Open ${item.name}`} key={item.id} onClick={() => launch(item)}><div className={`card-icon tone-${item.tone}`}>{item.icon}</div></button>)}</div></section>
}

function PlayerView({ item, goBack, setActive }: { item: { name: string; category?: string; icon: string; tone: string }; goBack: () => void; setActive: (tab: string) => void }) {
  return <section className="player-view"><div className="player-topline"><button className="back-button" onClick={goBack}><ArrowLeft size={15} /> Back to library</button><span className="player-path">Sentinel / {item.category}</span></div><div className="player-layout"><div className="player-main"><div className={`player-stage tone-${item.tone}`}><div className="stage-grid" /><div className="stage-content"><div className={`stage-logo tone-${item.tone}`}>{item.icon}</div><span className="stage-label">Ready to launch</span><h1>{item.name}</h1><button className="launch-button"><Zap size={15} fill="currentColor" /> Start {item.category?.toLowerCase()}</button></div><div className="stage-corner">SNTL / 001</div></div><div className="player-bar"><div className="player-title"><div className={`tiny-icon tone-${item.tone}`}>{item.icon}</div><div><strong>{item.name}</strong><span>{item.category}</span></div></div><div className="player-controls"><button aria-label="Fullscreen"><Maximize2 size={16} /></button><button aria-label="More options"><MoreHorizontal size={17} /></button></div></div></div><aside className="side-rail"><div className="rail-label">Explore</div><button className="rail-link" onClick={() => setActive('apps')}><AppWindow size={17} /><span>Apps</span></button><button className="rail-link" onClick={() => setActive('games')}><Gamepad2 size={17} /><span>Games</span></button><div className="rail-divider" />{[...apps.slice(0, 2), ...games.slice(0, 2)].map(rail => <button className="rail-app" key={rail.id} onClick={() => setActive(rail.category === 'Arcade' || rail.category === 'Racing' || rail.category === 'Adventure' || rail.category === 'Strategy' ? 'games' : 'apps')}><div className={`tiny-icon tone-${rail.tone}`}>{rail.icon}</div><span>{rail.name}</span></button>)}</aside></div></section>
}

function SearchView({ launch }: { launch: (item: { name: string; category?: string; icon: string; tone: string }) => void }) {
  const items = [...apps, ...games]
  return <section className="search-view"><div className="eyebrow"><span className="status-dot" /> Sentinel / search</div><h1>Find your next place.</h1><div className="large-search"><Search size={19} /><input autoFocus aria-label="Search apps and games" placeholder="Search apps and games" /><kbd>⌘ K</kbd></div><div className="search-results">{items.map(item => <button key={item.id} className="search-result" aria-label={`Open ${item.name}`} onClick={() => launch(item)}><div className={`card-icon tone-${item.tone}`}>{item.icon}</div></button>)}</div></section>
}

export default function Page() {
  const [active, setActive] = useState('browser')
  const [selected, setSelected] = useState<{ name: string; category?: string; icon: string; tone: string } | null>(null)
  const launch = (item: { name: string; category?: string; icon: string; tone: string }) => setSelected(item)
  const navigate = (tab: string) => { setSelected(null); setActive(tab) }
  return <main className="sentinel-app"><TopNav active={selected ? 'player' : active} setActive={navigate} />{selected ? <PlayerView item={selected} goBack={() => setSelected(null)} setActive={navigate} /> : active === 'browser' ? <BrowserHome launch={launch} /> : active === 'search' ? <SearchView launch={launch} /> : <LibraryView type={active as 'apps' | 'games'} launch={launch} />}<div className="ambient-line" /></main>
}
