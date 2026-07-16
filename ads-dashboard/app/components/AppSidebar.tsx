const links = [
  { href: "#campaigns", label: "Chiến dịch" },
  { href: "#audiences", label: "Đối tượng" },
  { href: "#placements", label: "Vị trí quảng cáo" },
  { href: "#exports", label: "File export" }
];

export function AppSidebar() {
  return (
    <aside className="sidebar">
      <div>
        <p className="eyebrow">Khải Hoàn</p>
        <h1>Ads Ops</h1>
      </div>
      <nav aria-label="Điều hướng chính">
        {links.map((link, index) => (
          <a className={index === 0 ? "active" : undefined} href={link.href} key={link.href}>
            {link.label}
          </a>
        ))}
      </nav>
    </aside>
  );
}
