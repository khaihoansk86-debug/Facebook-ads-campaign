import Link from 'next/link';

const links = [
  { id: "campaigns", label: "Chiến dịch" },
  { id: "audiences", label: "Đối tượng" },
  { id: "placements", label: "Vị trí quảng cáo" },
  { id: "exports", label: "File export" }
];

export function AppSidebar({ activeTab = "campaigns" }: { activeTab?: string }) {
  return (
    <aside className="sidebar">
      <div>
        <p className="eyebrow">Khải Hoàn</p>
        <h1>Ads Ops</h1>
      </div>
      <nav aria-label="Điều hướng chính">
        {links.map((link) => (
          <Link className={activeTab === link.id ? "active" : undefined} href={`/?tab=${link.id}`} key={link.id}>
            {link.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
