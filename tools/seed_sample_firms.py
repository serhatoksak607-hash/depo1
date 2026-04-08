from app.db import SessionLocal
from app.models import ModuleData, Project


def main():
    db = SessionLocal()
    try:
        project = (
            db.query(Project)
            .filter(Project.id == 3)
            .first()
        )
        if not project:
            project = (
                db.query(Project)
                .filter(Project.name == "TOD")
                .order_by(Project.id.asc())
                .first()
            )
        if not project:
            raise SystemExit("Project not found: TOD / id=3")

        tenant_id = project.tenant_id
        project_id = project.id

        cities = [
            ("İstanbul", "Şişli"),
            ("Ankara", "Çankaya"),
            ("İzmir", "Konak"),
            ("Antalya", "Muratpaşa"),
            ("Bursa", "Nilüfer"),
        ]
        tax_offices = [
            "Maslak",
            "Kavaklıdere",
            "Konak",
            "Muratpaşa",
            "Nilüfer",
        ]
        legal_types = [
            "A.Ş.",
            "Ltd. Şti.",
            "San. ve Tic. A.Ş.",
            "Turizm ve Organizasyon Ltd. Şti.",
        ]

        created = 0
        for idx in range(1, 51):
            display_name = f"Örnek Sponsor {idx:02d}"
            exists = (
                db.query(ModuleData.id)
                .filter(
                    ModuleData.module_name == "kayit",
                    ModuleData.entity_type == "sponsor_firma",
                    ModuleData.project_id == project_id,
                    ModuleData.data["display_name"].astext == display_name,
                )
                .first()
            )
            if exists:
                continue

            city, district = cities[(idx - 1) % len(cities)]
            payload = {
                "company_name": display_name,
                "display_name": display_name,
                "legal_name": f"{display_name} {legal_types[(idx - 1) % len(legal_types)]}",
                "representative_name": f"Temsilci {idx:02d}",
                "representative_phone": f"+90532{idx:06d}",
                "representative_email": f"sponsor{idx:02d}@ornekfirma.com",
                "city": city,
                "district": district,
                "address": f"{district} Mah. Örnek Cad. No:{idx} {city}",
                "company_phone": f"+90212{(3000000 + idx):07d}",
                "phone": f"+90212{(3000000 + idx):07d}",
                "tax_office": tax_offices[(idx - 1) % len(tax_offices)],
                "tax_number": f"{1000000000 + idx}",
                "note": f"Deneme sponsor firma kaydı {idx:02d}",
            }
            row = ModuleData(
                tenant_id=tenant_id,
                project_id=project_id,
                module_name="kayit",
                entity_type="sponsor_firma",
                data=payload,
            )
            db.add(row)
            created += 1

        db.commit()
        total = (
            db.query(ModuleData)
            .filter(
                ModuleData.module_name == "kayit",
                ModuleData.entity_type == "sponsor_firma",
                ModuleData.project_id == project_id,
            )
            .count()
        )
        print(f"project_id={project_id} created={created} total_sponsor_firma={total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
