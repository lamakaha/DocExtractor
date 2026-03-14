from src.db.session import db_session
from src.models.schema import Package, PackageLog

def check():
    session = db_session()
    packages = session.query(Package).order_by(Package.created_at.desc()).all()
    print(f"Total packages in DB: {len(packages)}")
    for pkg in packages[:5]:
        print(f"ID: {pkg.id}, Filename: {pkg.original_filename}, Status: {pkg.status}, Created: {pkg.created_at}")
        logs = session.query(PackageLog).filter_by(package_id=pkg.id).order_by(PackageLog.timestamp.asc()).all()
        for log in logs:
            print(f"  [{log.timestamp}] {log.stage} - {log.level}: {log.message}")
    session.close()

if __name__ == "__main__":
    check()
