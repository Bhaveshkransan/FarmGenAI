import json
import uuid
from copy import deepcopy
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import AsyncSessionLocal, DBUser

class UserRepository:
    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session

    async def get_by_email(self, email: str) -> Optional[DBUser]:
        if self.session is not None:
            res = await self.session.execute(select(DBUser).where(DBUser.email == email))
            return res.scalars().first()
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBUser).where(DBUser.email == email))
            return res.scalars().first()

    async def create(self, user_in: Any) -> DBUser:
        from backend.services.security import hash_password
        name = getattr(user_in, "name", None) or getattr(user_in, "full_name", "")
        pwd = getattr(user_in, "password", "")
        hashed_pwd = hash_password(pwd)
        user_id = getattr(user_in, "user_id", None) or getattr(user_in, "id", None) or str(uuid.uuid4())
        role = getattr(user_in, "role", "farmer")
        
        db_user = DBUser(
            user_id=user_id,
            email=user_in.email,
            password=hashed_pwd,
            name=name,
            role=role,
            location=getattr(user_in, "location", ""),
            language=getattr(user_in, "language", "English"),
            verification_status="PENDING",
            trust_score=4.0
        )
        if self.session is not None:
            self.session.add(db_user)
            await self.session.commit()
            await self.session.refresh(db_user)
            return db_user
        else:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    session.add(db_user)
            return db_user

    @staticmethod
    async def get_by_id(user_id: str) -> dict | None:
        async with AsyncSessionLocal() as session:
            db_user = await session.get(DBUser, user_id)
            if not db_user:
                return None
            
            docs = []
            try: docs = json.loads(db_user.verification_docs or "[]")
            except: pass
            
            prefs = {}
            try: prefs = json.loads(db_user.preferences or "{}")
            except: pass

            return {
                "user_id": db_user.user_id,
                "name": db_user.name,
                "email": db_user.email,
                "password": db_user.password,
                "location": db_user.location,
                "language": db_user.language,
                "role": db_user.role,
                "verification_status": db_user.verification_status,
                "verification_docs": docs,
                "preferences": prefs,
                "trust_score": db_user.trust_score
            }

    @staticmethod
    async def upsert(p: dict) -> dict:
        p = deepcopy(p)
        user_id = p["user_id"]
        async with AsyncSessionLocal() as session:
            async with session.begin():
                db_user = await session.get(DBUser, user_id)
                if not db_user:
                    db_user = DBUser(user_id=user_id)
                    session.add(db_user)
                
                if "name" in p: db_user.name = p["name"]
                if "email" in p: db_user.email = p["email"]
                if p.get("password"): db_user.password = p["password"]
                if "location" in p: db_user.location = p["location"]
                if "language" in p: db_user.language = p["language"]
                if "role" in p: db_user.role = p["role"]
                if "verification_status" in p: db_user.verification_status = p["verification_status"]
                if "verification_docs" in p: db_user.verification_docs = json.dumps(p["verification_docs"])
                if "preferences" in p: db_user.preferences = json.dumps(p["preferences"])
                if "trust_score" in p: db_user.trust_score = p["trust_score"]
        return p
