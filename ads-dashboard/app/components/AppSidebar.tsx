export function AppSidebar() {
  return (
    <aside className="sidebar">
      <div>
        <p className="eyebrow">Khai Hoan</p>
        <h1>Ads Ops</h1>
      </div>
      <nav aria-label="Main navigation">
        <a className="active" href="/">
          Campaigns
        </a>
        <a href="/">Exports</a>
        <a href="/">Notion sync</a>
        <a href="/">Presets</a>
      </nav>
    </aside>
  );
}
