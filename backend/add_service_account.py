#!/usr/bin/env python3
"""CLI script to add a Google service account to the database."""
import asyncio
import json
import sys
from pathlib import Path

async def main():
    if len(sys.argv) < 3:
        print("Usage: python add_service_account.py <name> <path-to-json-key>")
        print("Example: python add_service_account.py indexai-sa-1 ../credentials/sa-key.json")
        sys.exit(1)

    name = sys.argv[1]
    key_path = Path(sys.argv[2]).resolve()

    if not key_path.exists():
        print(f"Error: File not found: {key_path}")
        sys.exit(1)

    key_data = json.loads(key_path.read_text())
    email = key_data.get("client_email")
    if not email:
        print("Error: No client_email found in JSON key")
        sys.exit(1)

    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from sqlalchemy import select
    from app.config import settings
    from app.models.service_account import ServiceAccount

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        existing = await db.execute(
            select(ServiceAccount).where(ServiceAccount.email == email)
        )
        if existing.scalars().first():
            print(f"Service account {email} already registered")
            sys.exit(0)

        sa = ServiceAccount(
            name=name,
            email=email,
            json_key_path=str(key_path),
            daily_quota=200,
            is_active=True,
        )
        db.add(sa)
        await db.commit()
        print(f"Service account added:")
        print(f"  Name:  {name}")
        print(f"  Email: {email}")
        print(f"  Key:   {key_path}")
        print(f"  Quota: 200/day")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
