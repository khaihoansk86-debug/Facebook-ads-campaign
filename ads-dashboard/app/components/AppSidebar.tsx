export function AppSidebar() {
  return (
    <aside className="sidebar">
      <div>
        <p className="eyebrow">Khải Hoàn</p>
        <h1>Ads Ops</h1>
      </div>
      <nav aria-label="Điều hướng chính">
        <a className="active" href="/">
          Chiến dịch
        </a>
        <a href="/">File export</a>
        <a href="/">Đồng bộ Notion</a>
        <a href="/">Bundle mẫu</a>
      </nav>
    </aside>
  );
}
